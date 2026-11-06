/**
 * Work.Janoubona (`work.tagline`, the owner's request of 5 Nov 2026):
 * an Upwork-style site for services and talents, served from the same build
 * and the same API as janoubona.net, on its own address. Accounts and talent
 * profiles are shared; the sites differ by the address they are opened on.
 */

const OVERRIDE_KEY = 'south.site'

/** True on work.janoubona.net (and work.* anywhere, e.g. work.localhost). */
export function isWorkSite(): boolean {
  if (typeof window === 'undefined') return false
  if (window.location.hostname.startsWith('work.')) return true
  // Local development and the develop preview have one address, so the Work
  // site can be opened there with `?site=work` (and left with `?site=main`).
  // Remembered for the tab only.
  try {
    const asked = new URLSearchParams(window.location.search).get('site')
    if (asked === 'work') window.sessionStorage.setItem(OVERRIDE_KEY, 'work')
    if (asked === 'main') window.sessionStorage.removeItem(OVERRIDE_KEY)
    return window.sessionStorage.getItem(OVERRIDE_KEY) === 'work'
  } catch {
    return false
  }
}

/**
 * The main site's address, for links that leave Work (the admin panel, a
 * shop). On work.janoubona.net it is janoubona.net; where both share one
 * address (develop, local) it is this one with `?site=main`.
 */
export function mainSiteUrl(path = '/'): string {
  const { protocol, hostname, port } = window.location
  if (hostname.startsWith('work.')) {
    const host = hostname.slice('work.'.length)
    return `${protocol}//${host}${port ? `:${port}` : ''}${path}`
  }
  const separator = path.includes('?') ? '&' : '?'
  return `${path}${separator}site=main`
}
