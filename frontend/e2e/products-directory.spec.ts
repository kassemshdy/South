import { expect, test, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { openBusinessWizard } from './support/wizard'

import { demoOwnerPhone, signIn } from './support/sign-in'
import { ADMIN_EMAIL, ADMIN_PASSWORD } from './support/admin'
import { dropPin } from './support/map'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
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
  phone: string
  availableItem: { title: string; price: string }
  unavailableItem: { title: string }
}>('./fixtures/products-directory-data.json')

const t = (key: string): string => ar[key]!

const categoryName = categories.find((c) => c.slug === fixture.categorySlug)!.name_ar
const districtName = locations
  .flatMap((governorate) => governorate.children ?? [])
  .find((district) => district.slug === fixture.locationSlug)!.name_ar

const OWNER_PHONE = demoOwnerPhone('products')

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

/**
 * `/products` lists the shops with something on sale (the owners' decision,
 * round 3), and a product is searched inside its shop's page. A shop is only
 * there once approved, and only while one of its products is available — the
 * same two visibility rules the backend enforces.
 */
test.describe('Products directory', () => {
  test('owner publishes items, admin approves, visitor finds only the available one', async ({
    page,
  }) => {
    await signInAsOwner(page)

    // --- Create the business -------------------------------------------------
    await openBusinessWizard(page)
    await page.getByLabel(t('form.name')).fill(fixture.businessName)
    await page.getByLabel(t('form.shortDescription')).fill(fixture.shortDescription)
    // Producer detail and the long description are optional at submission,
    // in the section the owners asked to be always open.
    await page.getByLabel(t('form.description')).fill(fixture.description)
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: categoryName }).click()
    await page.getByLabel(t('form.whatsapp')).fill(fixture.phone)
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    await expect(page.getByLabel(t('form.area'))).toBeVisible()
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: districtName, exact: true }).click()
    // Every seller pins themselves on the map; a tap anywhere drops it.
    await dropPin(page, t('form.mapPinLabel'))
    await page.getByLabel(t('form.address')).fill(fixture.address)
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    await expect(page.getByRole('heading', { name: t('images.logoTitle') })).toBeVisible()
    await page.locator('input[type="file"]').first().setInputFiles(jpeg())
    await expect(page.getByText(t('images.uploaded'), { exact: true }).first()).toBeVisible()
    await page.getByRole('button', { name: t('common.continue'), exact: true }).click()

    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    // Official papers sit between the social links and the catalogue, and are
    // optional: this owner has none, so the step is walked straight past.
    await page.getByRole('button', { name: t('common.continue'), exact: true }).click()

    // --- Two items: one available, one not -----------------------------------
    await page.getByRole('button', { name: t('items.addItem') }).first().click()
    await page.getByLabel(t('items.nameLabel')).fill(fixture.availableItem.title)
    await page.getByLabel(t('items.priceLabel')).fill(fixture.availableItem.price)
    await page.getByRole('button', { name: t('items.addAction') }).click()
    await expect(
      page.getByRole('heading', { name: fixture.availableItem.title, level: 4 }),
    ).toBeVisible()

    await page.getByRole('button', { name: t('items.addItem') }).first().click()
    await page.getByLabel(t('items.nameLabel')).fill(fixture.unavailableItem.title)
    await page.getByLabel(t('items.priceLabel')).fill(fixture.unavailableItem.price)
    await page.getByLabel(t('items.availableLabel')).uncheck()
    await page.getByRole('button', { name: t('items.addAction') }).click()
    await expect(
      page.getByRole('heading', { name: fixture.unavailableItem.title, level: 4 }),
    ).toBeVisible()

    await page.getByRole('button', { name: t('wizard.continueToReview') }).click()
    await expect(page.getByText(t('wizard.allComplete')).first()).toBeVisible()
    await page.getByRole('button', { name: t('dashboard.submitForReview') }).click()
    await expect(page).toHaveURL(/\/dashboard/)

    // --- Not reachable before approval -----------------------------------------
    await page.goto('/products')
    await expect(page.getByText(fixture.businessName, { exact: true })).toHaveCount(0)

    // --- Administrator approves -------------------------------------------------
    await page.goto('/admin/login')
    await page.getByLabel(t('adminLogin.email')).fill(ADMIN_EMAIL)
    await page.getByLabel(t('adminLogin.password')).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: t('adminLogin.submit') }).click()
    await expect(page.getByRole('heading', { name: t('admin.dashboardHeading') })).toBeVisible()
    // The business queue's link, named by its card: the talent queue has a
    // card and an identical button beside it.
    await page
      .getByRole('link', {
        name: `${t('admin.pendingLabel')} ${t('admin.reviewRequests')}`,
        exact: true,
      })
      .click()
    await page
      .getByRole('listitem')
      .filter({ hasText: fixture.businessName })
      .getByRole('link', { name: t('admin.review') })
      .click()
    await page.getByRole('button', { name: t('admin.approve') }).click()
    await expect(page.getByRole('heading', { name: t('admin.confirmApproveTitle') })).toBeVisible()
    await page.getByRole('button', { name: t('common.confirm'), exact: true }).click()
    await expect(page.getByText(t('status.APPROVED'), { exact: true }).first()).toBeVisible()

    // --- The shop is now on /products, found by what it sells ----------------
    await page.goto('/products')
    await expect(page.getByRole('article').filter({ hasText: fixture.businessName })).toHaveCount(1)
    await page.goto(`/products?q=${encodeURIComponent(fixture.availableItem.title)}`)
    const card = page.getByRole('article').filter({ hasText: fixture.businessName })
    await expect(card).toHaveCount(1)

    // --- Inside the shop, the products are searched ----------------------------
    await card.getByRole('link', { name: fixture.businessName }).first().click()
    await expect(
      page.getByRole('heading', { name: fixture.businessName, level: 1 }),
    ).toBeVisible()
    const search = page.getByLabel(t('business.itemsSearchLabel'))
    await search.fill(fixture.availableItem.title)
    await expect(page.getByRole('heading', { name: fixture.availableItem.title })).toBeVisible()
    await expect(page.getByRole('heading', { name: fixture.unavailableItem.title })).toHaveCount(0)

    // The unavailable item still shows on its own business's page, marked as such.
    await search.fill('')
    await expect(page.getByRole('heading', { name: fixture.unavailableItem.title })).toBeVisible()
    await expect(page.getByText(t('business.itemUnavailable')).first()).toBeVisible()

    // --- A product keeps its own page, which links back to the shop ------------
    const found = await page.request.get(
      `/api/items?q=${encodeURIComponent(fixture.availableItem.title)}`,
    )
    const { items } = (await found.json()) as { items: { slug: string }[] }
    expect(items).toHaveLength(1)
    await page.goto(`/product/${encodeURIComponent(items[0]!.slug)}`)
    await expect(
      page.getByRole('heading', { name: fixture.availableItem.title, level: 1 }),
    ).toBeVisible()
    await expect(page.getByText('$3.00').first()).toBeVisible()
    // A product is the most passed-around thing on this site — a photo, a name
    // and a price — and it was the one public page with no way to pass it on.
    await expect(page.getByRole('button', { name: t('business.share') })).toBeVisible()
    await expect(page.getByRole('link', { name: fixture.businessName })).toBeVisible()
  })
})
