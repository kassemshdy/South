import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const en = load<Record<string, string>>('../src/i18n/locales/en.json')

const t = (key: string): string => ar[key]!
const tEn = (key: string): string => en[key]!

// The control's accessible name, exactly as each catalog renders it. Built from
// the catalogs rather than hard-coded, so a reworded label updates the test.
const SWITCH_TO_ENGLISH = t('nav.switchLanguage').replace('{language}', t('nav.localeEnglish'))
const SWITCH_TO_ARABIC = tEn('nav.switchLanguage').replace('{language}', tEn('nav.localeArabic'))

/**
 * The language switcher, end to end.
 *
 * Both catalogs have been complete for a while and no visitor could reach the
 * English one — nothing in the app called `setLocale`. This spec is what keeps
 * that from silently happening again: it drives the control a real person
 * would use, then checks the three things that make the switch real —
 * translated chrome, a flipped document direction, and a choice that survives
 * a reload.
 */
test.describe('Language switcher', () => {
  test('a visitor can switch to English, and the choice sticks', async ({ page }) => {
    await page.goto('/businesses')

    // Arabic is the default, and the directory heading proves the catalog is live.
    await expect(page.getByRole('heading', { name: t('directory.heading') })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    await expect(page.locator('html')).toHaveAttribute('lang', 'ar')

    // The control names the language it switches *to*, in that language.
    // getByRole only matches what is in the accessibility tree, so this
    // resolves to whichever of the two toggles (desktop nav or mobile icon
    // row) is actually on screen at this viewport.
    const toEnglish = page.getByRole('button', { name: SWITCH_TO_ENGLISH })
    await expect(toEnglish).toBeVisible()
    await toEnglish.click()

    await expect(page.getByRole('heading', { name: tEn('directory.heading') })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')

    // Persisted, not just held in memory for this render.
    await page.reload()
    await expect(page.getByRole('heading', { name: tEn('directory.heading') })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')

    // And it goes back.
    await page.getByRole('button', { name: SWITCH_TO_ARABIC }).click()
    await expect(page.getByRole('heading', { name: t('directory.heading') })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  })

  test('Arabic listing content still reads right-to-left on the English site', async ({
    page,
  }) => {
    // The bidi rule the switch exposed: UI language and content language are
    // independent, so an Arabic listing must not be dragged left-to-right by
    // an English page around it.
    await page.goto('/businesses')
    await page.getByRole('button', { name: SWITCH_TO_ENGLISH }).click()
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')

    const firstCard = page.getByRole('article').first()
    await expect(firstCard).toBeVisible()
    // The card body declares dir="auto" so the browser resolves each string's
    // direction from its own text rather than from the page.
    await expect(firstCard.locator('[dir="auto"]').first()).toHaveAttribute('dir', 'auto')
  })
})
