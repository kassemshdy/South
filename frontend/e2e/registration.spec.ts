import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { ADMIN_EMAIL, ADMIN_PASSWORD } from './support/admin'
import { dropPin } from './support/map'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const fixture = load<{
  businessName: string
  shortDescription: string
  loginPhone: string
  chosenPassword: string
  resetPassword: string
  fullName: string
  birthYear: string
  registrationPlace: string
  residencePlace: string
}>('./fixtures/registration-data.json')
const t = (key: string): string => ar[key]!

/** A one-pixel PNG. The API sniffs magic bytes, so it has to be a real one. */
const PNG_BYTES = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
)


/**
 * The only way onto this site.
 *
 * There is no SMS or WhatsApp gateway, so every listing arrives this way:
 * somebody applies on a public form, choosing the password for their account
 * as they do (round 3), and an administrator confirms them on WhatsApp before
 * anything is published. Nothing else in this suite covers it, and it is the
 * path every real owner takes.
 *
 * The claims, each of which would be a live incident if it stopped holding:
 *
 * - an application is **not published** before a person has looked at it,
 *   though its applicant can sign in and see it under review;
 * - an administrator can still hand over a password -- a reset now -- without
 *   the site sending anything, and the WhatsApp message carries both values;
 * - that handed-over password opens **one screen** and nothing else until it
 *   is replaced, and it ends the session opened with the old one;
 * - replacing it reaches the dashboard, with the listing there.
 */
test.describe('Applying for a listing', () => {
  test('a visitor applies with their own password, an admin audits, a reset still works', async ({
    page,
    browser,
  }) => {
    // --- 1. Apply, with no account ------------------------------------------
    await page.goto('/register/business')
    await expect(
      page.getByRole('heading', { name: t('register.businessTitle') }),
    ).toBeVisible()

    // The sequence is stated before the first input, because it is not the one
    // people expect: nothing here goes live, and the login arrives later.
    await expect(page.getByText(t('register.stepReview'))).toBeVisible()
    await expect(page.getByText(t('register.stepCredentials'))).toBeVisible()

    await page.getByLabel(t('register.loginPhoneLabel')).fill(fixture.loginPhone)
    // The password is chosen here now; exact, because the confirmation's
    // label contains this one.
    await page
      .getByRole('textbox', { name: t('register.passwordLabel'), exact: true })
      .fill(fixture.chosenPassword)
    await page
      .getByRole('textbox', { name: t('register.passwordConfirmLabel'), exact: true })
      .fill(fixture.chosenPassword)

    // Who they are, asked here because the reviewer is about to decide
    // whether this is a real person from the South.
    await page.getByLabel(t('account.fullNameLabel')).fill(fixture.fullName)
    await page.getByLabel(t('account.birthYearLabel')).fill(fixture.birthYear)
    await page.getByLabel(t('account.registrationPlaceLabel')).fill(fixture.registrationPlace)
    await page.getByLabel(t('account.residencePlaceLabel')).fill(fixture.residencePlace)
    // Required, and for the team only: whether they are displaced right now.
    await page
      .getByRole('group', { name: t('account.displacedLabel') })
      .getByText(t('common.no'), { exact: true })
      .click()

    // Both sides of the ID travel with the application: there is no account
    // to upload them to yet, and the reviewer is about to decide whether the
    // four fields above describe a real person.
    const scans = page.locator('input[type="file"]')
    await scans.nth(0).setInputFiles({
      name: 'front.png',
      mimeType: 'image/png',
      buffer: PNG_BYTES,
    })
    await scans.nth(1).setInputFiles({
      name: 'back.png',
      mimeType: 'image/png',
      buffer: PNG_BYTES,
    })

    await page.getByLabel(t('form.name')).fill(fixture.businessName)
    await page.getByLabel(t('form.shortDescription')).fill(fixture.shortDescription)
    await page.locator('button[role="combobox"]').first().click()
    await page.locator('[role="option"]').first().click()
    // The area is asked for here now, and required.
    await page.getByLabel(t('form.area')).click()
    await page.getByRole('option').nth(1).click()
    // Every seller pins themselves on the map; a tap anywhere drops it.
    await dropPin(page, t('form.mapPinLabel'))

    // The responsibility notice is on this page now (round 3), and nothing
    // is sent until it is agreed to.
    await page.getByRole('button', { name: t('register.submit') }).click()
    await expect(page.getByText(t('validation.consentRequired'))).toBeVisible()
    await expect(page.getByRole('heading', { name: t('register.doneTitle') })).toHaveCount(0)
    await page.getByRole('checkbox', { name: t('consent.agree') }).check()
    await page.getByRole('button', { name: t('register.submit') }).click()

    await expect(page.getByRole('heading', { name: t('register.doneTitle') })).toBeVisible()

    // --- 2. Not published, but its applicant can sign in and see it ----------
    await page.goto(`/businesses?q=${encodeURIComponent(fixture.businessName)}`)
    await expect(page.getByText(fixture.businessName)).toHaveCount(0)

    await page.goto('/login')
    await page.getByLabel(t('login.identifierLabel')).fill(fixture.loginPhone)
    await page.getByLabel(t('login.passwordLabel')).fill(fixture.chosenPassword)
    await page.getByRole('button', { name: t('login.signIn'), exact: true }).click()
    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByText(fixture.businessName).first()).toBeVisible()
    await expect(page.getByText(t('status.PENDING_REVIEW')).first()).toBeVisible()
    // Signed out again for what follows: the issued password below is a reset.
    await page.evaluate(() => window.localStorage.clear())

    // --- 3. An administrator audits it, and can reset the password ----------
    // A separate context, not another tab: the session token lives in this
    // origin's local storage, so an administrator signing in beside the
    // applicant would replace them — and the rest of this test would be
    // checking what an administrator can do, which is not the claim.
    const adminContext = await browser.newContext({ locale: 'ar-LB' })
    const admin = await adminContext.newPage()
    await admin.goto('/admin/login')
    await admin.getByLabel(t('adminLogin.email')).fill(ADMIN_EMAIL)
    await admin.getByLabel(t('adminLogin.password')).fill(ADMIN_PASSWORD)
    await admin.getByRole('button', { name: t('adminLogin.submit') }).click()
    await expect(
      admin.getByRole('heading', { name: t('admin.dashboardHeading') }),
    ).toBeVisible()

    // The queue is oldest-first, so target this application's row rather than
    // whichever one happens to be at the top.
    await admin.goto('/admin/businesses')
    await admin
      .getByRole('listitem')
      .filter({ hasText: fixture.businessName })
      .getByRole('link', { name: t('admin.review') })
      .click()
    await expect(admin.getByRole('heading', { name: fixture.businessName })).toBeVisible()

    // The login number the applicant gave is the account's, and the reviewer
    // can see it — it is what they are about to send the credentials to.
    await expect(admin.getByText('+9613977012').first()).toBeVisible()

    // So is who they said they are: the whole point of asking on the form is
    // that it is on this screen when the decision is made.
    await expect(admin.getByText(fixture.fullName).first()).toBeVisible()
    await expect(admin.getByText(fixture.residencePlace).first()).toBeVisible()

    // And both sides they attached, which is what the reviewer checks those
    // against — downloaded here rather than merely present, because a
    // document that cannot be opened is not evidence.
    const frontDownload = admin.waitForEvent('download')
    await admin.getByRole('button', { name: t('admin.downloadDocument') }).click()
    expect((await frontDownload).suggestedFilename()).toBe('front.png')

    const backDownload = admin.waitForEvent('download')
    await admin.getByRole('button', { name: t('admin.downloadDocumentBack') }).click()
    expect((await backDownload).suggestedFilename()).toBe('back.png')

    await admin.getByRole('button', { name: t('credentials.issue') }).click()
    await expect(admin.getByText(t('credentials.onceWarning'))).toBeVisible()

    const issued = (await admin.locator('dd.font-mono').innerText()).trim()
    expect(issued.length).toBeGreaterThan(8)

    // The site sends nothing. What it produces is a wa.me link the
    // administrator opens themselves, carrying both values the owner needs.
    const whatsapp = await admin
      .getByRole('link', { name: t('credentials.sendOnWhatsapp') })
      .getAttribute('href')
    expect(whatsapp).toContain('wa.me/')
    expect(decodeURIComponent(whatsapp ?? '')).toContain(issued)

    // --- 4. The issued password replaces the chosen one, and opens one screen -
    await page.goto('/login')
    await page.getByLabel(t('login.identifierLabel')).fill(fixture.loginPhone)
    await page.getByLabel(t('login.passwordLabel')).fill(fixture.chosenPassword)
    await page.getByRole('button', { name: t('login.signIn'), exact: true }).click()
    await expect(page).not.toHaveURL(/\/dashboard/)

    await page.goto('/login')
    await page.getByLabel(t('login.identifierLabel')).fill(fixture.loginPhone)
    await page.getByLabel(t('login.passwordLabel')).fill(issued)
    await page.getByRole('button', { name: t('login.signIn'), exact: true }).click()
    await expect(page).toHaveURL(/\/change-password/)

    // Not around it, either: the dashboard bounces straight back.
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/change-password/)

    // --- 5. Choosing their own password reaches the dashboard ---------------
    // By autocomplete rather than by label: the confirmation field's label
    // contains the new password field's, so a label lookup matches both.
    await page.getByLabel(t('password.currentLabel')).fill(issued)
    const chosen = page.locator('input[autocomplete="new-password"]')
    await chosen.nth(0).fill(fixture.resetPassword)
    await chosen.nth(1).fill(fixture.resetPassword)
    await page.getByRole('button', { name: t('password.submit') }).click()

    await expect(page).toHaveURL(/\/dashboard$/)
    await expect(page.getByText(fixture.businessName)).toBeVisible()

    await adminContext.close()
  })
})
