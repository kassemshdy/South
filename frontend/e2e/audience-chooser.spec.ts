import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const t = (key: string): string => ar[key]!

const OWNER_PHONE = '03966401'
const DEV_OTP = '123456'

/**
 * The first question the site asks.
 *
 * The two rules it must not break are behavioural, not visual, so they are
 * pinned here: it never blocks the content behind it, and it is asked once.
 * The third is that choosing to list something explains the three steps before
 * asking for a phone number — the point of the whole issue was that "sign in"
 * is not an answer to "I have a shop".
 */
test.describe('Audience chooser', () => {
  test('asks once, explains before signing in, and never blocks the page', async ({ page }) => {
    await page.goto('/')

    const question = page.getByRole('heading', { name: t('onboarding.heading') })
    await expect(question).toBeVisible()

    // Not a wall: the homepage below it is present and reachable without
    // answering anything.
    await expect(page.getByRole('heading', { name: t('home.heroTitle') })).toBeVisible()

    // Choosing to list a business explains what that involves, in place,
    // rather than jumping to a phone-number prompt.
    await page.getByRole('button', { name: new RegExp(t('onboarding.ownerTitle')) }).click()
    await expect(page.getByText(t('onboarding.step1'))).toBeVisible()
    await expect(page.getByText(t('onboarding.step3'))).toBeVisible()
    expect(new URL(page.url()).pathname).toBe('/')

    // And only then does it offer the way in.
    await page.getByRole('link', { name: t('onboarding.start') }).click()
    await expect(page).toHaveURL(/\/login/)

    // Answering is remembered, so a returning visitor gets the site rather
    // than the question again.
    await page.goto('/')
    await expect(question).toHaveCount(0)
  })

  test('skipping is one tap and it stays skipped', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: t('onboarding.dismiss') }).click()

    const question = page.getByRole('heading', { name: t('onboarding.heading') })
    await expect(question).toHaveCount(0)

    // The regression this catches: a dismissal that does not round-trip
    // through storage turns a one-time question into a nag on every visit.
    await page.reload()
    await expect(question).toHaveCount(0)
    await expect(page.getByRole('heading', { name: t('home.heroTitle') })).toBeVisible()
  })

  test('someone already signed in is never asked', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(t('login.phoneLabel')).fill(OWNER_PHONE)
    await page.getByRole('button', { name: t('login.sendCode') }).click()
    await page.getByLabel(t('login.codeLabel')).fill(DEV_OTP)
    await page.getByRole('button', { name: t('login.confirm') }).click()
    await expect(page).toHaveURL(/\/dashboard/)

    await page.goto('/')
    // Having an account answers the question by existing.
    await expect(page.getByRole('heading', { name: t('onboarding.heading') })).toHaveCount(0)
  })
})
