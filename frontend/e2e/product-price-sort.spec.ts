import { expect, test, type APIRequestContext } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

interface Product {
  title: string
  price: string | null
}

// 60 is `MAX_PAGE_SIZE`; the seed is well inside it, so one page is the
// whole directory and the ordering can be checked end to end.
async function products(request: APIRequestContext, sort: string): Promise<Product[]> {
  const response = await request.get(`/api/items?page_size=60&sort=${sort}`)
  expect(response.ok(), `GET /api/items?sort=${sort}`).toBeTruthy()
  return ((await response.json()) as { items: Product[] }).items
}

/**
 * Ordering products by price, on the API.
 *
 * The products page lists shops now (round 3), so the ordering is no longer
 * offered there; it stays on `/api/items`, which the rest of this pins.
 *
 * This replaced a price *filter*, which needed a currency (a bound spanning
 * dollars and lira means two things at once) plus a fourth control deciding
 * what became of the products whose owner named no price. Four questions to
 * narrow a catalogue of 28. An ordering asks none of them.
 *
 * What the ordering must not do is the reason for this spec:
 *
 * 1. **It must not drop anything.** Every product on `newest` is still there
 *    on both price orders — that is the whole difference from the filter it
 *    replaced, and it is the property an owner with a blank price depends on.
 * 2. **An unpriced product sorts last in both directions.** Postgres puts
 *    NULLs first on a descending order, so "most expensive first" would
 *    otherwise open with the products that state no price at all — a claim
 *    the data does not support, and a page that reads as broken.
 */
test.describe('Products price sort', () => {
  test('both orders keep every product and sort the unpriced ones last', async ({ request }) => {
    const baseline = await products(request, 'newest')
    const unpriced = baseline.filter((product) => product.price === null)

    // The fixture the rest of this test leans on: the seed has to contain
    // both priced and unpriced products, or neither assertion means anything.
    expect(baseline.length).toBeGreaterThan(1)
    expect(unpriced.length).toBeGreaterThan(0)

    for (const sort of ['price_asc', 'price_desc']) {
      const sorted = await products(request, sort)

      // Nothing removed — an ordering is not a filter.
      expect(sorted.length, sort).toBe(baseline.length)
      expect(new Set(sorted.map((p) => p.title)), sort).toEqual(
        new Set(baseline.map((p) => p.title)),
      )

      // The unpriced ones are the tail, in both directions.
      const tail = sorted.slice(sorted.length - unpriced.length)
      expect(
        tail.every((product) => product.price === null),
        `${sort}: products with no stated price must sort last`,
      ).toBeTruthy()

      const amounts = sorted
        .filter((product) => product.price !== null)
        .map((product) => Number(product.price))
      const expected = [...amounts].sort((a, b) => (sort === 'price_asc' ? a - b : b - a))
      expect(amounts, sort).toEqual(expected)
    }
  })
})
