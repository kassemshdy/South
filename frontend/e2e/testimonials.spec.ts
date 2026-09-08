import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const fixture = load<{ author: string; body: string }>('./fixtures/testimonial-data.json')

const t = (key: string): string => ar[key]!

/**
 * Owner-approved testimonials, from the visitor's side.
 *
 * Two things are asserted in a browser rather than only against the API,
 * because both are properties of the *page* and would break silently:
 *
 * 1. **Submitted praise does not appear.** The backend suite pins this on the
 *    payload; this pins it on what a person actually sees, which is the claim
 *    the feature makes to the shop owner.
 * 2. **The disclaimer is on screen.** These are owner-selected, so the page
 *    must say they are not independent reviews. Nothing else in the stack can
 *    catch that line being deleted — it is a sentence, not a behaviour.
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

    // The rule: not visible to anyone until the owner approves it. Checked on
    // a fresh load so nothing is being hidden by client state alone.
    await page.reload()
    await expect(page.getByText(fixture.body)).toHaveCount(0)
    await expect(page.getByText(t('testimonials.empty'))).toBeVisible()
  })
})
