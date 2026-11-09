/**
 * Putting an ID card on the signed-in account, which review needs before a
 * listing can be submitted (the owners' decision, 9 Nov 2026). Through the
 * API with the page's own session: the account page's upload has its own
 * spec (account-and-verification.spec.ts), and every other spec only needs
 * the card to be there.
 */

import { expect, type Page } from '@playwright/test'

const PDF = Buffer.from('%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n')

export async function uploadIdCard(page: Page): Promise<void> {
  const token = await page.evaluate(() => window.localStorage.getItem('south.auth.token'))
  expect(token, 'signed in before uploading an ID card').toBeTruthy()
  const response = await page.request.post('/api/me/verification-document', {
    headers: { Authorization: `Bearer ${token}` },
    multipart: { file: { name: 'id.pdf', mimeType: 'application/pdf', buffer: PDF } },
  })
  expect(response.status(), await response.text()).toBeLessThan(300)
}
