import { expect, test, type APIRequestContext } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')

const t = (key: string): string => ar[key]!

/** A public product, so the spec does not depend on where a seeded listing
 * falls in a paginated directory. */
async function publicProduct(request: APIRequestContext) {
  const listing = await request.get('/api/items?page_size=1')
  expect(listing.ok()).toBeTruthy()
  const { items } = (await listing.json()) as { items: { slug: string; title: string }[] }
  expect(items.length).toBeGreaterThan(0)
  return items[0]!
}

/**
 * Saving a listing, from the visitor's side.
 *
 * What is worth a browser rather than a unit test:
 *
 * 1. **It survives a reload.** That is the entire feature — a list held only
 *    in React state would pass every other assertion here and be useless.
 * 2. **No account.** The flow runs signed out from start to finish.
 * 3. **A corrupt stored value does not break the page.** Storage is edited by
 *    hand, shared with older versions of this code, and occasionally
 *    truncated; the page it renders must not be the thing that fails.
 */
test.describe('Saved listings', () => {
  test('a visitor saves a product and it is still there after a reload', async ({
    page,
    request,
  }) => {
    const { slug, title } = await publicProduct(request)

    await page.goto(`/product/${encodeURIComponent(slug)}`)
    await expect(page.getByRole('heading', { name: title, level: 1 })).toBeVisible()

    await page.getByRole('button', { name: t('favourites.save'), exact: true }).click()
    // The same button, now reflecting that it is saved.
    await expect(page.getByRole('button', { name: t('favourites.saved') })).toBeVisible()

    // Survives both a navigation and a full reload.
    await page.goto('/favourites')
    await page.reload()
    await expect(page.getByRole('heading', { name: t('favourites.title') })).toBeVisible()
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible()

    // And can be given back.
    await page.getByRole('button', { name: t('favourites.remove') }).first().click()
    await expect(page.getByText(t('favourites.empty'))).toBeVisible()

    // With nothing saved, the header link is absent rather than showing a zero.
    await page.goto('/products')
    await expect(page.getByRole('link', { name: t('favourites.link') })).toHaveCount(0)
  })

  test('a corrupt saved list does not break the page it is rendered on', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => {
      window.localStorage.setItem('south.favourites', '{"not":"an array"}')
    })
    await page.goto('/favourites')
    await expect(page.getByText(t('favourites.empty'))).toBeVisible()

    // A list that is an array but whose entries are junk keeps the good ones
    // and drops the rest, rather than throwing the list away wholesale.
    await page.evaluate(() => {
      window.localStorage.setItem(
        'south.favourites',
        JSON.stringify([
          { subject: 'NONSENSE', slug: 'x', title: 'x', imageUrl: null, savedAt: 'now' },
          { slug: 'missing-a-subject' },
          null,
        ]),
      )
    })
    await page.reload()
    await expect(page.getByText(t('favourites.empty'))).toBeVisible()
  })
})
