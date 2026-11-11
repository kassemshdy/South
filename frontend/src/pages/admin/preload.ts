/**
 * Fetches admin screens' code ahead of when React would ask for it.
 *
 * The admin area is split out of the main bundle so the public never pays
 * for it, but that split made opening an admin URL a chain of round trips:
 * the session check, then the layout's code, then the page's code, then its
 * data. From Lebanon each hop is a few hundred milliseconds.
 *
 * Two steps, in this order on purpose:
 * - `preloadAdminFor(path)`: on opening an admin URL, the layout and that
 *   one page start downloading alongside the session check.
 * - `preloadAdmin()`: once an administrator is signed in and the page has
 *   finished loading, every other screen, so moving between them does not
 *   wait. Fetching all of them up front was measured slower (3.9 s against
 *   1.9 s with 250 ms latency): forty downloads queued ahead of the ones the
 *   open page needed.
 *
 * The glob produces the same dynamic imports the routes use, so these are the
 * same chunks, fetched once and reused.
 */
const screens = import.meta.glob('./Admin*.tsx')

/** Path to screen, mirroring the admin routes in App.tsx. A path missing
 * here is only not fetched early; it still loads when opened. */
const ROUTES: [RegExp, string][] = [
  [/^\/admin\/?$/, 'AdminDashboardPage'],
  [/^\/admin\/businesses\/?$/, 'AdminBusinessesPage'],
  [/^\/admin\/businesses\/[^/]+\/?$/, 'AdminReviewPage'],
  [/^\/admin\/talent\/?$/, 'AdminTalentsPage'],
  [/^\/admin\/talent\/[^/]+\/?$/, 'AdminTalentReviewPage'],
  [/^\/admin\/categories\/?$/, 'AdminCategoriesPage'],
  [/^\/admin\/products\/?$/, 'AdminProductsPage'],
  [/^\/admin\/talent-skills\/?$/, 'AdminTalentSkillsPage'],
  [/^\/admin\/locations\/?$/, 'AdminLocationsPage'],
  [/^\/admin\/users\/?$/, 'AdminUsersPage'],
  [/^\/admin\/applications\/?$/, 'AdminApplicationsPage'],
  [/^\/admin\/orders\/?$/, 'AdminOrdersPage'],
  [/^\/admin\/growth\/?$/, 'AdminGrowthPage'],
  [/^\/admin\/export\/?$/, 'AdminExportPage'],
  [/^\/admin\/setup-map\/?$/, 'AdminSetupMapPage'],
  [/^\/admin\/staff\/?$/, 'AdminStaffPage'],
  [/^\/admin\/home-layout\/?$/, 'AdminHomeLayoutPage'],
  [/^\/admin\/menu\/?$/, 'AdminMenuPage'],
  [/^\/admin\/reels\/?$/, 'AdminReelsPage'],
  [/^\/admin\/stories\/?$/, 'AdminStoriesPage'],
  [/^\/admin\/page-covers\/?$/, 'AdminPageCoversPage'],
  [/^\/admin\/pages\/?$/, 'AdminPagesPage'],
  [/^\/admin\/site-settings\/?$/, 'AdminSiteSettingsPage'],
  [/^\/admin\/partners\/?$/, 'AdminPartnersPage'],
  [/^\/admin\/shopify\/?$/, 'AdminShopifyPage'],
  [/^\/admin\/api-partners\/?$/, 'AdminApiPartnersPage'],
  [/^\/admin\/users\/[^/]+\/?$/, 'AdminUserDetailPage'],
  [/^\/admin\/feedback\/?$/, 'AdminFeedbackPage'],
  [/^\/admin\/testimonials\/?$/, 'AdminTestimonialsPage'],
  [/^\/admin\/articles\/?$/, 'AdminArticlesPage'],
  [/^\/admin\/shops-without-products\/?$/, 'AdminShopsWithoutProductsPage'],
  [/^\/admin\/contacted-shops\/?$/, 'AdminContactedShopsPage'],
  [/^\/admin\/map-locations\/?$/, 'AdminMapLocationsPage'],
  [/^\/admin\/workshops\/?$/, 'AdminWorkshopsPage'],
  [/^\/admin\/activities\/?$/, 'AdminActivitiesPage'],
  [/^\/admin\/carousel\/?$/, 'AdminCarouselPage'],
  [/^\/admin\/job-openings\/?$/, 'AdminJobOpeningsPage'],
  [/^\/admin\/employer-requests\/?$/, 'AdminEmployerRequestsPage'],
  [/^\/admin\/service-requests\/?$/, 'AdminServiceRequestsPage'],
]

function load(name: string): void {
  // A failed prefetch is not an error: the route will ask again on demand.
  void screens[`./${name}.tsx`]?.().catch(() => undefined)
}

export function preloadAdminFor(pathname: string): void {
  load('AdminLayout')
  const match = ROUTES.find(([pattern]) => pattern.test(pathname))
  if (match) load(match[1])
}

let started = false

export function preloadAdmin(): void {
  if (started) return
  started = true
  const all = () => {
    for (const fetchScreen of Object.values(screens)) void fetchScreen().catch(() => undefined)
  }
  // After the open page has what it needs: the load event, then a pause.
  const later = () => window.setTimeout(all, 1500)
  if (document.readyState === 'complete') later()
  else window.addEventListener('load', later, { once: true })
}
