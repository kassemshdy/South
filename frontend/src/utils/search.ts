/**
 * Loose text matching for searching a short list in the browser -- the
 * products inside one shop's page, which are all already loaded.
 *
 * Mirrors what `normalize_arabic` does for the server's search text, so a
 * visitor typing without hamza or diacritics finds the same things here as
 * in the directory: diacritics and tatweel dropped, the alef forms folded to
 * a bare alef, taa marbuta to haa and alef maqsura to yaa. Built from code
 * points because no Arabic may appear in source, escaped or not (AGENTS.md).
 */
const char = (code: number) => String.fromCharCode(code)
const range = (from: number, to: number) => `${char(from)}-${char(to)}`

const DIACRITICS = new RegExp(`[${range(0x064b, 0x065f)}${char(0x0670)}${char(0x0640)}]`, 'g')
const ALEF_FORMS = new RegExp(`[${[0x0622, 0x0623, 0x0625, 0x0671].map(char).join('')}]`, 'g')
const ALEF = char(0x0627)
const TAA_MARBUTA = new RegExp(char(0x0629), 'g')
const HAA = char(0x0647)
const ALEF_MAQSURA = new RegExp(char(0x0649), 'g')
const YAA = char(0x064a)

export function normalizeForSearch(value: string): string {
  return value
    .toLowerCase()
    .replace(DIACRITICS, '')
    .replace(ALEF_FORMS, ALEF)
    .replace(TAA_MARBUTA, HAA)
    .replace(ALEF_MAQSURA, YAA)
    .replace(/\s+/g, ' ')
    .trim()
}

/** Whether every word of the query appears somewhere in the fields. */
export function matchesSearch(query: string, ...fields: (string | null | undefined)[]): boolean {
  const words = normalizeForSearch(query).split(' ').filter(Boolean)
  if (words.length === 0) return true
  const haystack = normalizeForSearch(fields.filter(Boolean).join(' '))
  return words.every((word) => haystack.includes(word))
}
