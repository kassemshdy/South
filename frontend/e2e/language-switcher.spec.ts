import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const en = load<Record<string, string>>('../src/i18n/locales/en.json')

// The backend's catalogs, read directly: these tests assert on sentences the
// *server* renders, so the expected text has to come from the server's own
// source of truth rather than a copy in the frontend.
const apiArCatalog = load<Record<string, string>>('../../backend/app/locales/ar.json')
const apiEnCatalog = load<Record<string, string>>('../../backend/app/locales/en.json')
const fixture = load<{ customer: string; phone: string }>('./fixtures/order-data.json')

const t = (key: string): string => ar[key]!
const tEn = (key: string): string => en[key]!
const apiAr = (key: string): string => apiArCatalog[key]!
const apiEn = (key: string): string => apiEnCatalog[key]!

// The control's accessible name, exactly as each catalog renders it. Built from
// the catalogs rather than hard-coded, so a reworded label updates the test.
const SWITCH_TO_ENGLISH = t('nav.switchLanguage').replace('{language}', t('nav.localeEnglish'))
const SWITCH_TO_ARABIC = tEn('nav.switchLanguage').replace('{language}', tEn('nav.localeArabic'))

/**
 * The language switcher, end to end.
 *
 * Both catalogs have been complete for a while and no visitor could reach the
 * English one — nothing in the app called `setLocale`. This spec is what keeps
 * that from silently happening again: it drives the control a real person
 * would use, then checks the three things that make the switch real —
 * translated chrome, a flipped document direction, and a choice that survives
 * a reload.
 */
test.describe('Language switcher', () => {
  test('a visitor can switch to English, and the choice sticks', async ({ page }) => {
    await page.goto('/businesses')

    // Arabic is the default, and the directory heading proves the catalog is live.
    await expect(page.getByRole('heading', { name: t('directory.heading') })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    await expect(page.locator('html')).toHaveAttribute('lang', 'ar')

    // The control names the language it switches *to*, in that language.
    // getByRole only matches what is in the accessibility tree, so this
    // resolves to whichever of the two toggles (desktop nav or mobile icon
    // row) is actually on screen at this viewport.
    const toEnglish = page.getByRole('button', { name: SWITCH_TO_ENGLISH })
    await expect(toEnglish).toBeVisible()
    await toEnglish.click()

    await expect(page.getByRole('heading', { name: tEn('directory.heading') })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')

    // Persisted, not just held in memory for this render.
    await page.reload()
    await expect(page.getByRole('heading', { name: tEn('directory.heading') })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')

    // And it goes back.
    await page.getByRole('button', { name: SWITCH_TO_ARABIC }).click()
    await expect(page.getByRole('heading', { name: t('directory.heading') })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  })

  test('Arabic listing content still reads right-to-left on the English site', async ({
    page,
  }) => {
    // The bidi rule the switch exposed: UI language and content language are
    // independent, so an Arabic listing must not be dragged left-to-right by
    // an English page around it.
    await page.goto('/businesses')
    await page.getByRole('button', { name: SWITCH_TO_ENGLISH }).click()
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')

    const firstCard = page.getByRole('article').first()
    await expect(firstCard).toBeVisible()
    // The card body declares dir="auto" so the browser resolves each string's
    // direction from its own text rather than from the page.
    await expect(firstCard.locator('[dir="auto"]').first()).toHaveAttribute('dir', 'auto')
  })
})

/**
 * Place an order through the UI. `ui` is the catalog the page is currently
 * rendering in — the labels have to be looked up in the language on screen,
 * which is the same distinction these tests are about.
 */
async function orderTheFirstProduct(
  page: Page,
  request: APIRequestContext,
  ui: (key: string) => string,
) {
  const listing = await request.get('/api/items?page_size=1')
  expect(listing.ok()).toBeTruthy()
  const { items } = (await listing.json()) as { items: { slug: string }[] }
  const { slug } = items[0]!

  await page.goto(`/product/${encodeURIComponent(slug)}`)
  await page.getByRole('button', { name: ui('cart.add') }).click()
  await page.goto('/cart')
  await page.getByLabel(ui('cart.nameLabel')).fill(fixture.customer)
  await page.getByLabel(ui('cart.phoneLabel')).fill(fixture.phone)
  await page.getByRole('button', { name: ui('cart.submit') }).click()
}

/**
 * Each of the two blocks below puts the browser in the language the site is
 * *not* in, because that mismatch is the whole bug: the API picks its locale
 * from `Accept-Language`, the client sent none of its own, so the browser's
 * header went out and the site's choice was ignored. Someone ordering on the
 * Arabic site was told "Your order was sent." in English.
 *
 * Matching browser and site would prove nothing — and that is exactly why
 * the suite missed this. `playwright.config.ts` sets `locale: 'ar-LB'`, so
 * every other spec has a browser and a site that agree on Arabic by
 * coincidence.
 */
test.describe('An English browser does not make the Arabic site speak English', () => {
  test.use({ locale: 'en-US' })

  test('the order confirmation comes back in Arabic', async ({ page, request }) => {
    await page.goto('/')
    await expect(page.locator('html')).toHaveAttribute('lang', 'ar')

    await orderTheFirstProduct(page, request, t)

    // The toast description is the API's own sentence rather than a local
    // string, which is why it was the thing the visitor saw in the wrong
    // language.
    await expect(page.getByText(apiAr('order.received'))).toBeVisible()
  })
})

test.describe('An Arabic browser does not make the English site speak Arabic', () => {
  // The config default (ar-LB) is the mismatch here, so it is left alone.

  test('the order confirmation comes back in English', async ({ page, request }) => {
    await page.goto('/')
    await page.getByRole('button', { name: SWITCH_TO_ENGLISH }).click()
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')

    await orderTheFirstProduct(page, request, tEn)

    await expect(page.getByText(apiEn('order.received'))).toBeVisible()
  })
})
