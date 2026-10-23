import { expect, test, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { ADMIN_EMAIL, ADMIN_PASSWORD } from './support/admin'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const fixture = load<{ author: string; body: string }>('./fixtures/testimonial-data.json')

const t = (key: string): string => ar[key]!

async function signInAsAdmin(page: Page) {
  await page.goto('/admin/login')
  await page.getByLabel(t('adminLogin.email')).fill(ADMIN_EMAIL)
  await page.getByLabel(t('adminLogin.password')).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: t('adminLogin.submit') }).click()
  await expect(page.getByRole('heading', { name: t('admin.dashboardHeading') })).toBeVisible()
}

/**
 * Testimonials, from the visitor's side and then the administrator's.
 *
 * Asserted in a browser rather than only against the API, because these are
 * properties of the *page* and would break silently:
 *
 * 1. **Submitted praise does not appear** until an administrator publishes
 *    it -- and then does, with no step for the listing's owner (the owners'
 *    decision, round 3).
 * 2. **The disclaimer is on screen.** The authors are not verified, and the
 *    page must say so. Nothing else in the stack can catch that line being
 *    deleted — it is a sentence, not a behaviour.
 *
 * The listing comes from the API rather than from the seed file: the point is
 * "some published listing", and picking one by name meant depending on where
 * it happened to fall in a paginated directory, which is how the first
 * version of this spec failed.
 */
test.describe('Testimonials', () => {
  test('a visitor can leave one, it does not appear, and the page says why', async ({
    page,
    request,
  }) => {
    const listing = await request.get('/api/businesses?page_size=1')
    expect(listing.ok()).toBeTruthy()
    const { items } = (await listing.json()) as { items: { slug: string; name: string }[] }
    expect(items.length).toBeGreaterThan(0)
    const { slug, name } = items[0]!

    await page.goto(`/business/${encodeURIComponent(slug)}`)
    await expect(page.getByRole('heading', { name, level: 1 })).toBeVisible()

    // The honesty requirement, on screen next to the heading.
    await expect(
      page.getByRole('heading', { name: t('testimonials.heading') }),
    ).toBeVisible()
    await expect(page.getByText(t('testimonials.disclaimer'))).toBeVisible()

    await page.getByLabel(t('testimonials.authorLabel')).fill(fixture.author)
    await page.getByLabel(t('testimonials.bodyLabel')).fill(fixture.body)
    await page.getByRole('button', { name: t('testimonials.submit') }).click()

    // Accepted, and explicitly pending rather than published.
    await expect(page.getByText(t('testimonials.sent')).first()).toBeVisible()

    // The rule: not visible to anyone until an administrator publishes it.
    // Checked on a fresh load so nothing is being hidden by client state alone.
    await page.reload()
    await expect(page.getByText(fixture.body)).toHaveCount(0)
    await expect(page.getByText(t('testimonials.empty'))).toBeVisible()

    // The administrator publishes it; nobody else is asked.
    await signInAsAdmin(page)
    await page.goto('/admin/testimonials')
    const entry = page.getByRole('listitem').filter({ hasText: fixture.body })
    await entry.getByRole('button', { name: t('admin.testimonialClear') }).click()
    await expect(page.getByText(t('admin.testimonialCleared')).first()).toBeVisible()

    await page.goto(`/business/${encodeURIComponent(slug)}`)
    await expect(page.getByText(fixture.body)).toBeVisible()
  })
})
