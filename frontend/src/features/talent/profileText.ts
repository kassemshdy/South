/**
 * Turning a profile's free-text fields into lists.
 *
 * Owners paste whatever they have into "services offered", "training" and
 * "skills": numbered lists, dashes, a heading line, and often each entry
 * twice, once per language ("1. <Arabic>" then "<English>" on the next
 * line). Shown as one pre-formatted block in a narrow column that read as a
 * wall of broken lines, so each entry becomes an item of its own.
 */

/** A leading list marker: a dash or bullet, or a number with "." or ")". */
const MARKER = /^\s*(?:[-*•–·]|\d{1,2}\s*[.)\-])\s*/
const NUMBERED = /^\s*\d{1,2}\s*[.)\-]\s*/

export interface ListItem {
  /** The entry itself, marker removed. */
  main: string
  /** Lines that belong to it: the other-language version of a numbered entry. */
  sub: string[]
}

export interface ParsedList {
  /** Lines before the first numbered entry of a numbered list (a heading). */
  intro: string[]
  items: ListItem[]
}

function lines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
}

/**
 * One item per line, except in a numbered list: there, an unnumbered line
 * belongs to the numbered one above it, and lines before the first number
 * are its heading.
 */
export function parseList(text: string): ParsedList {
  const all = lines(text)
  const numbered = all.some((line) => NUMBERED.test(line))
  if (!numbered) {
    return { intro: [], items: all.map((line) => ({ main: line.replace(MARKER, ''), sub: [] })) }
  }
  const intro: string[] = []
  const items: ListItem[] = []
  for (const line of all) {
    if (NUMBERED.test(line)) {
      items.push({ main: line.replace(NUMBERED, ''), sub: [] })
    } else if (items.length === 0) {
      intro.push(line.replace(MARKER, ''))
    } else {
      items[items.length - 1]!.sub.push(line.replace(MARKER, ''))
    }
  }
  return { intro, items }
}

/** Short enough to show as chips rather than a list: skills, mostly. */
export function isChipList(text: string): boolean {
  const all = lines(text)
  return all.length > 1 && all.every((line) => line.replace(MARKER, '').length <= 40)
}

/**
 * The direction a block of owner text reads in, from its first strong
 * letter. `dir="auto"` does the same per element, but a list needs one
 * direction for all its items so the bullets line up on one side. Code
 * points, not a character class: no Arabic text in source (test_i18n.py).
 */
export function textDirection(text: string): 'ltr' | 'rtl' {
  for (const char of text) {
    const code = char.codePointAt(0) ?? 0
    if ((code >= 0x0590 && code <= 0x08ff) || (code >= 0xfb1d && code <= 0xfefc)) return 'rtl'
    if (/[A-Za-zÀ-ɏ]/.test(char)) return 'ltr'
  }
  return 'rtl'
}

/** Every line of a field, marker removed. */
export function plainLines(text: string): string[] {
  return lines(text).map((line) => line.replace(MARKER, ''))
}
