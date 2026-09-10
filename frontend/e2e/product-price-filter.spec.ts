import { expect, test, type APIRequestContext } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const t = (key: string): string => ar[key]!
const resultCount = (count: number): string =>
  t('products.resultCount').replace('{count}', String(count))

async function total(request: APIRequestContext, query: string): Promise<number> {
  const response = await request.get(`/api/items?page_size=1&${query}`)
  expect(response.ok(), `GET /api/items?${query}`).toBeTruthy()
  return ((await response.json()) as { meta: { total: number } }).meta.total
}

/**
 * Filtering the products directory by price.
 *
 * Counts are read from the API rather than from the cards on screen, because
 * the directory paginates at twelve and the point being asserted is what the
 * filter *includes*, not what fits on the first page.
 *
 * The two decisions inside this filter are what the spec exists for, and
 * both are ways it could quietly mislead someone:
 *
 * 1. **A bound needs a currency.** The directory lists in dollars and in
 *    lira and holds no exchange rate, so a range spanning both is
 *    meaningless. The UI says so and refuses the input rather than sending a
 *    request it knows the API will reject.
 * 2. **A product with no stated price stays.** Two of the seeded products
 *    have no price — the kind of listing an owner puts up without naming a
 *    number — and dropping them behind the visitor's back would penalise
 *    them for an empty field. They go only when the visitor says so.
 */
test.describe('Products price filter', () => {
  test('a range needs a currency, and an unstated price is never dropped silently', async ({
    page,
    request,
  }) => {
    const everything = await total(request, '')
    const pricedUnderTen = await total(
      request,
      'currency=USD&max_price=10&include_unpriced=false',
    )
    const underTenWithUnpriced = await total(request, 'currency=USD&max_price=10')
    const unpriced = underTenWithUnpriced - pricedUnderTen

    // The fixture the rest of this spec leans on: the seed has to contain
    // both a product under ten dollars and one without a price, or nothing
    // below distinguishes the two behaviours.
    expect(pricedUnderTen).toBeGreaterThan(0)
    expect(unpriced).toBeGreaterThan(0)
    expect(underTenWithUnpriced).toBeLessThan(everything)

    await page.goto('/products')
    await expect(page.getByText(resultCount(everything), { exact: true })).toBeVisible()

    // On a narrow screen every filter sits behind the toggle, price included
    // — the only project this suite runs is a phone.
    await page.getByRole('button', { name: t('directory.filtersAria'), exact: true }).click()

    // --- Without a currency there is nothing to type a bound in ---------------
    const maxPrice = page.getByLabel(t('products.priceMaxLabel'))
    await expect(maxPrice).toBeDisabled()
    await expect(page.getByText(t('products.priceCurrencyFirst'))).toBeVisible()

    // --- Pick one, and the bounds come alive ----------------------------------
    await page.getByLabel(t('items.currencyLabel')).click()
    await page.getByRole('option', { name: t('items.currencyUsd') }).click()
    await expect(maxPrice).toBeEnabled()
    await expect(page.getByText(t('products.priceCurrencyFirst'))).toHaveCount(0)

    await maxPrice.fill('10')
    await maxPrice.press('Enter')

    // Committed to the URL, so the search is shareable like every other one.
    await expect(page).toHaveURL(/max_price=10/)
    await expect(page).toHaveURL(/currency=USD/)
    await expect(page.getByText(resultCount(underTenWithUnpriced), { exact: true })).toBeVisible()

    // --- The unpriced products are in that number, and said to be -------------
    await expect(page.getByText(t('products.includeUnpricedHint'))).toBeVisible()
    const keepUnpriced = page.getByLabel(t('products.includeUnpriced'))
    await expect(keepUnpriced).toBeChecked()

    // click + assert rather than `uncheck()`: the box is driven by the URL, so
    // its DOM state settles a React render after the click and `uncheck`'s
    // own check runs too early to see it.
    await keepUnpriced.click()
    await expect(keepUnpriced).not.toBeChecked()
    await expect(page.getByText(resultCount(pricedUnderTen), { exact: true })).toBeVisible()

    // --- Clearing the currency clears the bound with it -----------------------
    // A range left behind with nothing to denominate it is the meaningless
    // comparison this whole filter refuses to make.
    await page.getByLabel(t('items.currencyLabel')).click()
    await page.getByRole('option', { name: t('products.priceCurrencyAll') }).click()
    await expect(page).not.toHaveURL(/max_price=/)
    await expect(maxPrice).toBeDisabled()
  })
})
