import { expect, test, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { demoOwnerPhone, signIn } from './support/sign-in'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const skills = load<{ slug: string; name_ar: string }[]>(
  '../../backend/scripts/data/talent_skills.json',
)
const locations = load<{ children?: { slug: string; name_ar: string }[] }[]>(
  '../../backend/scripts/data/locations.json',
)
const fixture = load<{
  displayName: string
  bio: string
  yearsExperience: string
  skillSlug: string
  locationSlug: string
  phone: string
  searchTerm: string
}>('./fixtures/talent-directory-data.json')

const t = (key: string): string => ar[key]!

const skillName = skills.find((s) => s.slug === fixture.skillSlug)!.name_ar
const districtName = locations
  .flatMap((governorate) => governorate.children ?? [])
  .find((district) => district.slug === fixture.locationSlug)!.name_ar

const OWNER_PHONE = demoOwnerPhone('talent')
const ADMIN_EMAIL = 'admin@example.com'
const ADMIN_PASSWORD = 'ChangeMe!123'

function jpeg(): { name: string; mimeType: string; buffer: Buffer } {
  const base64 =
    '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a' +
    'HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAAKAAoBAREA/8QAHwAAAQUBAQEB' +
    'AQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1Fh' +
    'ByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZ' +
    'WmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXG' +
    'x8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oACAEBAAA/APn+iiiv/9k='
  return { name: 'photo.jpg', mimeType: 'image/jpeg', buffer: Buffer.from(base64, 'base64') }
}

async function signInAsOwner(page: Page) {
  await signIn(page, OWNER_PHONE)
}

async function signInAsAdmin(page: Page) {
  await page.goto('/admin/login')
  await page.getByLabel(t('adminLogin.email')).fill(ADMIN_EMAIL)
  await page.getByLabel(t('adminLogin.password')).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: t('adminLogin.submit') }).click()
  await expect(page.getByRole('heading', { name: t('admin.dashboardHeading') })).toBeVisible()
}

async function openTalentReview(page: Page) {
  await page.goto('/admin/talent')
  await page
    .getByRole('listitem')
    .filter({ hasText: fixture.displayName })
    .getByRole('link', { name: t('admin.review') })
    .click()
}

/**
 * The talent tier end to end: a person creates their one profile, an admin
 * approves it, and only then is it reachable by an anonymous visitor — the
 * same "APPROVED only is public" rule the business directory follows.
 */
test.describe('Talent directory', () => {
  test('person creates a profile, admin approves, visitor finds it', async ({
    page,
  }) => {
    await signInAsOwner(page)

    // --- Create the profile ---------------------------------------------------
    await page.goto('/dashboard/talent')
    await expect(
      page.getByRole('heading', { name: t('talentDashboard.createHeading') }),
    ).toBeVisible()

    await page.getByLabel(t('talentForm.displayName')).fill(fixture.displayName)
    await page.getByLabel(t('talentForm.bio')).fill(fixture.bio)
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: skillName }).click()
    await page.getByLabel(t('talentForm.yearsExperience')).fill(fixture.yearsExperience)
    await page.getByRole('combobox').nth(1).click()
    await page.getByRole('option', { name: districtName, exact: true }).click()
    await page.getByLabel(t('form.whatsapp')).fill(fixture.phone)
    // The job-seeker's own warning, and it must be *above* the button: a
    // caution met after pressing send is a record that somebody was told,
    // not a warning. Someone listing a profile here is asking for work, so
    // what reaches them is an approach from a stranger claiming to be an
    // employer — and nothing on this platform has checked that claim.
    const caution = page.getByText(t('consent.jobSeekerBody'))
    const send = page.getByRole('button', { name: t('talentDashboard.createSubmit') })
    await expect(caution).toBeVisible()
    const cautionBox = await caution.boundingBox()
    const sendBox = await send.boundingBox()
    expect(cautionBox!.y).toBeLessThan(sendBox!.y)

    await page.getByRole('button', { name: t('talentDashboard.createSubmit') }).click()

    await expect(page.getByRole('heading', { name: fixture.displayName })).toBeVisible()
    await expect(page.getByText(t('status.DRAFT'), { exact: true }).first()).toBeVisible()

    // A profile with no photo is not ready for review yet.
    await expect(page.getByText(t('talent.field.photo'), { exact: true })).toBeVisible()

    // --- Add the profile photo -------------------------------------------------
    await page.getByRole('tab', { name: t('talentDashboard.tabImages') }).click()
    await page.locator('input[type="file"]').first().setInputFiles(jpeg())
    await expect(page.getByText(t('images.uploaded'), { exact: true }).first()).toBeVisible()

    // --- Not reachable before approval ------------------------------------------
    await page.goto('/talent')
    await expect(page.getByText(fixture.displayName, { exact: true })).toHaveCount(0)

    // --- Submit for review --------------------------------------------------------
    await page.goto('/dashboard/talent')
    await page.getByRole('button', { name: t('dashboard.submitForReview') }).click()
    await expect(page.getByText(t('status.PENDING_REVIEW'), { exact: true }).first()).toBeVisible()

    // Still invisible while pending.
    await page.goto('/talent')
    await expect(page.getByText(fixture.displayName, { exact: true })).toHaveCount(0)

    // --- Administrator approves ----------------------------------------------------
    // The reject-then-resubmit round is covered by the backend suite
    // (test_talent.py); this spec keeps to the browser path that actually
    // publishes a profile, so it needs a single role switch rather than four.
    await signInAsAdmin(page)
    await openTalentReview(page)
    await expect(page.getByText(fixture.bio)).toBeVisible()
    await page.getByRole('button', { name: t('admin.approve') }).click()
    await expect(page.getByRole('heading', { name: t('admin.confirmApproveTitle') })).toBeVisible()
    await page.getByRole('button', { name: t('common.confirm'), exact: true }).click()
    await expect(page.getByText(t('status.APPROVED'), { exact: true }).first()).toBeVisible()

    // --- The profile is now public --------------------------------------------------
    await page.goto('/talent')
    const card = page.getByRole('article').filter({ hasText: fixture.displayName })
    await expect(card).toHaveCount(1)
    await expect(card.getByText(skillName)).toBeVisible()

    // Free-text search reaches it through the Arabic-normalized haystack.
    await page.goto(`/talent?q=${encodeURIComponent(fixture.searchTerm)}`)
    await expect(page.getByRole('article').filter({ hasText: fixture.displayName })).toHaveCount(1)

    // Filtering by another skill excludes it.
    await page.goto('/talent?skill=software')
    await expect(page.getByText(fixture.displayName, { exact: true })).toHaveCount(0)

    // --- The public profile page renders, with no moderation state on it ----------
    await page.goto('/talent')
    await page.getByRole('link', { name: fixture.displayName, exact: true }).click()
    await expect(page.getByRole('heading', { name: fixture.displayName, level: 1 })).toBeVisible()
    await expect(page.getByText(fixture.bio)).toBeVisible()
    // A public page never carries a status badge.
    await expect(page.getByText(t('status.APPROVED'), { exact: true })).toHaveCount(0)
  })
})
