import { expect, test, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const talents = load<{ display_name: string; status: string; owner_phone: string }[]>(
  '../../backend/scripts/data/talents.json',
)
const fixture = load<{ customer: string; phone: string; details: string }>(
  './fixtures/service-request-data.json',
)

const t = (key: string): string => ar[key]!

// The seeded person this spec asks for work. Taken from the seed file the app
// is loaded with rather than named here, so the two cannot drift apart, and
// their login phone is what lets the second half sign in as them.
const provider = talents.find((entry) => entry.status === 'APPROVED')!
const DEV_OTP = '123456'

async function signInAsProvider(page: Page) {
  await page.goto('/login')
  await page.getByLabel(t('login.phoneLabel')).fill(provider.owner_phone)
  await page.getByRole('button', { name: t('login.sendCode') }).click()
  await expect(page.getByRole('heading', { name: t('login.codeTitle') })).toBeVisible()
  await page.getByLabel(t('login.codeLabel')).fill(DEV_OTP)
  await page.getByRole('button', { name: t('login.confirm') }).click()
  await expect(page).toHaveURL(/\/dashboard/)
}

/**
 * Asking a craftsperson for work, and that request arriving.
 *
 * This is the half of the directory that had no way to be asked. A product
 * could be collected and sent as an order that reaches the owner's
 * dashboard; a talent profile offered a WhatsApp link and nothing else, so a
 * request that was never sent — or sent and lost in a busy inbox — left no
 * trace either person could come back to.
 *
 * What is worth asserting in a browser rather than against the API:
 *
 * 1. **No account, on the asking side.** The whole flow runs signed out, the
 *    same as an order.
 * 2. **The form sits beside the WhatsApp button, not instead of it.** They
 *    are not alternatives: the message gets a faster answer, the stored
 *    request is what survives the answer not coming.
 * 3. **It actually arrives.** The request shows up in the provider's own
 *    dashboard, which is the entire point of storing it, and it can be moved
 *    along so the list stays a queue rather than a pile.
 * 4. **It is between those two people.** Nothing about the requester appears
 *    on the public page.
 */
test.describe('Service requests', () => {
  test('a visitor asks for work without an account, and it reaches the provider', async ({
    page,
    request,
  }) => {
    // Resolve the slug through the public directory rather than guessing how
    // the seed slugified an Arabic name.
    const found = await request.get(
      `/api/talent?page_size=1&q=${encodeURIComponent(provider.display_name)}`,
    )
    expect(found.ok()).toBeTruthy()
    const { items } = (await found.json()) as { items: { slug: string }[] }
    expect(items.length).toBe(1)
    const { slug } = items[0]!

    await page.goto(`/talent/${encodeURIComponent(slug)}`)
    await expect(
      page.getByRole('heading', { name: provider.display_name, level: 1 }),
    ).toBeVisible()

    // Both ways of getting in touch are on the page at once.
    await expect(page.getByRole('link', { name: t('business.whatsappCta') })).toBeVisible()
    await expect(
      page.getByRole('heading', { name: t('serviceRequests.askHeading') }),
    ).toBeVisible()

    await page.getByLabel(t('serviceRequests.nameLabel')).fill(fixture.customer)
    await page.getByLabel(t('serviceRequests.phoneLabel')).fill(fixture.phone)
    await page.getByLabel(t('serviceRequests.detailsLabel')).fill(fixture.details)
    await page.getByRole('button', { name: t('serviceRequests.submit') }).click()

    // Says what happened and stays said, because nothing else will say it.
    await expect(page.getByText(t('serviceRequests.sentHint'))).toBeVisible()

    // --- Not published: a request is between two people -----------------------
    await page.reload()
    await expect(page.getByText(fixture.customer, { exact: true })).toHaveCount(0)
    await expect(page.getByText(fixture.details, { exact: true })).toHaveCount(0)

    // --- It arrives in the provider's own dashboard ---------------------------
    await signInAsProvider(page)
    await page.goto('/dashboard/talent')
    await page.getByRole('tab', { name: t('serviceRequests.ownerTab') }).click()

    const row = page.getByRole('listitem').filter({ hasText: fixture.customer })
    await expect(row).toHaveCount(1)
    await expect(row.getByText(fixture.details)).toBeVisible()
    await expect(row.getByText(t('serviceRequests.statusNEW'), { exact: true })).toBeVisible()

    // Says out loud that nothing pinged them, because nothing did.
    await expect(page.getByText(t('serviceRequests.ownerIntro'))).toBeVisible()

    // --- And it can be worked through rather than piling up -------------------
    await row.getByRole('button', { name: t('serviceRequests.markContacted') }).click()
    await expect(
      row.getByText(t('serviceRequests.statusCONTACTED'), { exact: true }),
    ).toBeVisible()
  })
})
