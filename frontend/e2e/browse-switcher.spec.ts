import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const fixture = load<{ query: string; locationSlug: string }>(
  './fixtures/browse-switcher-data.json',
)

const t = (key: string): string => ar[key]!

/**
 * Moving between the directories: goods and products, and services and skills.
 *
 * They used to be islands. A visitor who searched the products directory and
 * found nothing had the browser's back button and the homepage, and nothing
 * else. So the doors the homepage offers are repeated above the results, where
 * the decision is actually being reconsidered. There is no businesses tab: at
 * the CEO's request the site speaks only of those two, and a shop is reached
 * through its products.
 *
 * The part worth asserting rather than eyeballing is **which filters travel**.
 * `q` and `location` mean the same thing in both directories and must survive
 * the hop; the price bounds are products-only, and carrying them into a page
 * with no price filter would apply a narrowing the visitor can neither see nor
 * clear.
 */
test.describe('Browse switcher', () => {
  test('marks where you are, carries the shared filters, and drops the ones that do not travel', async ({
    page,
  }) => {
    await page.goto(
      `/products?q=${encodeURIComponent(fixture.query)}` +
        `&location=${fixture.locationSlug}&currency=USD&max_price=10`,
    )

    const strip = page.getByRole('navigation', { name: t('browse.switcherLabel') })
    await expect(strip).toBeVisible()

    // Announced, not merely coloured.
    await expect(strip.getByRole('link', { name: t('browse.productsShort') })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(strip.getByRole('link', { name: t('browse.businessesShort') })).toHaveCount(0)

    await strip.getByRole('link', { name: t('browse.servicesShort') }).click()

    await expect(page).toHaveURL(/\/services/)
    const carried = new URL(page.url()).searchParams
    expect(carried.get('q')).toBe(fixture.query)
    expect(carried.get('location')).toBe(fixture.locationSlug)
    // Products-only, and the talent directory can neither show nor clear
    // them, so they are dropped rather than applied invisibly.
    expect(carried.get('max_price')).toBeNull()
    expect(carried.get('currency')).toBeNull()

    // The search box on the new page is actually holding the carried term,
    // rather than the URL saying one thing and the form another.
    await expect(page.getByRole('searchbox')).toHaveValue(fixture.query)
  })

  test('both directories carry the strip, each one tap from the other', async ({ page }) => {
    await page.goto('/services')
    const strip = page.getByRole('navigation', { name: t('browse.switcherLabel') })
    await expect(strip.getByRole('link', { name: t('browse.servicesShort') })).toHaveAttribute(
      'aria-current',
      'page',
    )

    await strip.getByRole('link', { name: t('browse.productsShort') }).click()
    await expect(page).toHaveURL(/\/products/)

    const onProducts = page.getByRole('navigation', { name: t('browse.switcherLabel') })
    await expect(
      onProducts.getByRole('link', { name: t('browse.productsShort') }),
    ).toHaveAttribute('aria-current', 'page')
  })
})
