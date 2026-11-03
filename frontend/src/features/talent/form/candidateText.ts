/**
 * The two checks on what a job seeker types, mirrored from the API
 * (`app/core/candidate_text.py`) so the form can say so while they type:
 * the bio holds no contact details, and the name is a person's name.
 * The API enforces both regardless.
 */

// Seven or more digits, Western or Arabic-Indic, with the separators people use.
const PHONE = /(?:[0-9\u0660-\u0669\u06f0-\u06f9][\s\-./()]*){7,}/
const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]+/
const LINK = /(?:https?:\/\/|www\.)|\b[\w-]+\.(?:com|net|org|me|lb|io|co)\b/i

export function containsContactDetails(text: string | null | undefined): boolean {
  if (!text) return false
  return PHONE.test(text) || EMAIL.test(text) || LINK.test(text)
}

// Arabic or Latin letters, Arabic vowel marks, and the joiners inside a name.
const NAME_CHARS = /^[\p{Script=Arabic}\p{Script=Latin}\s\-'’]+$/u
const LETTER = /[\p{Script=Arabic}\p{Script=Latin}]/u
const ANY_DIGIT = /[\p{Nd}]/u

export function isPersonName(name: string): boolean {
  const trimmed = name.trim()
  if (!NAME_CHARS.test(trimmed) || ANY_DIGIT.test(trimmed)) return false
  const words = trimmed.split(/\s+/)
  const real = words.filter((word) => [...word].filter((char) => LETTER.test(char)).length >= 2)
  return words.length >= 2 && real.length >= 2
}
