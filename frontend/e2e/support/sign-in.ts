/**
 * Signing an owner in, in one place.
 *
 * It used to be eight places: every spec that needed an owner carried its own
 * copy of "go to /login, type the number, press send, type the code". When the
 * login page grew a password step in front of the code step, all eight broke
 * at once — which is the same lesson `src/features/onboarding/destinations.ts`
 * records about three hand-written copies of one list.
 *
 * The code path is what these specs use because the development OTP provider
 * hands out a fixed code, so a test can complete it without a gateway. It is
 * no longer the first thing the login page shows — a password is, since that
 * is the route that works in production — so getting to it starts with the
 * link that switches steps.
 */

import { expect, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const ar = JSON.parse(
  readFileSync(resolve(here, '../../src/i18n/locales/ar.json'), 'utf-8'),
) as Record<string, string>
const t = (key: string): string => ar[key]!

/** The fixed code the development OTP provider always issues. */
export const DEV_OTP = '123456'

export async function signInWithCode(page: Page, phone: string): Promise<void> {
  await page.goto('/login')
  await page.getByRole('button', { name: t('login.useCodeInstead') }).click()
  await page.getByLabel(t('login.phoneLabel')).fill(phone)
  await page.getByRole('button', { name: t('login.sendCode') }).click()
  await expect(page.getByRole('heading', { name: t('login.codeTitle') })).toBeVisible()
  await page.getByLabel(t('login.codeLabel')).fill(DEV_OTP)
  await page.getByRole('button', { name: t('login.confirm') }).click()
  await expect(page).toHaveURL(/\/dashboard/)
}
