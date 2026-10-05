import { ArrowRight } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { useT } from '@/i18n'

/**
 * «Back», at the top of a listing page.
 *
 * A visitor who came from a directory goes back to it as they left it --
 * the same filters, sort and scroll position -- which a plain link to the
 * directory would lose. Someone who arrived from outside (a shared link, a
 * search engine) has no in-site page to return to, so the link takes them
 * to `fallback`, the directory the listing belongs to.
 *
 * React Router keeps the position in its own history stack in
 * `history.state.idx`: 0 means this is the first page of the visit.
 */
export function BackLink({ fallback }: { fallback: string }) {
  const t = useT()
  const navigate = useNavigate()

  return (
    <Link
      to={fallback}
      onClick={(event) => {
        const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0
        if (idx > 0) {
          event.preventDefault()
          navigate(-1)
        }
      }}
      className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-500 hover:text-brand-700"
    >
      {/* Pointing the way the page reads from: right in Arabic, left in
          English. */}
      <ArrowRight className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
      {t('common.back')}
    </Link>
  )
}
