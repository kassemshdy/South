import { expect, test } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const apiAr = load<Record<string, string>>('../../backend/app/locales/ar.json')
const talents = load<{ display_name: string; status: string }[]>(
  '../../backend/scripts/data/talents.json',
)
const fixture = load<{ customer: string; phone: string; details: string }>(
  './fixtures/service-request-data.json',
)

const t = (key: string): string => ar[key]!
const provider = talents.find((entry) => entry.status === 'APPROVED')!

/**
 * A rejected form says which field it means.
 *
 * The API has always answered a 422 with one sentence per bad field, in the
 * reader's locale, under `error.details.fields`. The client parsed it and
 * then nothing read it: every form showed only the envelope — "check the
 * fields below" — which named no field, so "below" was a guess.
 *
 * Asserted end to end rather than as a unit test because the whole point is
 * the join: the API's sentence, in Arabic, on the input it is about. Both
 * halves of that are read from the catalogs the two sides actually ship, so
 * this cannot pass against a hardcoded English string.
 */
test.describe('Server validation messages', () => {
  test('a rejected field shows the API sentence on the field itself', async ({
    page,
    request,
  }) => {
    // Resolve the slug through the directory rather than guessing how the
    // seed slugified an Arabic name — same as `service-requests.spec.ts`.
    const found = await request.get(
      `/api/talent?page_size=1&q=${encodeURIComponent(provider.display_name)}`,
    )
    expect(found.ok()).toBeTruthy()
    const { items } = (await found.json()) as { items: { slug: string }[] }
    await page.goto(`/talent/${encodeURIComponent(items[0]!.slug)}`)

    const details = page.getByLabel(t('serviceRequests.detailsLabel'))
    await expect(details).toBeVisible()

    // `novalidate` is not set on this form, so the browser would block the
    // submit before the server ever saw it. Filling valid-to-the-browser but
    // invalid-to-the-API values is what actually exercises the 422: the
    // details field requires ten characters server-side.
    await page.getByLabel(t('serviceRequests.nameLabel')).fill(fixture.customer)
    await page.getByLabel(t('serviceRequests.phoneLabel')).fill(fixture.phone)
    await details.fill('short')
    await details.evaluate((el) => el.removeAttribute('minlength'))

    await page.getByRole('button', { name: t('serviceRequests.submit') }).click()

    // The API's own sentence for "too short", interpolated with the bound the
    // schema declares — read from the backend catalog, so a reworded message
    // updates this assertion rather than breaking it.
    const expected = apiAr['validation.string_too_short']!.replace('{min_length}', '10')
    const message = page.getByRole('alert').filter({ hasText: expected })
    await expect(message).toBeVisible()

    // And it is attached to the field, not floating: `Field` wires the error
    // through aria-describedby, which is what a screen reader follows.
    const describedBy = await details.getAttribute('aria-describedby')
    expect(describedBy).toBeTruthy()
    // Attribute selector rather than `#id`: React's `useId` emits `:r5:`,
    // which is not a valid bare CSS id selector.
    await expect(page.locator(`[id="${describedBy}"]`)).toHaveText(expected)
    await expect(details).toHaveAttribute('aria-invalid', 'true')
  })
})
