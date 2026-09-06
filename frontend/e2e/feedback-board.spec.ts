import { expect, test, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const load = <T>(relative: string): T =>
  JSON.parse(readFileSync(resolve(here, relative), 'utf-8')) as T

const ar = load<Record<string, string>>('../src/i18n/locales/ar.json')
const fixture = load<{ title: string; description: string; comment: string }>(
  './fixtures/feedback-board-data.json',
)

const t = (key: string): string => ar[key]!

const ADMIN_EMAIL = 'admin@example.com'
const ADMIN_PASSWORD = 'ChangeMe!123'

async function signInAsAdmin(page: Page) {
  await page.goto('/admin/login')
  await page.getByLabel(t('adminLogin.email')).fill(ADMIN_EMAIL)
  await page.getByLabel(t('adminLogin.password')).fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: t('adminLogin.submit') }).click()
  await expect(page.getByRole('heading', { name: t('admin.dashboardHeading') })).toBeVisible()
}

/**
 * The admin-only feedback tool end to end: report a bug from the floating
 * button on an ordinary page, find it on the Kanban board, comment on it,
 * then delete it. Column-to-column drag itself is not simulated here — a
 * mouse-drag sequence against dnd-kit on the suite's narrow mobile viewport
 * (where the board's columns stack vertically) is exactly the kind of thing
 * that is fragile in a headless run for no real coverage gain: the move
 * endpoint's reordering and column bookkeeping is asserted directly by the
 * backend suite (test_feedback.py).
 */
test.describe('Feedback board', () => {
  test('admin reports a bug, finds it on the board, comments, then deletes it', async ({
    page,
  }) => {
    await signInAsAdmin(page)

    // --- Report from an ordinary page, not the admin panel ---------------------
    await page.goto('/')
    const reportButton = page.getByRole('button', { name: t('feedback.reportBug') })
    await expect(reportButton).toBeVisible()
    await reportButton.click()

    await expect(page.getByRole('heading', { name: t('feedback.reportBug') })).toBeVisible()
    await page.getByLabel(t('feedback.titleLabel')).fill(fixture.title)
    await page.getByLabel(t('feedback.descriptionLabel')).fill(fixture.description)
    await page.getByRole('button', { name: t('feedback.submitReport') }).click()
    await expect(page.getByText(t('feedback.reportSent'), { exact: true })).toBeVisible()

    // --- The ticket lands on the board, in Backlog ------------------------------
    await page.goto('/admin/feedback')
    const backlogColumn = page
      .locator('div')
      .filter({ has: page.getByRole('heading', { name: t('feedback.status.BACKLOG') }) })
      .first()
    await expect(backlogColumn.getByText(fixture.title, { exact: true })).toBeVisible()

    // --- Opening it shows the details, and a comment can be added --------------
    await backlogColumn.getByText(fixture.title, { exact: true }).click()
    await expect(page.getByRole('heading', { name: fixture.title })).toBeVisible()
    await expect(page.getByText(fixture.description)).toBeVisible()

    await page.getByLabel(t('feedback.addCommentLabel')).fill(fixture.comment)
    await page.getByRole('button', { name: t('feedback.addCommentAction') }).click()
    await expect(page.getByText(fixture.comment)).toBeVisible()

    // --- Deleting it removes it from the board ----------------------------------
    page.once('dialog', (dialog) => void dialog.accept())
    await page.getByRole('button', { name: t('feedback.deleteTicket') }).click()
    await expect(page.getByText(t('feedback.ticketDeleted'), { exact: true })).toBeVisible()
    await expect(page.getByText(fixture.title, { exact: true })).toHaveCount(0)
  })
})
