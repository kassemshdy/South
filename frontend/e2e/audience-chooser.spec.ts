import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { demoOwnerPhone, signIn } from './support/sign-in'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const t = (key: string): string => ar[key]!

const OWNER_PHONE = demoOwnerPhone('audience')

/**
 * The ways into the site.
 *
 * These cards are the homepage's navigation for anyone not confident online,
 * so the rule pinned here is that they are **always** there — no dismissal, no
 * memory, present on a return visit and present when signed in. It started out
 * as a once-only question; navigation you see once is not navigation.
 *
 * The second rule: choosing to list something explains the three steps before
 * asking for a phone number, because "sign in" is not an answer to "I have a
 * shop".
 *
 * The third, and the reason several of these tests have an extra click in
 * them: **the responsibility notice is the only way through an offering
 * door.** Listing something ends at a dealing between two strangers that the
 * platform does not stand behind, so the visitor reads that and agrees before
 * the page opens. Browsing carries none of that responsibility, so those
 * doors are real links straight through, with nothing in between. Pinned here
 * rather than trusted, because the failure mode is silent either way — an
 * offering door that quietly becomes a link skips the notice, and a browsing
 * door that quietly grows one adds a click nobody asked for.
 *
 * The second level replaces the first in place. A dialog was tried and read
 * as heavier than the choice deserves — these cards are navigation, and
 * navigation should not darken the page behind it to ask which of two
 * lists you want.
 *
 * Locators here use plain substrings rather than `new RegExp(...)`: the two
 * top-level labels carry a parenthesised aside, and `(` inside a RegExp is a
 * group rather than a bracket, so a pattern built from the label stops
 * matching the label.
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
    // rather than jumping straight to a form.
    // Two levels now: the intent first, then which kind.
    await page.getByRole('button', { name: t('home.actionOffer') }).click()
    await page.getByRole('button', { name: t('onboarding.ownerTitle') }).click()

    // The notice first, and it is the screen rather than a line on it.
    await expect(page.getByRole('heading', { name: t('consent.heading') })).toBeVisible()
    await expect(page.getByText(t('consent.body'))).toBeVisible()
    await page.getByRole('button', { name: t('consent.agree') }).click()

    await expect(page.getByText(t('onboarding.step1'))).toBeVisible()
    await expect(page.getByText(t('onboarding.step3'))).toBeVisible()
    expect(new URL(page.url()).pathname).toBe('/')

    // And only then does it offer the way in — the public application form,
    // not the login page. Somebody at this point has no account and no way to
    // get one except by applying, so /login was a door onto nothing.
    await page.getByRole('link', { name: t('onboarding.start') }).click()
    await expect(page).toHaveURL(/\/register\/business/)

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
    await page.getByRole('button', { name: t('home.actionOffer') }).click()
    await page.getByRole('button', { name: t('onboarding.ownerTitle') }).click()
    await page.getByRole('button', { name: t('consent.agree') }).click()

    await expect(page.getByText(t('onboarding.step1'))).toBeVisible()
    await expect(page.getByText(t('assisted.title'))).toHaveCount(0)
    await expect(page.getByRole('link', { name: t('assisted.cta') })).toHaveCount(0)
  })

  test('someone signed in gets the same doors, pointing at their dashboard', async ({
    page,
  }) => {
    await signIn(page, OWNER_PHONE)

    await page.goto('/')
    await expect(page.getByRole('heading', { name: t('onboarding.heading') })).toBeVisible()

    // Signed in, the header offers the account section and nothing after
    // it. It used to end in an "add your business" button, which sat beside
    // the account controls and made the bar appear to offer a way in and a
    // way further in at once. Adding a business is a task, not a greeting —
    // the card below is the route to it, which the rest of this test walks.
    const menu = page.getByRole('button', { name: t('nav.openMenu') })
    await menu.click()
    const mobileNav = page.getByRole('navigation', { name: t('nav.mobileAria') })
    await expect(mobileNav.getByRole('link', { name: t('nav.myBusinesses') })).toBeVisible()
    await expect(mobileNav.getByRole('link', { name: t('nav.addBusiness') })).toHaveCount(0)
    await expect(mobileNav.getByRole('link', { name: t('nav.login') })).toHaveCount(0)
    await page.getByRole('button', { name: t('nav.closeMenu') }).click()

    // No steps panel for someone who has already been through it: the card is
    // a link straight to the thing it describes.
    await page.getByRole('button', { name: t('home.actionOffer') }).click()
    await page.getByRole('button', { name: t('onboarding.ownerTitle') }).click()
    // Signed in, agreeing is the whole remaining step: no steps panel, and the
    // control is a real link straight to the wizard.
    await page.getByRole('link', { name: t('consent.agree') }).click()
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

  test('the buying half forks two ways, and backing out restores the question', async ({
    page,
  }) => {
    // Two doors, on the axis the board ticket named: goods and products, or
    // services and jobs. It offered three until that ticket — the businesses
    // directory had a card here too — and the cost of dropping to two is
    // asserted rather than assumed further down this test: the shops
    // directory is still reachable, just not from this fork.
    await page.goto('/')
    await page.getByRole('button', { name: t('home.actionBrowse') }).click()

    // Browsing doors are real links, not buttons: there is no notice ahead of
    // them to hold navigation back.
    for (const key of ['onboarding.seekGoodsTitle', 'onboarding.seekServiceTitle']) {
      await expect(page.getByRole('link', { name: t(key) })).toBeVisible()
    }
    await expect(
      page.getByRole('link', { name: t('browse.businessesTitle') }),
    ).toHaveCount(0)

    // Backing out is a real option, and it returns to the one question rather
    // than leaving the visitor in a half-answered state.
    await page.getByRole('button', { name: t('onboarding.back') }).click()
    await expect(page.getByRole('heading', { name: t('onboarding.heading') })).toBeVisible()

    // And the doors lead straight where they say -- browsing carries no
    // responsibility notice.
    await page.getByRole('button', { name: t('home.actionBrowse') }).click()
    await page.getByRole('link', { name: t('onboarding.seekGoodsTitle') }).click()
    await expect(page).toHaveURL(/\/products/)

    // The door this fork no longer offers, still one tap from the page it
    // sent us to. This is the whole argument for dropping to two, so it is
    // pinned next to the assertion that the card is gone.
    const strip = page.getByRole('navigation', { name: t('browse.switcherLabel') })
    await strip.getByRole('link', { name: t('browse.businessesShort') }).click()
    await expect(page).toHaveURL(/\/businesses/)
  })

  test('the notice is the only way through an offering door', async ({ page }) => {
    // The assertion that matters is the negative one: choosing a door must
    // not navigate. A door that regresses to a plain link still looks and
    // behaves correctly to anyone clicking through it — the notice simply
    // never appears — so "we are still on the homepage" is the line that
    // catches it.
    await page.goto('/')
    await page.getByRole('button', { name: t('home.actionOffer') }).click()
    await page.getByRole('button', { name: t('onboarding.talentTitle') }).click()

    await expect(page.getByRole('heading', { name: t('consent.heading') })).toBeVisible()
    expect(new URL(page.url()).pathname).toBe('/')

    // Backing out of the notice returns to the two doors and navigates
    // nowhere: declining is a real answer, not a dead end.
    await page.getByRole('button', { name: t('onboarding.back') }).click()
    await expect(page.getByRole('button', { name: t('onboarding.ownerTitle') })).toBeVisible()
    expect(new URL(page.url()).pathname).toBe('/')

    // And agreeing carries on to the steps panel — anonymous, so there is no
    // direct link to the wizard yet.
    await page.getByRole('button', { name: t('onboarding.talentTitle') }).click()
    await page.getByRole('button', { name: t('consent.agree') }).click()
    await expect(page.getByText(t('onboarding.step1'))).toBeVisible()
  })

  test('choosing to browse goes straight through, with no notice in the way', async ({
    page,
  }) => {
    // The opposite claim from the test above, on the other half: browsing
    // carries no responsibility to accept, so a door here is a real link with
    // nothing between it and the page it names — no heading, no agree button,
    // ever rendered.
    await page.goto('/')
    await page.getByRole('button', { name: t('home.actionBrowse') }).click()
    await page.getByRole('link', { name: t('onboarding.seekServiceTitle') }).click()

    await expect(page).toHaveURL(/\/talent/)
    await expect(page.getByRole('heading', { name: t('consent.heading') })).toHaveCount(0)
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

  test('the video comes before the question, not after it', async ({ page }) => {
    // A deliberate order, and the two layouts used to disagree about it: on a
    // phone the cards came second and the player last, while from `lg` up the
    // player shared the first row and the cards took the second. The video is
    // the pitch, and it only does its job if it is what you meet before being
    // asked to choose — so it is now first on both.
    //
    // Asserted by geometry rather than by DOM order, because `order-*` classes
    // are exactly what moves here: the markup can stay put while the rendered
    // page flips.
    await page.goto('/')
    const player = page.getByRole('button', { name: t('home.videoPlayAria') })
    const question = page.getByRole('heading', { name: t('onboarding.heading') })
    await expect(player).toBeVisible()
    await expect(question).toBeVisible()

    const playerBox = await player.boundingBox()
    const questionBox = await question.boundingBox()
    expect(playerBox!.y).toBeLessThan(questionBox!.y)
  })
})
