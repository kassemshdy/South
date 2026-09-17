import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { signInWithCode } from './support/sign-in'

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
  customCategoryText: string
  locationSlug: string
}>('./fixtures/other-category-data.json')

const t = (key: string): string => ar[key]!

const otherCategoryName = categories.find((c) => c.slug === 'other')!.name_ar
const districtName = locations
  .flatMap((governorate) => governorate.children ?? [])
  .find((district) => district.slug === fixture.locationSlug)!.name_ar

const OWNER_PHONE = '03911223'

/**
 * Selecting the "Other" category must reveal a required free-text field, and
 * the value entered there must be the one that reaches the next step — not
 * the literal category name.
 */
test.describe('"Other" business category', () => {
  test('requires and saves the custom category text', async ({ page }) => {
    await signInWithCode(page, OWNER_PHONE)

    await page.goto('/dashboard/businesses/new')
    await page.getByLabel(t('form.name')).fill(fixture.businessName)
    await page.getByLabel(t('form.shortDescription')).fill(fixture.shortDescription)

    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: otherCategoryName }).click()

    // The free-text field appears as soon as "Other" is selected.
    const customCategoryField = page.getByLabel(t('form.customCategoryLabel'))
    await expect(customCategoryField).toBeVisible()

    // Leaving it blank must block the step: no navigation to "location".
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()
    await expect(page.getByText(t('validation.customCategoryRequired'))).toBeVisible()
    await expect(page.getByLabel(t('form.name'))).toBeVisible()

    await customCategoryField.fill(fixture.customCategoryText)
    await page.getByLabel(t('form.whatsapp')).fill(OWNER_PHONE)
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    // Submission proceeds to the next step once the field is filled.
    await expect(page.getByLabel(t('form.area'))).toBeVisible()
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: districtName, exact: true }).click()
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    // The dashboard card shows the owner's own words, not the literal "Other".
    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { name: fixture.businessName })).toBeVisible()
    await expect(page.getByText(fixture.customCategoryText)).toBeVisible()
  })
})
