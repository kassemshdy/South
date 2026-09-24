/**
 * The administrator the specs sign in as.
 *
 * The password is not written here. The repository is public, so any fixed
 * value would be everybody's admin password on any deployment that kept it;
 * CI generates one per run and passes it to both the seed and these specs.
 * Locally, export E2E_ADMIN_PASSWORD with the ADMIN_PASSWORD your API was
 * seeded with.
 */
export const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com'

export const ADMIN_PASSWORD: string = (() => {
  const value = process.env.E2E_ADMIN_PASSWORD
  if (!value) {
    throw new Error('Set E2E_ADMIN_PASSWORD to the ADMIN_PASSWORD the API was seeded with')
  }
  return value
})()
