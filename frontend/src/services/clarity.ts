/**
 * Microsoft Clarity — heatmaps and session replay for the public directory.
 *
 * Wired like Sentry and the analytics tag before it: a `VITE_`-prefixed
 * variable set per service in Railway, and **completely inert without it**. No
 * project id means no script tag, no network request, no recording — so local
 * development and the test suite never phone home, and a developer's own
 * clicks never land in the numbers.
 *
 * ## Why this one is gated harder than the analytics tag
 *
 * Clarity is not a page counter. It records the session: pointer movement,
 * clicks, scrolling, and a reconstruction of the page that can be played back
 * afterwards. Everything `services/analytics.ts` says about the query string
 * applies here and then some, because the screens behind a sign-in are not
 * pages of a catalogue — they are:
 *
 * - the owner's account page, which holds the legal name, birth year, gender,
 *   marital status, place of civil registration and place of residence that
 *   `AGENTS.md` calls the one thing standing between those columns and the
 *   open internet;
 * - the moderation queue, which shows all of that for **every** owner, plus
 *   identity documents and CVs;
 * - the credentials panel, which puts an issued password on screen in
 *   plaintext so an administrator can relay it.
 *
 * A replay of any of those is a disclosure, so the rule here is not "skip
 * those page views" — it is **never start recording in the first place**.
 *
 * ## What that means in practice
 *
 * A session recorder cannot be un-started: once the tag is on the page it
 * records the rest of the session, SPA navigations included, and there is no
 * "forget the last minute". So the decision has to be made *before* the script
 * loads, from what is knowable then. Two gates, both checked at that moment:
 *
 * 1. **Nobody signed in.** Every private screen is behind authentication, so
 *    the absence of a session token is a reliable proxy for "this visitor
 *    cannot reach one without signing in first" — and signing in is a full
 *    navigation to `/dashboard`, by which point this has already decided not
 *    to load. An owner or an administrator is therefore never recorded at all.
 * 2. **Not already on a private path**, which catches a reload while signed
 *    in before the token check has any state to read.
 *
 * The consequence is deliberate and worth stating: Clarity here measures
 * **anonymous visitors browsing the public directory**, which is the only
 * question it was added to answer. It will not tell you anything about how
 * owners use their dashboard, and that is the trade.
 *
 * ## The half this code cannot enforce
 *
 * Masking is a setting in the Clarity dashboard, not something the tag takes
 * as a parameter, so the project should be set to **Strict** masking there.
 * The gates above mean a recording should never contain a private screen in
 * the first place; strict masking is what makes that survive a mistake —
 * including the one screen a signed-out visitor does type into, the public
 * application form, where they enter the phone number that becomes their
 * login.
 */

const PROJECT_ID = import.meta.env.VITE_CLARITY_PROJECT_ID as string | undefined

/** The same key `services/api/client.ts` stores the session token under. */
const TOKEN_STORAGE_KEY = 'south.auth.token'

/** Paths that must never appear in a recording. See the note above. */
const PRIVATE_PREFIXES = ['/dashboard', '/admin'] as const

/** True only when a project id is configured. */
export const clarityEnabled = Boolean(PROJECT_ID)

let started = false

function someoneIsSignedIn(): boolean {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY) !== null
  } catch {
    // Private browsing can throw on storage access. Unreadable means unknown,
    // and unknown resolves to "do not record" — the failure that costs a
    // datapoint rather than the one that leaks a screen.
    return true
  }
}

function onPrivatePath(): boolean {
  const path = window.location.pathname
  return PRIVATE_PREFIXES.some((prefix) => path.startsWith(prefix))
}

/**
 * Load the Clarity tag once, if configured and if this session may be
 * recorded at all.
 *
 * Called from `main.tsx` at startup and nowhere else: the gates are only
 * meaningful before the script exists, so there is deliberately no way to
 * start it later from a route change.
 */
export function initClarity(): void {
  if (!PROJECT_ID || started || typeof document === 'undefined') return
  if (someoneIsSignedIn() || onPrivatePath()) return
  started = true

  // Microsoft's own snippet, as a function rather than an inline <script>, so
  // it is subject to the gates above instead of running the moment the
  // document parses.
  const script = document.createElement('script')
  script.async = true
  script.src = `https://www.clarity.ms/tag/${PROJECT_ID}`
  document.head.appendChild(script)
}
