import { Eye } from 'lucide-react'

import { useT } from '@/i18n'
import { viewAsStorage } from '@/services/api/client'

/**
 * Says, on every page of a view, whose account this is and whether changes
 * are saved (a manager's editing session) or not, with the way back to the
 * administrator's own session. Read once per render: starting or ending a
 * view reloads the page.
 */
export function ViewAsBanner() {
  const t = useT()
  const session = viewAsStorage.get()
  if (!session) return null

  const end = () => {
    viewAsStorage.end()
    window.location.assign(`/admin/users/${encodeURIComponent(session.userId)}`)
  }

  return (
    <div className="sticky top-0 z-50 bg-clay-600 text-white print:hidden" role="status">
      <div className="container-page flex flex-wrap items-center justify-between gap-3 py-2 text-sm">
        <p className="flex items-center gap-2 font-semibold">
          <Eye className="h-4 w-4 shrink-0" aria-hidden="true" />
          {t(session.canEdit ? 'viewAs.bannerEdit' : 'viewAs.banner', {
            name: session.name ?? t('admin.userNoName'),
          })}
        </p>
        <button
          type="button"
          onClick={end}
          className="rounded-lg bg-white px-3 py-1 font-semibold text-clay-700 hover:bg-clay-50"
        >
          {t('viewAs.end')}
        </button>
      </div>
    </div>
  )
}
