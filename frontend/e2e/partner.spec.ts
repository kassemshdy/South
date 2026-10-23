import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { ADMIN_EMAIL, ADMIN_PASSWORD } from './support/admin'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const fixture = load<{
  name: string
  phone: string
  occupation: string
  residence: string
  offer: string
}>('./fixtures/partner-data.json')

const t = (key: string): string => ar[key]!

/**
 * The partner form (round 3): from the card on the homepage, through the
 * form, to the admin page of its own -- and nowhere public on the way.
 */
test.describe('Partner form', () => {
  test('a visitor offers support, and it reaches the admin page', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: t('partner.title') }).click()
    await expect(page).toHaveURL(/\/partner$/)
    await expect(page.getByRole('heading', { name: t('partner.title'), level: 1 })).toBeVisible()

    await page.getByLabel(t('partner.nameLabel')).fill(fixture.name)
    await page.getByLabel(t('partner.phoneLabel')).fill(fixture.phone)
    await page.getByLabel(t('partner.occupationLabel')).fill(fixture.occupation)
    await page.getByLabel(t('partner.residenceLabel')).fill(fixture.residence)
    await page.getByLabel(t('partner.offerLabel')).fill(fixture.offer)
    await page.getByRole('button', { name: t('partner.submit') }).click()
    await expect(page.getByRole('heading', { name: t('partner.sentTitle') })).toBeVisible()

    await page.goto('/admin/login')
    await page.getByLabel(t('adminLogin.email')).fill(ADMIN_EMAIL)
    await page.getByLabel(t('adminLogin.password')).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: t('adminLogin.submit') }).click()
    await expect(page.getByRole('heading', { name: t('admin.dashboardHeading') })).toBeVisible()

    await page.goto('/admin/partners')
    const entry = page.getByRole('listitem').filter({ hasText: fixture.offer })
    await expect(entry).toHaveCount(1)
    await expect(entry.getByText(fixture.name)).toBeVisible()
  })
})
