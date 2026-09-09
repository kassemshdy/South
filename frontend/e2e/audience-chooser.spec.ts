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
 * The three ways into the site.
 *
 * These cards are the homepage's navigation for anyone not confident online,
 * so the rule pinned here is that they are **always** there — no dismissal, no
 * memory, present on a return visit and present when signed in. It started out
 * as a once-only question; navigation you see once is not navigation.
 *
 * The other rule: choosing to list something explains the three steps before
 * asking for a phone number, because "sign in" is not an answer to "I have a
 * shop".
 */
test.describe('Audience chooser', () => {
  test('is always there, explains before signing in, and never blocks the page', async ({
    page,
  }) => {
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

    // Still there on the way back — permanent navigation, not a prompt that
    // spends itself on first use.
    await page.goto('/')
    await expect(question).toBeVisible()
  })

  test('the assisted-listing offer is absent until a support number is configured', async ({
    page,
  }) => {
    // The rule every optional integration here follows: nothing at all when
    // its variable is unset -- no link, no half-configured block. This suite
    // runs without VITE_SUPPORT_WHATSAPP, which is exactly the state that
    // needs guarding: a "contact us" pointing nowhere is worse than none,
    // because it spends the one attempt a hesitant person was willing to
    // make. The positive case cannot be asserted here -- Vite inlines the
    // value at build time, so it would need a second build -- but the
    // failure that actually costs someone a listing is this one.
    await page.goto('/')
    await page.getByRole('button', { name: new RegExp(t('onboarding.ownerTitle')) }).click()

    await expect(page.getByText(t('onboarding.step1'))).toBeVisible()
    await expect(page.getByText(t('assisted.title'))).toHaveCount(0)
    await expect(page.getByRole('link', { name: t('assisted.cta') })).toHaveCount(0)
  })

  test('someone signed in gets the same three routes, pointing at their dashboard', async ({
    page,
  }) => {
    await page.goto('/login')
    await page.getByLabel(t('login.phoneLabel')).fill(OWNER_PHONE)
    await page.getByRole('button', { name: t('login.sendCode') }).click()
    await page.getByLabel(t('login.codeLabel')).fill(DEV_OTP)
    await page.getByRole('button', { name: t('login.confirm') }).click()
    await expect(page).toHaveURL(/\/dashboard/)

    await page.goto('/')
    await expect(page.getByRole('heading', { name: t('onboarding.heading') })).toBeVisible()

    // No steps panel for someone who has already been through it: the card is
    // a link straight to the thing it describes.
    await page.getByRole('link', { name: new RegExp(t('onboarding.ownerTitle')) }).click()
    await expect(page).toHaveURL(/\/dashboard\/businesses\/new/)
  })
})
