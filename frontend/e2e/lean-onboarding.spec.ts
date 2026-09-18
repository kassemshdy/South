import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { openBusinessWizard } from './support/wizard'

import { signInWithCode } from './support/sign-in'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const fixture = load<{ name: string; shortDescription: string }>(
  './fixtures/lean-onboarding-data.json',
)
const t = (key: string): string => ar[key]!

const OWNER_PHONE = '03966501'

// The same tiny-but-valid JPEG the acceptance spec uses. The upload sniffs
// real magic bytes and rejects anything it cannot decode, so a hand-rolled
// stub silently uploads nothing — which is exactly how this spec first failed.
const JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a' +
    'HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAAKAAoBAREA/8QAHwAAAQUBAQEB' +
    'AQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1Fh' +
    'ByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZ' +
    'WmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXG' +
    'x8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oACAEBAAA/APn+iiiv/9k=',
  'base64',
)

/**
 * The lean path to review.
 *
 * `SUBMISSION_REQUIREMENTS` in `app/services/business.py` asks for six things:
 * a name, a short description, a category, an area, a logo and one contact
 * number. The wizard was six steps, two of them entirely optional, with those
 * six requirements scattered across three — so the shortest real path looked
 * like the longest possible one to exactly the person least likely to push
 * through it.
 *
 * This pins the two claims that fix makes: the optional fields are out of the
 * way until asked for, and the moment a listing is genuinely submittable the
 * owner is told, rather than walked through steps that cannot block them.
 */
test.describe('Lean onboarding', () => {
  test('an owner reaches review without touching an optional step', async ({ page }) => {
    await signInWithCode(page, OWNER_PHONE)

    await openBusinessWizard(page)

    // The optional fields are present but collapsed: a long description is not
    // required to be reviewed, so it does not share a column with the fields
    // that are.
    await expect(page.getByLabel(t('form.name'))).toBeVisible()
    await expect(page.getByLabel(t('form.description'))).toBeHidden()
    await page.getByText(t('form.optionalSectionTitle')).click()
    await expect(page.getByLabel(t('form.description'))).toBeVisible()

    // The two steps nothing depends on say so, before they are walked into.
    const optionalChips = page.getByRole('button', { name: new RegExp(t('wizard.optionalStep')) })
    await expect(optionalChips).toHaveCount(2)

    // --- Required basics only ------------------------------------------------
    await page.getByLabel(t('form.name')).fill(fixture.name)
    await page.getByLabel(t('form.shortDescription')).fill(fixture.shortDescription)
    await page.getByRole('combobox').first().click()
    await page.getByRole('option').nth(1).click()
    await page.getByLabel(t('form.whatsapp')).fill(OWNER_PHONE)
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    // Not ready yet — an area and a logo are still missing, and claiming
    // otherwise would send an owner into a rejection.
    await expect(page.getByLabel(t('form.area'))).toBeVisible()
    await expect(page.getByText(t('wizard.readyTitle'))).toHaveCount(0)

    // --- Area ----------------------------------------------------------------
    await page.getByRole('combobox').first().click()
    await page.getByRole('option').nth(1).click()
    await page.getByRole('button', { name: t('wizard.saveAndContinue') }).click()

    // --- Logo, which completes the required set ------------------------------
    await expect(page.getByRole('heading', { name: t('images.logoTitle') })).toBeVisible()
    await expect(page.getByText(t('wizard.readyTitle'))).toHaveCount(0)
    await page.locator('input[type="file"]').first().setInputFiles({
      name: 'logo.jpg',
      mimeType: 'image/jpeg',
      buffer: JPEG,
    })
    // Wait for the upload to actually land before judging readiness.
    await expect(page.getByText(t('images.uploaded'), { exact: true }).first()).toBeVisible()

    // The moment it is submittable, the owner is told — while still standing
    // on the images step, two optional steps short of the old route.
    await expect(page.getByText(t('wizard.readyTitle'))).toBeVisible()
    await page.getByRole('button', { name: t('wizard.readyCta') }).click()

    // And the backend agrees: nothing is missing.
    await expect(page.getByText(t('wizard.allComplete'))).toBeVisible()
    await expect(page.getByText(t('wizard.missingTitle'))).toHaveCount(0)
  })
})
