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
const fixture = load<{
  businessName: string
  shortDescription: string
  fullName: string
  registrationPlace: string
  residencePlace: string
  institutionName: string
  productionNature: string
}>('./fixtures/account-verification-data.json')

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
 * phone number, their identity details and an ID document from the Account
 * page, and an administrator sees all three — plus the producer detail the
 * listing itself publishes — from a business review page.
 *
 * The identity assertions are the point of the account-level split: the same
 * legal name a reviewer reads here was typed once, on the account, and would
 * be shared by every other listing this owner creates.
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

    // --- Personal phone and identity round-trip and persist ----------------
    await page.getByLabel(t('account.personalPhoneLabel')).fill(PERSONAL_PHONE)
    await page.getByLabel(t('account.fullNameLabel')).fill(fixture.fullName)
    await page.getByLabel(t('account.birthYearLabel')).fill('1985')
    await page.getByLabel(t('account.registrationPlaceLabel')).fill(fixture.registrationPlace)
    await page.getByLabel(t('account.residencePlaceLabel')).fill(fixture.residencePlace)
    await page.getByRole('button', { name: t('account.saveProfile') }).click()
    await expect(page.getByText(t('account.profileSaved'), { exact: true }).first()).toBeVisible()

    await page.reload()
    await expect(page.getByLabel(t('account.personalPhoneLabel'))).toHaveValue('+9613966102')
    await expect(page.getByLabel(t('account.fullNameLabel'))).toHaveValue(fixture.fullName)
    await expect(page.getByLabel(t('account.birthYearLabel'))).toHaveValue('1985')

    // --- Document uploads: the ID scan and the CV ---------------------------
    // Each input is addressed by its own accessible name. A bare
    // input[type="file"] matched both cards once the CV card arrived, and an
    // index would silently target the wrong one again. Upload+replace also
    // covers a rerun where this account already has documents.
    const replaceButtons = page.getByRole('button', {
      name: t('account.documentReplace'),
    })

    await page.getByLabel(t('account.documentTitle')).setInputFiles(pdf())
    await expect(replaceButtons).toHaveCount(1)

    await page.getByLabel(t('account.cvTitle')).setInputFiles(pdf('cv.pdf'))
    await expect(replaceButtons).toHaveCount(2)

    // --- A minimal business so the admin has something to review -----------
    await page.goto('/dashboard/businesses/new')
    await page.getByLabel(t('form.name')).fill(fixture.businessName)
    await page.getByLabel(t('form.shortDescription')).fill(fixture.shortDescription)
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: categoryName }).click()
    await page.getByLabel(t('form.whatsapp')).fill(OWNER_PHONE)
    // Producer detail and the long description are optional at submission, so
    // they sit behind a disclosure (#34); open it before filling them.
    await page.getByText(t('form.optionalSectionTitle')).click()
    await page.getByLabel(t('form.institutionName')).fill(fixture.institutionName)
    await page.getByLabel(t('form.foundingDate')).fill('2004-03-15')
    await page.getByLabel(t('form.productionNature')).fill(fixture.productionNature)
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

    // The identity the owner typed on their account, read here on a listing.
    await expect(page.getByText(fixture.fullName)).toBeVisible()
    await expect(page.getByText(fixture.registrationPlace)).toBeVisible()

    // Producer detail belongs to the listing, and is published.
    await expect(page.getByText(fixture.institutionName)).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: t('admin.downloadDocument') }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('id.pdf')

    const cvDownloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: t('admin.downloadCv') }).click()
    expect((await cvDownloadPromise).suggestedFilename()).toBe('cv.pdf')
  })
})
