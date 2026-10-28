/**
 * The crop window every photo upload now opens (`ImageCropDialog`), in one
 * place: a spec that picks a photo confirms the crop as an owner would,
 * and waits for the window to close before the upload is judged.
 */

import { expect, type Page } from '@playwright/test'

import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const ar = JSON.parse(
  readFileSync(resolve(here, '../../src/i18n/locales/ar.json'), 'utf-8'),
) as Record<string, string>

/** Accept the crop window's framing of the photo just picked. */
export async function cropAndUse(page: Page): Promise<void> {
  const dialog = page.getByRole('dialog', { name: ar['crop.title']! })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: ar['crop.apply']!, exact: true }).click()
  await expect(dialog).toHaveCount(0)
}
