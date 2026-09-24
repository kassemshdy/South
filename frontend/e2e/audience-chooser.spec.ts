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
 * **Each half is a page.** This is the rule that replaced "the second level
 * replaces the first in place", and it replaced it on the CEO's reading of
 * the screen: choosing a card used to swap two boxes while the hero, the
 * video and everything below stayed put, so the most consequential choice on
 * the site read as a toggle rather than as going somewhere. The old shape
 * also had no URL — the back button left the homepage instead of stepping
 * back, nothing could be sent to somebody over WhatsApp, and no search engine
 * saw a word of it. Those three are asserted below, because a regression to
 * an in-place panel would look correct to anyone clicking through it.
 *
 * The second rule, unchanged: choosing to list something explains who may
 * list and the three steps before asking for a phone number, because "sign
 * in" is not an answer to "I have a shop".
 *
 * The third, and the reason several of these tests have an extra click in
 * them: **both sides read the responsibility notice.** A dealing here ends
 * between two strangers the platform does not stand behind, and that is as
 * true of the person buying as of the person selling — so each half asks
 * before it opens. This half of the rule is new: browsing used to go straight
 * through on the reasoning that it carried no responsibility to accept, and
 * the CEO's correction was that trusting a stranger's description of a thing
 * is exactly such a responsibility.
 *
 * What differs between the two is only what is left out. `consent.body`
 * carries clauses that are the lister's alone — what you publish is yours,
 * and a proven violation removes you — and `consent.buyerBody` drops them,
 * because repeating them at a buyer teaches people to skip the box. Pinned
 * here rather than trusted, because a door that quietly regresses to a plain
 * link still behaves correctly to anyone clicking through it; the notice
 * simply never appears.
 *
 * Locators here use plain substrings rather than `new RegExp(...)`: the two
 * top-level labels carry a parenthesised aside, and `(` inside a RegExp is a
 * group rather than a bracket, so a pattern built from the label stops
 * matching the label.
 */
test.describe('Audience chooser', () => {
  test('both halves are real pages, reachable and reversible', async ({ page }) => {
    await page.goto('/')

    const question = page.getByRole('heading', { name: t('onboarding.heading') })
    await expect(question).toBeVisible()

    // Not a wall: the homepage below it is present and reachable without
    // answering anything.
    await expect(page.getByRole('heading', { name: t('home.heroTitle') })).toBeVisible()

    // Links, not buttons — the whole point of the change. A regression to an
    // in-place panel fails right here.
    await page.getByRole('link', { name: t('home.actionOffer') }).click()
    await expect(page).toHaveURL(/\/offer/)
    await expect(page.getByRole('heading', { name: t('offerPage.title') })).toBeVisible()

    // The browser's own back button steps back, which it could not do when
    // this was a state machine on the homepage.
    await page.goBack()
    await expect(page).toHaveURL(/\/$/)
    await expect(question).toBeVisible()

    // And the page offers its own way home, above the content rather than
    // buried under it.
    await page.getByRole('link', { name: t('home.actionOffer') }).click()
    await page.getByRole('link', { name: t('choice.backHome') }).click()
    await expect(question).toBeVisible()
  })

  test('the offer page says who may list before it asks for anything', async ({ page }) => {
    // The platform is open to southerners in its first phase. Somebody who
    // does not qualify must find that out here, not after filling a form and
    // waiting for a rejection — so the rule is on the page, above the doors.
    await page.goto('/offer')

    await expect(
      page.getByRole('heading', { name: t('offerPage.eligibilityTitle') }),
    ).toBeVisible()
    await expect(page.getByText(t('offerPage.eligibilityOne'))).toBeVisible()
    await expect(page.getByText(t('offerPage.eligibilityTwo'))).toBeVisible()
    await expect(page.getByText(t('offerPage.eligibilityNote'))).toBeVisible()

    // The three steps are on the page too, not hidden behind a click.
    await expect(page.getByText(t('onboarding.step1'))).toBeVisible()
    await expect(page.getByText(t('onboarding.step3'))).toBeVisible()
  })

  test('explains before signing in, and ends at the application form', async ({ page }) => {
    await page.goto('/offer')
    await page.getByRole('button', { name: t('onboarding.ownerTitle') }).click()

    // The notice first, and it is the screen rather than a line on it.
    await expect(page.getByRole('heading', { name: t('consent.heading') })).toBeVisible()
    await expect(page.getByText(t('consent.body'))).toBeVisible()
    await page.getByRole('button', { name: t('consent.agree') }).click()

    await expect(page.getByText(t('onboarding.step1'))).toBeVisible()
    await expect(page.getByText(t('onboarding.step3'))).toBeVisible()

    // And only then does it offer the way in — the public application form,
    // not the login page. Somebody at this point has no account and no way to
    // get one except by applying, so /login was a door onto nothing.
    await page.getByRole('link', { name: t('onboarding.start') }).click()
    await expect(page).toHaveURL(/\/register\/business/)

    // Still there on the way back — permanent navigation, not a prompt that
    // spends itself on first use.
    await page.goto('/')
    await expect(page.getByRole('heading', { name: t('onboarding.heading') })).toBeVisible()
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
    await page.goto('/offer')
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

    // No steps panel for someone who has already been through it: agreeing is
    // the whole remaining step, and the control is a real link.
    await page.getByRole('link', { name: t('home.actionOffer') }).click()
    await page.getByRole('button', { name: t('onboarding.ownerTitle') }).click()
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

  test('the buying half forks two ways on its own page', async ({ page }) => {
    // Two doors, on the axis the board ticket named: goods and products, or
    // services and jobs. It offered three until that ticket — the businesses
    // directory had a card here too — and the cost of dropping to two is
    // asserted rather than assumed further down this test: the shops
    // directory is still reachable, just not from this fork.
    await page.goto('/')
    await page.getByRole('link', { name: t('home.actionBrowse') }).click()
    await expect(page).toHaveURL(/\/browse/)

    // The buyer reads the same warning the seller does, minus the clauses
    // that are the seller's alone. Both sides of a dealing, one warning.
    await expect(page.getByText(t('consent.buyerBody'))).toBeVisible()
    await page.getByRole('button', { name: t('consent.agree') }).click()

    // Past the notice the doors are real links, with nothing further between
    // them and the directory they name.
    for (const key of ['onboarding.seekGoodsTitle', 'onboarding.seekServiceTitle']) {
      await expect(page.getByRole('link', { name: t(key) })).toBeVisible()
    }
    await expect(
      page.getByRole('link', { name: t('browse.businessesTitle') }),
    ).toHaveCount(0)

    // And the doors lead straight where they say -- browsing carries no
    // responsibility notice.
    await page.getByRole('link', { name: t('onboarding.seekGoodsTitle') }).click()
    await expect(page).toHaveURL(/\/products/)

    // The door this fork no longer offers, still one tap from the page it
    // sent us to. This is the whole argument for dropping to two, so it is
    // pinned next to the assertion that the card is gone.
    const strip = page.getByRole('navigation', { name: t('browse.switcherLabel') })
    await strip.getByRole('link', { name: t('browse.businessesShort') }).click()
    await expect(page).toHaveURL(/\/businesses/)
  })

  test('goods made in the South and imported goods are separate doors, on both halves', async ({
    page,
  }) => {
    // At the CEO's request: a southern store selling imported goods is
    // welcome, but under its own door, so a buyer looking for what the South
    // produces is never shown an import under that heading. The mark is the
    // business's `goods_origin`, set by the door the owner came through.
    //
    // Anchored to the start of the card: the local door's own description
    // mentions imported goods, so a plain substring would match both cards.
    const startsWith = (key: string) =>
      new RegExp(`^${t(key).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`)

    await page.goto('/offer')
    await expect(page.getByRole('button', { name: startsWith('onboarding.ownerTitle') })).toBeVisible()
    await page.getByRole('button', { name: startsWith('onboarding.importedTitle') }).click()
    await page.getByRole('button', { name: t('consent.agree') }).click()
    await page.getByRole('link', { name: t('onboarding.start') }).click()

    // The application form opens on the door chosen, and says so.
    await expect(page).toHaveURL(/\/register\/business\?origin=IMPORTED/)
    await expect(page.getByRole('combobox', { name: t('offerPage.doorsTitle') })).toHaveText(
      t('onboarding.importedTitle'),
    )

    // The looking-for half has the same split, each onto its own page --
    // an address that can be sent to somebody, headed with the title the CEO
    // chose for it so the narrowing is never silent.
    await page.goto('/browse')
    await page.getByRole('button', { name: t('consent.agree') }).click()
    await expect(page.getByRole('link', { name: startsWith('onboarding.ownerTitle') })).toBeVisible()
    await page.getByRole('link', { name: startsWith('onboarding.importedTitle') }).click()
    await expect(page).toHaveURL(/\/products\/imported$/)
    await expect(
      page.getByRole('heading', { level: 1, name: t('products.importedPageTitle') }),
    ).toBeVisible()

    // The whole directory still offers the same narrowing as a filter, and
    // shows it when a link arrives with one set.
    await page.goto('/products?origin=IMPORTED')
    await expect(page.getByRole('combobox', { name: t('directory.origin') })).toHaveText(
      t('onboarding.importedTitle'),
    )
  })

  test('a step change puts the top of the page back in view', async ({ page }) => {
    // `ScrollToTop` keys off the pathname, and the steps inside these two
    // pages are state rather than routes — so it never fired for them. The
    // doors sit far down a long page and the notice that replaces them is
    // short, which left the notice's own heading 458px above the viewport:
    // the visitor pressed a card and, as far as they could see, nothing
    // happened.
    await page.goto('/offer')
    const door = page.getByRole('button', { name: t('onboarding.ownerTitle') })
    await door.scrollIntoViewIfNeeded()
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0)

    await door.click()
    await expect(page.getByRole('heading', { name: t('consent.heading') })).toBeVisible()
    expect(await page.evaluate(() => window.scrollY)).toBe(0)

    // And again on the next step, which is a second state change.
    await page.getByRole('button', { name: t('consent.agree') }).click()
    await expect(page.getByText(t('onboarding.step1'))).toBeVisible()
    expect(await page.evaluate(() => window.scrollY)).toBe(0)

    // The browsing half has one such step, and it behaves the same.
    await page.goto('/browse')
    await page.evaluate(() => window.scrollTo(0, 400))
    await page.getByRole('button', { name: t('consent.agree') }).click()
    await expect(page.getByRole('link', { name: t('onboarding.seekGoodsTitle') })).toBeVisible()
    expect(await page.evaluate(() => window.scrollY)).toBe(0)
  })

  test('the notice is the only way through an offering door', async ({ page }) => {
    // The assertion that matters is the negative one: choosing a door must
    // not navigate. A door that regresses to a plain link still looks and
    // behaves correctly to anyone clicking through it — the notice simply
    // never appears — so "we are still on /offer" is the line that catches it.
    await page.goto('/offer')
    await page.getByRole('button', { name: t('onboarding.talentTitle') }).click()

    await expect(page.getByRole('heading', { name: t('consent.heading') })).toBeVisible()
    expect(new URL(page.url()).pathname).toBe('/offer')

    // Backing out of the notice returns to the two doors and navigates
    // nowhere: declining is a real answer, not a dead end.
    await page.getByRole('button', { name: t('onboarding.back') }).click()
    await expect(page.getByRole('button', { name: t('onboarding.ownerTitle') })).toBeVisible()
    expect(new URL(page.url()).pathname).toBe('/offer')

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
    await page.goto('/browse')
    await page.getByRole('button', { name: t('consent.agree') }).click()
    await page.getByRole('link', { name: t('onboarding.seekServiceTitle') }).click()

    // Answered once, the notice does not reappear between the door and the
    // directory: the gate is the page, not every link on it.
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
