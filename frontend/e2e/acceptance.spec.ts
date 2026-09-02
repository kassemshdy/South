import { expect, test, type Page } from '@playwright/test'

/**
 * The MVP acceptance scenario, end to end in a real browser.
 *
 * A visitor browses without an account, an owner signs in by phone and builds a
 * listing, the listing stays invisible until an administrator approves it, and
 * it becomes searchable immediately afterwards.
 */

const OWNER_PHONE = '03987654'
const DEV_OTP = '123456'
const ADMIN_EMAIL = 'admin@example.com'
const ADMIN_PASSWORD = 'ChangeMe!123'
const BUSINESS_NAME = 'مناقيش الضيعة'

// A tiny valid JPEG generated at runtime, so no binary fixtures live in the repo.
function jpeg(): { name: string; mimeType: string; buffer: Buffer } {
  const base64 =
    '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a' +
    'HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAAKAAoBAREA/8QAHwAAAQUBAQEB' +
    'AQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1Fh' +
    'ByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZ' +
    'WmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXG' +
    'x8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oACAEBAAA/APn+iiiv/9k='
  return { name: 'photo.jpg', mimeType: 'image/jpeg', buffer: Buffer.from(base64, 'base64') }
}

async function signInAsOwner(page: Page) {
  await page.goto('/login')
  await page.getByLabel('رقم الهاتف').fill(OWNER_PHONE)
  await page.getByRole('button', { name: 'إرسال رمز التحقق' }).click()
  await expect(page.getByRole('heading', { name: 'أدخل رمز التحقق' })).toBeVisible()
  await page.getByLabel('رمز التحقق').fill(DEV_OTP)
  await page.getByRole('button', { name: 'تأكيد وتسجيل الدخول' }).click()
  await expect(page).toHaveURL(/\/dashboard/)
}

test.describe('MVP acceptance flow', () => {
  test('visitor browses, owner submits, admin approves, listing becomes searchable', async ({ page }) => {
    // --- 1. A visitor browses approved businesses without logging in --------
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'اكتشف الأعمال والخدمات في جنوب لبنان' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'أحدث النشاطات' })).toBeVisible()

    await page.goto('/businesses')
    await expect(page.getByRole('heading', { name: 'دليل الأعمال' })).toBeVisible()
    await expect(page.getByRole('article').first()).toBeVisible()
    await page.screenshot({ path: 'e2e/screenshots/01-directory.png', fullPage: false })

    // --- 2. The owner signs in with a Lebanese number + OTP -----------------
    await signInAsOwner(page)
    await expect(page.getByRole('heading', { name: 'نشاطاتي' })).toBeVisible()

    // --- 3. Create the business --------------------------------------------
    await page.goto('/dashboard/businesses/new')
    await page.getByLabel('اسم النشاط').fill(BUSINESS_NAME)
    await page.getByLabel('وصف مختصر').fill('مناقيش وفطائر على الصاج كل صباح')
    await page.getByLabel('نبذة عن النشاط').fill('فرن عائلي في صور، زعتر بلدي وجبنة طازجة يومياً.')

    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: 'مطاعم ومأكولات' }).click()

    await page.getByLabel('رقم واتساب').fill('03987654')
    await page.getByRole('button', { name: 'حفظ ومتابعة' }).click()

    // --- 4. Location: صور ---------------------------------------------------
    await expect(page.getByLabel('المنطقة')).toBeVisible()
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: 'صور', exact: true }).click()
    await page.getByLabel('تفاصيل العنوان').fill('شارع البلدية، مقابل الحديقة العامة')
    await page.getByRole('button', { name: 'حفظ ومتابعة' }).click()

    // --- 5. Images: a logo and three gallery photos -------------------------
    await expect(page.getByRole('heading', { name: 'شعار النشاط' })).toBeVisible()
    const fileInputs = page.locator('input[type="file"]')
    await fileInputs.nth(0).setInputFiles(jpeg())
    await expect(page.getByText('تم رفع الصورة', { exact: true }).first()).toBeVisible()

    for (let index = 0; index < 3; index += 1) {
      await page.locator('input[type="file"]').last().setInputFiles(jpeg())
      await expect(page.getByText(`${index + 1} من 10`, { exact: true })).toBeVisible()
    }
    await page.screenshot({ path: 'e2e/screenshots/02-images.png', fullPage: false })
    await page.getByRole('button', { name: 'متابعة', exact: true }).click()

    // --- 6. Social links: Instagram ----------------------------------------
    await page.getByLabel('إنستغرام').fill('instagram.com/manakish.aldayaa')
    await page.getByRole('button', { name: 'حفظ ومتابعة' }).click()

    // --- 7. Items: زعتر، جبنة، لبنة وخضار -----------------------------------
    const items: [string, string][] = [
      ['زعتر', '1.50'],
      ['جبنة', '3.00'],
      ['لبنة وخضار', '2.50'],
    ]
    for (const [title, price] of items) {
      await page.getByRole('button', { name: 'إضافة عنصر' }).first().click()
      await page.getByLabel('الاسم').fill(title)
      await page.getByLabel('السعر').fill(price)
      await page.getByRole('button', { name: 'إضافة العنصر' }).click()
      await expect(page.getByRole('heading', { name: title, level: 4 })).toBeVisible()
    }
    await page.screenshot({ path: 'e2e/screenshots/03-items.png', fullPage: false })

    // --- 8. Submit for review ----------------------------------------------
    await page.getByRole('button', { name: 'متابعة للمراجعة' }).click()
    await expect(page.getByText('جميع البيانات المطلوبة مكتملة.').first()).toBeVisible()
    await page.getByRole('button', { name: 'إرسال للمراجعة' }).click()

    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByText('قيد المراجعة', { exact: true }).first()).toBeVisible()
    await page.screenshot({ path: 'e2e/screenshots/04-pending.png', fullPage: false })

    // --- 9. The pending listing must NOT be publicly visible ----------------
    // Other approved listings may legitimately match this query, so assert on
    // the absence of *this* business rather than an empty result set.
    await page.goto(`/businesses?q=${encodeURIComponent('مناقيش')}`)
    await expect(page.getByRole('article').filter({ hasText: BUSINESS_NAME })).toHaveCount(0)

    // Its public profile must not be reachable directly either.
    await page.goto(`/business/${encodeURIComponent('مناقيش-الضيعة')}`)
    await expect(page.getByText('هذا النشاط غير متوفر أو لم تتم الموافقة عليه بعد.')).toBeVisible()

    // --- 10. Administrator approves ----------------------------------------
    await page.goto('/admin/login')
    await page.getByLabel('البريد الإلكتروني').fill(ADMIN_EMAIL)
    await page.getByLabel('كلمة المرور').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'تسجيل الدخول' }).click()

    await expect(page.getByRole('heading', { name: 'لوحة التحكم' })).toBeVisible()
    await page.getByRole('link', { name: 'مراجعة الطلبات' }).click()

    // The queue is oldest-first, so target this listing's row rather than the
    // first one in the list.
    await page
      .getByRole('listitem')
      .filter({ hasText: BUSINESS_NAME })
      .getByRole('link', { name: 'مراجعة' })
      .click()
    await expect(page.getByRole('heading', { name: BUSINESS_NAME })).toBeVisible()
    // The reviewer sees the owner's account phone and the submitted items.
    await expect(page.getByText('+9613987654').first()).toBeVisible()
    await expect(page.getByText('زعتر', { exact: true }).first()).toBeVisible()
    await page.screenshot({ path: 'e2e/screenshots/05-admin-review.png', fullPage: true })

    await page.getByRole('button', { name: 'موافقة' }).click()
    await expect(page.getByRole('heading', { name: 'تأكيد الموافقة' })).toBeVisible()
    await page.getByRole('button', { name: 'تأكيد', exact: true }).click()
    await expect(page.getByText('مقبول', { exact: true }).first()).toBeVisible()

    // --- 11. Immediately searchable on the public site ----------------------
    await page.goto(`/businesses?q=${encodeURIComponent('مناقيش')}`)
    const card = page.getByRole('article').filter({ hasText: BUSINESS_NAME })
    await expect(card).toHaveCount(1)
    await page.screenshot({ path: 'e2e/screenshots/06-search-result.png', fullPage: false })

    // --- 12. The public profile shows everything the owner published --------
    await card.getByRole('link', { name: 'عرض التفاصيل' }).click()
    await expect(page.getByRole('heading', { name: BUSINESS_NAME, level: 1 })).toBeVisible()
    await expect(page.getByText('نشاط موثّق').first()).toBeVisible()
    await expect(page.getByRole('heading', { name: 'المنتجات والخدمات' })).toBeVisible()
    await expect(page.getByText('$1.50')).toBeVisible()
    await expect(page.getByText('$3.00')).toBeVisible()
    await expect(page.getByText('$2.50')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'معرض الصور' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'تواصل عبر واتساب' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'إنستغرام' })).toBeVisible()
    await page.screenshot({ path: 'e2e/screenshots/07-public-profile.png', fullPage: true })
  })
})
