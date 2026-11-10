/**
 * Opening the business wizard, in one place.
 *
 * Five specs used to `goto('/dashboard/businesses/new')` and type straight
 * into the name field. When a personal-details step was put in front of the
 * basics form, all five broke at once — the same shape of failure as the
 * sign-in block in `sign-in.ts`, and the same lesson
 * `src/features/onboarding/destinations.ts` records about hand-written copies
 * of one list drifting apart.
 *
 * The personal step holds the account's own forms, and its Continue waits
 * for a full name and the front of the ID card (the owners' request, 10 Nov
 * 2026). The account page's forms have their own spec
 * (account-and-verification.spec.ts), so this helper puts both on the
 * account through the API with the page's session, then steps past.
 */

import { expect, type Page } from '@playwright/test'

import { uploadIdCard } from './identity'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const ar = JSON.parse(
  readFileSync(resolve(here, '../../src/i18n/locales/ar.json'), 'utf-8'),
) as Record<string, string>
const t = (key: string): string => ar[key]!

/** Open the wizard and step past the personal summary onto the basics form. */
export async function openBusinessWizard(page: Page): Promise<void> {
  // A full name and the ID card's front: what step 1 waits for.
  const token = await page.evaluate(() => window.localStorage.getItem('south.auth.token'))
  const named = await page.request.patch('/api/me', {
    headers: { Authorization: `Bearer ${token}` },
    data: { full_name: 'E2E Owner' },
  })
  expect(named.status(), await named.text()).toBeLessThan(300)
  await uploadIdCard(page)
  await page.goto('/dashboard/businesses/new')
  await expect(page.getByRole('heading', { name: t('wizard.personalHeading') })).toBeVisible()
  await page.getByRole('button', { name: t('common.continue'), exact: true }).click()
  await expect(page.getByLabel(t('form.name'))).toBeVisible()
}
