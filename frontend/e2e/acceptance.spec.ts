import { expect, test, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { openBusinessWizard } from './support/wizard'

import { signInWithCode } from './support/sign-in'

const here = dirname(fileURLToPath(import.meta.url))
// Read rather than import: Playwright's ESM loader would require import
// attributes for JSON, and reading keeps the spec working either way.
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const backendAr = load<Record<string, string>>('../../backend/app/locales/ar.json')
const categories = load<{ slug: string; name_ar: string }[]>(
  '../../backend/scripts/data/categories.json',
)
const locations = load<{ children?: { slug: string; name_ar: string }[] }[]>(
  '../../backend/scripts/data/locations.json',
)
const fixture = load<{
  businessName: string
  shortDescription: string
  description: string
  address: string
  categorySlug: string
  locationSlug: string
  searchTerm: string
  items: { title: string; price: string }[]
}>('./fixtures/acceptance-data.json')

/**
 * The UI text comes from the same catalog the app renders from, so this suite
 * fails if a translation key is renamed or removed — and it can never drift
 * out of step with the interface it is asserting on.
 */
const t = (key: string): string => ar[key]!

/**
 * Test *data* comes from the same seed files the application is loaded with, so
 * renaming a seeded category cannot silently invalidate this test.
 */
const categoryName = categories.find((c) => c.slug === fixture.categorySlug)!.name_ar
const districtName = locations
  .flatMap((governorate) => governorate.children ?? [])
  .find((district) => district.slug === fixture.locationSlug)!.name_ar

/**
 * The MVP acceptance scenario, end to end in a real browser.
 *
 * A visitor browses without an account, an owner signs in by phone and builds a
 * listing, the listing stays invisible until an administrator approves it, and
 * it becomes searchable immediately afterwards.
 */

const OWNER_PHONE = '03987654'
const ADMIN_EMAIL = 'admin@example.com'
const ADMIN_PASSWORD = 'ChangeMe!123'
const BUSINESS_NAME = fixture.businessName

// A tiny valid JPEG generated at runtime, so no binary fixtures live in the repo.
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
  await signInWithCode(page, OWNER_PHONE)
}

test.describe('MVP acceptance flow', () => {
  test('visitor browses, owner submits, admin approves, listing becomes searchable', async ({ page }) => {
    // --- 1. A visitor browses approved businesses without logging in --------
    await page.goto('/')
    await expect(page.getByRole('heading', { name: t('home.heroTitle') })).toBeVisible()

    // The one intent chooser, asked once: both halves of the question, and no
    // second or third widget asking it again further down. This replaced a
    // "what are you looking for" section that duplicated it.
    await expect(page.getByRole('heading', { name: t('onboarding.heading') })).toBeVisible()
    // Plain substrings rather than `new RegExp`: both of these labels carry a
    // parenthesised aside now, and `(` in a RegExp is a group rather than a
    // bracket, so the pattern would stop matching the text it was built from.
    await expect(page.getByRole('button', { name: t('home.actionOffer') })).toHaveCount(1)
    await expect(page.getByRole('button', { name: t('home.actionBrowse') })).toHaveCount(1)
    // Nothing anywhere on the page is "coming soon" any more.
    await expect(page.getByText(t('home.comingSoon'))).toHaveCount(0)

    // Looking for something forks by kind, and the service side reaches the
    // talent directory -- the same destination the old card asserted, now via
    // the path a visitor actually takes. Browsing carries no responsibility
    // notice -- only listing something does -- so this door is a real link
    // straight through.
    await page.getByRole('button', { name: t('home.actionBrowse') }).click()
    await expect(page.getByRole('link', { name: t('onboarding.seekGoodsTitle') })).toBeVisible()
    await page.getByRole('link', { name: t('onboarding.seekServiceTitle') }).click()
    await expect(page).toHaveURL(/\/talent$/)
    await expect(page.getByRole('heading', { name: t('talent.heading') })).toBeVisible()
    await page.goBack()

    await page.goto('/businesses')
    await expect(page.getByRole('heading', { name: t('directory.heading') })).toBeVisible()
    await expect(page.getByRole('article').first()).toBeVisible()
    await page.screenshot({ path: 'e2e/screenshots/01-directory.png', fullPage: false })

    // --- 2. The owner signs in with a Lebanese number + OTP -----------------
    await signInAsOwner(page)
    await expect(page.getByRole('heading', { name: t('dashboard.heading') })).toBeVisible()

    // --- 3. Create the business --------------------------------------------
    await openBusinessWizard(page)
    await page.getByLabel(t('form.name')).fill(BUSINESS_NAME)
    await page.getByLabel(t('form.shortDescription')).fill(fixture.shortDescription)

    // The long description is optional at submission, so it now sits behind a
    // disclosure (#34). This flow still fills it — a real listing wants one —
    // which also keeps the optional section covered end to end.
    await page.getByText(t('form.optionalSectionTitle')).click()
    await page.getByLabel(t('form.description')).fill(fixture.description)

    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: categoryName }).click()

    await page.getByLabel(t('form.whatsapp')).fill('03987654')
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    // --- 4. Location ---------------------------------------------------------
    await expect(page.getByLabel(t('form.area'))).toBeVisible()
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: districtName, exact: true }).click()
    await page.getByLabel(t('form.address')).fill(fixture.address)
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    // --- 5. Images: a logo and three gallery photos -------------------------
    await expect(page.getByRole('heading', { name: t('images.logoTitle') })).toBeVisible()
    const fileInputs = page.locator('input[type="file"]')
    await fileInputs.nth(0).setInputFiles(jpeg())
    await expect(page.getByText(t('images.uploaded'), { exact: true }).first()).toBeVisible()

    for (let index = 0; index < 3; index += 1) {
      await page.locator('input[type="file"]').last().setInputFiles(jpeg())
      await expect(page.getByText(ar['images.galleryCount']!.replace('{current}', String(index + 1)).replace('{max}', '10'), { exact: true })).toBeVisible()
    }
    await page.screenshot({ path: 'e2e/screenshots/02-images.png', fullPage: false })
    await page.getByRole('button', { name: t('common.continue'), exact: true }).click()

    // --- 6. Social links: Instagram ----------------------------------------
    await page.getByLabel(t('platform.INSTAGRAM')).fill('instagram.com/manakish.aldayaa')
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    // --- 7. Items with prices ------------------------------------------------
    for (const { title, price } of fixture.items) {
      await page.getByRole('button', { name: t('items.addItem') }).first().click()
      await page.getByLabel(t('items.nameLabel')).fill(title)
      await page.getByLabel(t('items.priceLabel')).fill(price)

      // This project runs at phone size, and that is the point of the next
      // three lines rather than a plain click. The item editor used to be a
      // centred modal; the form is long enough that on a Pixel 7 it hung off
      // both ends of a fixed, vertically centred box, and this button sat
      // below the fold where scrolling could not reach it — the page scrolls,
      // the box does not. An owner on a phone simply could not add an item.
      // The editor is a page now, so scrolling works; if it is ever put back
      // in a container the form outgrows, this fails here rather than in
      // somebody's shop.
      const submit = page.getByRole('button', { name: t('items.addAction') })
      await submit.scrollIntoViewIfNeeded()
      await expect(submit).toBeInViewport()
      await submit.click()

      await expect(page.getByRole('heading', { name: title, level: 4 })).toBeVisible()
    }
    await page.screenshot({ path: 'e2e/screenshots/03-items.png', fullPage: false })

    // --- 8. Submit for review ----------------------------------------------
    await page.getByRole('button', { name: t('wizard.continueToReview') }).click()
    await expect(page.getByText(t('wizard.allComplete')).first()).toBeVisible()
    await page.getByRole('button', { name: t('dashboard.submitForReview') }).click()

    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByText(t('status.PENDING_REVIEW'), { exact: true }).first()).toBeVisible()
    await page.screenshot({ path: 'e2e/screenshots/04-pending.png', fullPage: false })

    // --- 9. The pending listing must NOT be publicly visible ----------------
    // Other approved listings may legitimately match this query, so assert on
    // the absence of *this* business rather than an empty result set.
    await page.goto(`/businesses?q=${encodeURIComponent(fixture.searchTerm)}`)
    await expect(page.getByRole('article').filter({ hasText: BUSINESS_NAME })).toHaveCount(0)

    // Its public profile must not be reachable directly either.
    await page.goto(`/business/${encodeURIComponent(fixture.businessName.replace(/\s+/g, '-'))}`)
    await expect(page.getByText(backendAr['business.not_public']!)).toBeVisible()

    // --- 10. Administrator approves ----------------------------------------
    await page.goto('/admin/login')
    await page.getByLabel(t('adminLogin.email')).fill(ADMIN_EMAIL)
    await page.getByLabel(t('adminLogin.password')).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: t('adminLogin.submit') }).click()

    await expect(page.getByRole('heading', { name: t('admin.dashboardHeading') })).toBeVisible()
    await page.getByRole('link', { name: t('admin.reviewRequests') }).click()

    // The queue is oldest-first, so target this listing's row rather than the
    // first one in the list.
    await page
      .getByRole('listitem')
      .filter({ hasText: BUSINESS_NAME })
      .getByRole('link', { name: t('admin.review') })
      .click()
    await expect(page.getByRole('heading', { name: BUSINESS_NAME })).toBeVisible()
    // The reviewer sees the owner's account phone and the submitted items.
    await expect(page.getByText('+9613987654').first()).toBeVisible()
    await expect(page.getByText(fixture.items[0].title, { exact: true }).first()).toBeVisible()
    await page.screenshot({ path: 'e2e/screenshots/05-admin-review.png', fullPage: true })

    await page.getByRole('button', { name: t('admin.approve') }).click()
    await expect(page.getByRole('heading', { name: t('admin.confirmApproveTitle') })).toBeVisible()
    await page.getByRole('button', { name: t('common.confirm'), exact: true }).click()
    await expect(page.getByText(t('status.APPROVED'), { exact: true }).first()).toBeVisible()

    // --- 11. Immediately searchable on the public site ----------------------
    await page.goto(`/businesses?q=${encodeURIComponent(fixture.searchTerm)}`)
    const card = page.getByRole('article').filter({ hasText: BUSINESS_NAME })
    await expect(card).toHaveCount(1)
    await page.screenshot({ path: 'e2e/screenshots/06-search-result.png', fullPage: false })

    // --- 12. The public profile shows everything the owner published --------
    await card.getByRole('link', { name: t('business.viewDetails') }).click()
    await expect(page.getByRole('heading', { name: BUSINESS_NAME, level: 1 })).toBeVisible()
    await expect(page.getByText(t('business.verified')).first()).toBeVisible()
    await expect(page.getByRole('heading', { name: t('business.itemsHeading') })).toBeVisible()
    await expect(page.getByText('$1.50')).toBeVisible()
    await expect(page.getByText('$3.00')).toBeVisible()
    await expect(page.getByText('$2.50')).toBeVisible()
    await expect(page.getByRole('heading', { name: t('business.galleryHeading') })).toBeVisible()
    await expect(page.getByRole('link', { name: t('business.whatsappCta') })).toBeVisible()
    await expect(page.getByRole('link', { name: t('platform.INSTAGRAM') })).toBeVisible()
    await page.screenshot({ path: 'e2e/screenshots/07-public-profile.png', fullPage: true })
  })
})
