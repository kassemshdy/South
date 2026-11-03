/**
 * The last answer to a small public query, kept in the browser so the next
 * visit starts from it.
 *
 * The menu and the home page's section order are chosen by an administrator
 * and fetched on every load. Until the answer arrived, both rendered a
 * built-in default -- every menu item, and the home page's original three
 * sections -- and then jumped to the saved one: the menu "appears long then
 * collapses", the page shows the old hero first (the owners' report, 30 Oct
 * 2026). Starting from the last answer this browser saw removes the jump for
 * everyone who has been here before; the query still refetches at once and
 * replaces it.
 *
 * Only for public, non-personal data. Storage can be missing or full, so every
 * access is guarded and a failure just means the default is shown.
 */

const PREFIX = 'south.remembered.'

export function readRemembered<T>(name: string): T | undefined {
  try {
    const raw = window.localStorage.getItem(PREFIX + name)
    return raw ? (JSON.parse(raw) as T) : undefined
  } catch {
    return undefined
  }
}

export function writeRemembered(name: string, value: unknown): void {
  try {
    window.localStorage.setItem(PREFIX + name, JSON.stringify(value))
  } catch {
    // Nothing to do: the next visit shows the default for a moment.
  }
}
