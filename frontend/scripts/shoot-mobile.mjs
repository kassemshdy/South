/**
 * Screenshot the app at phone width so someone can actually look at it.
 *
 * The exposure plan asks for a walk through both journeys at 420px after every
 * slice, and for a long stretch nobody did it — the checks that ran were unit
 * tests, API probes and Playwright assertions, all of which pass happily while
 * a layout is unusable. An agent session cannot open a browser against a
 * deployed host, but it *can* drive a local one and read the resulting PNGs,
 * which is the same evidence.
 *
 * Usage, with the API on :8000, Vite on :5173, and a seeded database:
 *
 *   cd frontend
 *   NO_PROXY='localhost,127.0.0.1' HTTP_PROXY= HTTPS_PROXY= \
 *     node scripts/shoot-mobile.mjs [outDir]
 *
 * The proxy variables matter in a sandbox: without them Node's `fetch` sends
 * requests for localhost to an outbound proxy and they never arrive.
 *
 * Writes `NN-name.png` into `outDir` (default `/tmp/shots`) and prints one line
 * per shot. Nothing is asserted — a person or an agent reads the images. Keep
 * it that way: an assertion here would duplicate the Playwright suite, and the
 * point is to see what the suite cannot describe.
 */

import { chromium } from '@playwright/test'
import { mkdir, readFile } from 'node:fs/promises'

const OUT = process.argv[2] ?? '/tmp/shots'
const BASE = process.env.SHOOT_BASE ?? 'http://localhost:5173'
const API = process.env.SHOOT_API ?? 'http://localhost:8000'
const CHROMIUM =
  process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

await mkdir(OUT, { recursive: true })

/**
 * Button labels come from the catalog the app renders from, never as literals
 * here — the same rule `e2e/orders.spec.ts` follows. It keeps this file out of
 * the way of the no-Arabic-in-source guard (which does not scan `scripts/`,
 * so the convention has to hold by choice rather than by test), and it means
 * rewording a button does not silently break the tool.
 */
const ar = JSON.parse(
  await readFile(new URL('../src/i18n/locales/ar.json', import.meta.url), 'utf-8'),
)

const json = async (path) => {
  const response = await fetch(API + path)
  if (!response.ok) throw new Error(`${path} answered ${response.status}`)
  return response.json()
}

/**
 * The oldest listing, not the newest.
 *
 * `page_size=1` returns whatever the Playwright acceptance spec created most
 * recently, whose logo is a 10x10 black test fixture — which reads as a broken
 * image in a screenshot and sent one review off after a bug that did not
 * exist. The oldest rows are seeded content with real generated images.
 */
const oldest = (items) => {
  if (!items?.length) throw new Error('no public listings — is the database seeded?')
  return items[items.length - 1]
}

const browser = await chromium.launch({ executablePath: CHROMIUM })
try {
  // 420px is the width the plan names, and roughly the narrow end of the
  // Android phones this directory is built for.
  const page = await browser.newPage({ viewport: { width: 420, height: 900 } })

  const business = oldest((await json('/api/businesses?page_size=30')).items)
  const item = oldest((await json('/api/items?page_size=30')).items)
  const talent = oldest((await json('/api/talent?page_size=30')).items)
  console.log(`business=${business.slug} item=${item.slug} talent=${talent.slug}`)

  const url = {
    business: `/business/${encodeURIComponent(business.slug)}`,
    item: `/product/${encodeURIComponent(item.slug)}`,
    talent: `/talent/${encodeURIComponent(talent.slug)}`,
  }

  let n = 0
  const shot = async (name, path) => {
    await page.goto(BASE + path, { waitUntil: 'networkidle' })
    // Images and the first paint of a lazily-loaded route both land after
    // networkidle often enough to be worth waiting for.
    await page.waitForTimeout(600)
    const file = `${OUT}/${String(++n).padStart(2, '0')}-${name}.png`
    await page.screenshot({ path: file })
    console.log(`shot ${file}`)
  }

  await shot('home', '/')
  await shot('directory', '/businesses')
  await shot('products', '/products')
  await shot('business', url.business)
  await shot('talent', url.talent)
  await shot('product', url.item)

  // Saving from each of the three kinds of listing, then the list itself: the
  // one page whose whole content comes from browser storage.
  for (const path of [url.item, url.business, url.talent]) {
    await page.goto(BASE + path, { waitUntil: 'networkidle' })
    const save = page.getByRole('button', { name: ar['favourites.save'], exact: true })
    if (await save.count()) await save.first().click()
    await page.waitForTimeout(250)
  }
  await shot('favourites', '/favourites')
  await shot('product-saved', url.item)
  await shot('cart', '/cart')

  console.log(`\n${n} shots in ${OUT} — open them.`)
} finally {
  await browser.close()
}
