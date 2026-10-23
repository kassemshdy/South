/**
 * Dropping a seller's pin on the map, in one place.
 *
 * The map's container is on screen a moment before Leaflet listens for taps,
 * so a click straight away can be lost -- one CI run failed exactly that way,
 * with the profile never becoming ready for review. This waits for the map to
 * say it is listening, and then for the pin to actually appear.
 */

import { expect, type Page } from '@playwright/test'

export async function dropPin(page: Page, label: string): Promise<void> {
  const map = page.locator(`[role="region"][aria-label="${label}"][data-ready="true"]`)
  await expect(map).toBeVisible()
  await map.click()
  await expect(map.locator('.leaflet-marker-icon')).toBeVisible()
}
