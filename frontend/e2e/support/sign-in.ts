/**
 * Signing an owner in, in one place.
 *
 * It used to be eight places: every spec that needed an owner carried its own
 * copy of the navigation. When the login page changed, all eight broke at
 * once — which is the same lesson `src/features/onboarding/destinations.ts`
 * records about three hand-written copies of one list. It has since changed
 * twice more, and this file absorbed both.
 *
 * The password is the only way in now. The seeded owner accounts carry the
 * one `SEED_OWNER_PASSWORD` puts on them, which the seed script refuses to
 * apply in production — so this is a demo-and-test credential by construction,
 * not a backdoor that happens to be unused.
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

/** Must match SEED_OWNER_PASSWORD in the backend environment. */
export const SEEDED_OWNER_PASSWORD = process.env.E2E_OWNER_PASSWORD ?? 'DemoOwner!123'

const demoOwners = JSON.parse(
  readFileSync(resolve(here, '../../../backend/scripts/data/demo_owners.json'), 'utf-8'),
) as { key: string; phone: string }[]

/**
 * The phone number of a seeded owner account with nothing listed under it.
 *
 * Read from the seed file the app is loaded with rather than written out
 * here, so the number and the account it has to match cannot drift apart —
 * the same reason `service-requests.spec.ts` takes its talent from
 * `talents.json`. Signing in no longer creates the account it cannot find,
 * so a number nobody seeded is simply a failed sign-in.
 */
export function demoOwnerPhone(key: string): string {
  const owner = demoOwners.find((entry) => entry.key === key)
  if (!owner) {
    throw new Error(
      `No demo owner "${key}" in backend/scripts/data/demo_owners.json — ` +
        `add one there, and re-seed so the account exists.`,
    )
  }
  return owner.phone
}

export async function signIn(
  page: Page,
  identifier: string,
  password: string = SEEDED_OWNER_PASSWORD,
): Promise<void> {
  await page.goto('/login')
  await page.getByLabel(t('login.identifierLabel')).fill(identifier)
  await page.getByLabel(t('login.passwordLabel')).fill(password)
  await page.getByRole('button', { name: t('login.signIn'), exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard/)
}
