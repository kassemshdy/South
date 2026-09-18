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
 * The personal step is a summary of the account rather than a form, and it
 * blocks nothing: identity is checked by a person at review time, not by the
 * wizard. So stepping past it is exactly what an owner who has already filled
 * their account in — or who means to come back to it — does, and that is what
 * this helper is.
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

/** Open the wizard and step past the personal summary onto the basics form. */
export async function openBusinessWizard(page: Page): Promise<void> {
  await page.goto('/dashboard/businesses/new')
  await expect(page.getByRole('heading', { name: t('wizard.personalHeading') })).toBeVisible()
  await page.getByRole('button', { name: t('common.continue'), exact: true }).click()
  await expect(page.getByLabel(t('form.name'))).toBeVisible()
}
