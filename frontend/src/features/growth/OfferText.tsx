import { Fragment, type ReactNode } from 'react'

import { cn } from '@/utils/cn'

/**
 * WhatsApp's own bold, `*like this*`, so the offer can be pasted from the
 * message it was written in and read the same here. Anything else is text.
 */
function withBold(line: string): ReactNode[] {
  return line.split(/(\*[^*\n]+\*)/g).map((part, index) =>
    part.length > 2 && part.startsWith('*') && part.endsWith('*') ? (
      <strong key={index}>{part.slice(1, -1)}</strong>
    ) : (
      <Fragment key={index}>{part}</Fragment>
    ),
  )
}

/**
 * The offer as typed, with its section titles bold: a short line that opens
 * a paragraph (the first line, or one after a blank line) and is not a
 * bullet. Plain text in, so the manager edits words, not markup. Shared by
 * the admin growth page and the visitors' popup.
 */
export function OfferText({ text, className }: { text: string; className?: string }) {
  const lines = text.split('\n')
  return (
    <div className={cn('leading-relaxed text-ink-900', className)}>
      {lines.map((line, index) => {
        if (line.trim() === '') return <div key={index} className="h-3" />
        const opens = index === 0 || lines[index - 1]?.trim() === ''
        const title = opens && line.length <= 60 && !line.trimStart().startsWith('•')
        return (
          <p key={index} className={cn(title && 'font-bold text-brand-900', index === 0 && 'text-lg')}>
            {withBold(line)}
          </p>
        )
      })}
    </div>
  )
}
