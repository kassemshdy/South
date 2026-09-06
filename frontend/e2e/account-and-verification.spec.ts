import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const categories = load<{ slug: string; name_ar: string }[]>(
  '../../backend/scripts/data/categories.json',
)
const fixture = load<{ businessName: string; shortDescription: string }>(
  './fixtures/account-verification-data.json',
)

const t = (key: string): string => ar[key]!
const categoryName = categories.find((c) => c.slug === 'restaurants')!.name_ar

const OWNER_PHONE = '03966101'
const DEV_OTP = '123456'
const ADMIN_EMAIL = 'admin@example.com'
const ADMIN_PASSWORD = 'ChangeMe!123'
const PERSONAL_PHONE = '03966102'

// A tiny valid PDF: the service only sniffs the "%PDF-" magic prefix.
function pdf(name = 'id.pdf'): { name: string; mimeType: string; buffer: Buffer } {
  return { name, mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\nfake-id-document\n') }
}

/**
 * The private owner-verification feature end to end: an owner sets a personal
 * phone number and uploads an ID document from the Account page, and an
 * administrator can see the phone and download the document from a business
 * review page — the two surfaces that never got a real browser check before.
 */
test.describe('Private owner verification', () => {
  test('owner sets personal info; admin views and downloads it', async ({ page }) => {
    // --- Owner: sign in and open the Account page --------------------------
    await page.goto('/login')
    await page.getByLabel(t('login.phoneLabel')).fill(OWNER_PHONE)
    await page.getByRole('button', { name: t('login.sendCode') }).click()
    await page.getByLabel(t('login.codeLabel')).fill(DEV_OTP)
    await page.getByRole('button', { name: t('login.confirm') }).click()
    await expect(page).toHaveURL(/\/dashboard/)

    await page.goto('/dashboard/account')
    await expect(page.getByRole('heading', { name: t('account.heading') })).toBeVisible()

    // --- Personal phone number round-trips and persists ---------------------
    await page.getByLabel(t('account.personalPhoneLabel')).fill(PERSONAL_PHONE)
    await page.getByRole('button', { name: t('account.saveProfile') }).click()
    await expect(page.getByText(t('account.profileSaved'), { exact: true }).first()).toBeVisible()

    await page.reload()
    await expect(page.getByLabel(t('account.personalPhoneLabel'))).toHaveValue('+9613966102')

    // --- ID document upload (upload+replace covers a rerun where a document
    // from a previous run of this same account already exists) ----------------
    await page.locator('input[type="file"]').setInputFiles(pdf())
    await expect(page.getByRole('button', { name: t('account.documentReplace') })).toBeVisible()

    // --- A minimal business so the admin has something to review -----------
    await page.goto('/dashboard/businesses/new')
    await page.getByLabel(t('form.name')).fill(fixture.businessName)
    await page.getByLabel(t('form.shortDescription')).fill(fixture.shortDescription)
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: categoryName }).click()
    await page.getByLabel(t('form.whatsapp')).fill(OWNER_PHONE)
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()
    await expect(page.getByLabel(t('form.area'))).toBeVisible()

    // --- Admin: see the personal phone and download the document -----------
    await page.goto('/admin/login')
    await page.getByLabel(t('adminLogin.email')).fill(ADMIN_EMAIL)
    await page.getByLabel(t('adminLogin.password')).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: t('adminLogin.submit') }).click()
    await expect(page.getByRole('heading', { name: t('admin.dashboardHeading') })).toBeVisible()

    await page.goto('/admin/businesses?status=DRAFT')
    await page
      .getByRole('listitem')
      .filter({ hasText: fixture.businessName })
      .first()
      .getByRole('link', { name: t('admin.details') })
      .click()
    await expect(page.getByRole('heading', { name: fixture.businessName })).toBeVisible()

    await expect(page.getByText('+9613966102')).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: t('admin.downloadDocument') }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('id.pdf')
  })
})
