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
 *
 * The second level replaces the first in place. A dialog was tried and read
 * as heavier than the choice deserves — these cards are navigation, and
 * navigation should not darken the page behind it to ask which of three
 * lists you want.
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
    // Two levels now: the intent first, then which kind.
    await page.getByRole('button', { name: new RegExp(t('home.actionOffer')) }).click()
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
    // Two levels now: the intent first, then which kind.
    await page.getByRole('button', { name: new RegExp(t('home.actionOffer')) }).click()
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

    // Signed in, the header's call to action is the shortcut into the wizard.
    const menu = page.getByRole('button', { name: t('nav.openMenu') })
    await menu.click()
    const mobileNav = page.getByRole('navigation', { name: t('nav.mobileAria') })
    await expect(mobileNav.getByRole('link', { name: t('nav.addBusiness') })).toBeVisible()
    await page.getByRole('button', { name: t('nav.closeMenu') }).click()

    // No steps panel for someone who has already been through it: the card is
    // a link straight to the thing it describes.
    await page.getByRole('button', { name: new RegExp(t('home.actionOffer')) }).click()
    await page.getByRole('link', { name: new RegExp(t('onboarding.ownerTitle')) }).click()
    await expect(page).toHaveURL(/\/dashboard\/businesses\/new/)

    // And the fork is still reachable from inside the wizard, for someone who
    // realises here that they are a craftsperson rather than a shop. Only
    // until the first save — after that a DRAFT listing exists and walking
    // away would strand it.
    const adding = page.getByRole('navigation', { name: t('onboarding.offerSwitcherLabel') })
    await expect(adding).toBeVisible()
    await adding.getByRole('link', { name: t('onboarding.talentShort') }).click()
    await expect(page).toHaveURL(/\/dashboard\/talent/)
  })

  test('the buying half offers all three directories, and backing out restores the question', async ({
    page,
  }) => {
    // The half that was wrong on the live site in a quieter way: it offered
    // goods and someone-skilled, and simply had no door to the businesses
    // directory at all. Someone who wanted the bakery on the corner had to
    // find it through a product.
    await page.goto('/')
    await page.getByRole('button', { name: new RegExp(t('home.actionBrowse')) }).click()

    for (const key of [
      'browse.businessesTitle',
      'onboarding.seekGoodsTitle',
      'onboarding.seekServiceTitle',
    ]) {
      await expect(page.getByRole('link', { name: new RegExp(t(key)) })).toBeVisible()
    }

    // Backing out is a real option, and it returns to the one question rather
    // than leaving the visitor in a half-answered state.
    await page.getByRole('button', { name: t('onboarding.back') }).click()
    await expect(page.getByRole('heading', { name: t('onboarding.heading') })).toBeVisible()

    // And the doors lead where they say.
    await page.getByRole('button', { name: new RegExp(t('home.actionBrowse')) }).click()
    await page.getByRole('link', { name: new RegExp(t('browse.businessesTitle')) }).click()
    await expect(page).toHaveURL(/\/businesses/)
  })

  test('the header asks a signed-out visitor to sign in, not to open a shop', async ({
    page,
  }) => {
    // It used to say `nav.addBusiness` and go to `/login` anyway, so the one
    // call to action in the chrome told a craftsperson, a customer and a
    // shopkeeper alike that the thing to do here is open a shop — the same
    // assumption the hero card made, in the one place that is on every page.
    await page.goto('/')
    await page.getByRole('button', { name: t('nav.openMenu') }).click()

    const mobileNav = page.getByRole('navigation', { name: t('nav.mobileAria') })
    const signIn = mobileNav.getByRole('link', { name: t('nav.login') })
    await expect(signIn).toBeVisible()
    await expect(signIn).toHaveAttribute('href', '/login')
    await expect(mobileNav.getByRole('link', { name: t('nav.addBusiness') })).toHaveCount(0)
  })
})
