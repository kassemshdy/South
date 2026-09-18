import { Fragment } from 'react'

/**
 * An article body as written: plain text, with bare URLs turned into links.
 *
 * Admins type into a textarea rather than a rich-text editor, so a link
 * arrives as literal text — `https://www.upwork.com` in the middle of a
 * paragraph. Splitting the string on a URL pattern and building anchors from
 * the pieces keeps the body a string the whole way through: nothing is ever
 * parsed as HTML, so no article can inject markup regardless of what was
 * typed into it.
 *
 * Whitespace is preserved by the caller's `whitespace-pre-line`, which is
 * what makes paragraph breaks in the textarea survive to the page.
 */

/** Capturing, so `split` hands back the URLs interleaved with the text. */
const URL_PATTERN = /(https?:\/\/[^\s]+)/g

/**
 * Punctuation that ends the sentence rather than the address in it. A URL at
 * the end of an Arabic sentence is followed immediately by a full stop or by
 * the Arabic comma (U+060C) or semicolon (U+061B) with no space, and all of
 * those are legal in a path — so they are peeled off the end and rendered
 * as the text they are.
 *
 * The Arabic punctuation is written as escapes, not as itself: the
 * no-Arabic-in-source guard (backend/tests/test_i18n.py) scans this
 * directory for Arabic codepoints, and a regex class is not a catalog.
 */
const TRAILING_PUNCTUATION = /[.,:;!?)\]}\u00bb"'\u060c\u061b]+$/u

export function ArticleBody({ text }: { text: string }) {
  return (
    <>
      {text.split(URL_PATTERN).map((part, index) => {
        // Odd indices are the capture group: every other piece is a URL.
        if (index % 2 === 0) return <Fragment key={index}>{part}</Fragment>

        const trailing = TRAILING_PUNCTUATION.exec(part)?.[0] ?? ''
        const href = trailing ? part.slice(0, -trailing.length) : part

        return (
          <Fragment key={index}>
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer nofollow"
              // An LTR address inside RTL prose: `dir` isolates it, so the
              // surrounding Arabic does not reorder the domain.
              dir="ltr"
              className="break-all font-medium text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-600"
            >
              {href}
            </a>
            {trailing}
          </Fragment>
        )
      })}
    </>
  )
}
