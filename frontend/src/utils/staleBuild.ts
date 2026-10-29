/**
 * Recovering a page that was open across a release.
 *
 * Every deploy replaces the hashed files under `/assets`, and the old ones
 * are gone (they answer 404). A tab opened before the release still holds
 * the old `index-*.js`, so the first time it opens a lazily loaded screen
 * (most of the admin area, the dashboard) it asks for a chunk that no
 * longer exists, the import fails, and with nothing to catch it React
 * leaves a white page until someone refreshes. Refreshing loads the new
 * build, which is why it "fixes itself".
 *
 * The cure is the refresh, done for the visitor: reload once. Once, because
 * a chunk that is missing for some other reason would otherwise reload
 * forever; a second failure within the window falls through to the error
 * boundary, which shows a retry button instead of a blank page.
 */

const KEY = "south.staleBuildReload";
const WINDOW_MS = 15_000;

const CHUNK_ERROR =
  /dynamically imported module|Importing a module script failed|error loading dynamically imported module|Unable to preload CSS/i;

export function isChunkLoadError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return CHUNK_ERROR.test(message);
}

/** Reloads the page unless it already did so moments ago. True if it did. */
export function reloadOnce(): boolean {
  try {
    const last = Number(window.sessionStorage.getItem(KEY) ?? 0);
    if (Date.now() - last < WINDOW_MS) return false;
    window.sessionStorage.setItem(KEY, String(Date.now()));
  } catch {
    // Without storage there is no way to know whether this is a loop.
    return false;
  }
  window.location.reload();
  return true;
}

/** Vite reports a failed lazy import as `vite:preloadError` before React sees it. */
export function installStaleBuildRecovery(): void {
  window.addEventListener("vite:preloadError", (event) => {
    if (reloadOnce()) event.preventDefault();
  });
}
