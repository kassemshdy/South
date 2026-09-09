import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const fixture = load<{ customer: string; phone: string; note: string }>(
  './fixtures/order-data.json',
)

const t = (key: string): string => ar[key]!

/**
 * Cart to order, from the visitor's side.
 *
 * The parts worth asserting in a browser rather than against the API:
 *
 * 1. **No account.** The whole flow runs signed out — the point of the
 *    feature is that a buyer never meets a login.
 * 2. **The cart survives navigation**, because it lives in localStorage
 *    rather than in the page that added to it.
 * 3. **The total is labelled an estimate.** There is no payment and the
 *    owner sets the real price, so calling it a total without that line
 *    would be the first lie in a feature whose only asset is being believed.
 *
 * The listing comes from the API so this spec does not depend on where a
 * seeded business happens to fall in a paginated directory.
 */
test.describe('Cart and order', () => {
  test('a visitor collects a product and sends an order without an account', async ({
    page,
    request,
  }) => {
    // A public product, which by definition belongs to an approved listing
    // and is available — the two conditions an order requires.
    const listing = await request.get('/api/items?page_size=1')
    expect(listing.ok()).toBeTruthy()
    const { items } = (await listing.json()) as {
      items: { slug: string; title: string }[]
    }
    expect(items.length).toBeGreaterThan(0)
    const { slug, title } = items[0]!

    await page.goto(`/product/${encodeURIComponent(slug)}`)
    await expect(page.getByRole('heading', { name: title, level: 1 })).toBeVisible()

    await page.getByRole('button', { name: t('cart.add') }).click()

    // Survives a page change: the cart is not state belonging to that page.
    await page.goto('/products')
    await page.getByRole('link', { name: t('cart.link') }).first().click()
    await expect(page).toHaveURL(/\/cart/)
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible()

    // Honest about what the number is.
    await expect(page.getByText(t('cart.totalHint'))).toBeVisible()

    await page.getByLabel(t('cart.nameLabel')).fill(fixture.customer)
    await page.getByLabel(t('cart.phoneLabel')).fill(fixture.phone)
    await page.getByLabel(t('cart.noteLabel')).fill(fixture.note)
    await page.getByRole('button', { name: t('cart.submit') }).click()

    await expect(page.getByRole('heading', { name: t('cart.sentTitle') })).toBeVisible()

    // Cleared only after the server accepted it, so the cart link is gone.
    await page.goto('/products')
    await expect(page.getByRole('link', { name: t('cart.link') })).toHaveCount(0)
  })
})
