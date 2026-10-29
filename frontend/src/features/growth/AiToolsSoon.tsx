import { Clapperboard, ImageUp, Sparkles } from 'lucide-react'

import { useT } from '@/i18n'

/**
 * What is coming for sellers (the owners' request, 29 Oct 2026): product
 * photographs and short promotional videos made with AI from the seller's
 * own pictures. Shown as coming soon, with nothing to press, so it promises
 * the tools without pretending they already exist.
 */
export function AiToolsSoon() {
  const t = useT()
  const tools = [
    { icon: ImageUp, title: t('aiTools.imagesTitle'), body: t('aiTools.imagesBody') },
    { icon: Clapperboard, title: t('aiTools.videoTitle'), body: t('aiTools.videoBody') },
  ]
  return (
    <section className="mt-10 rounded-2xl border-2 border-dashed border-wheat-300 bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <Sparkles className="h-5 w-5 text-wheat-600" aria-hidden="true" />
        <h2 className="text-xl">{t('aiTools.heading')}</h2>
        <span className="rounded-full bg-wheat-100 px-2.5 py-0.5 text-xs font-bold text-wheat-700">
          {t('aiTools.soon')}
        </span>
      </div>
      <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {tools.map(({ icon: Icon, title, body }) => (
          <li key={title} className="flex gap-3 rounded-xl bg-sand-50 p-4" aria-disabled="true">
            <Icon className="mt-0.5 h-6 w-6 shrink-0 text-brand-700" aria-hidden="true" />
            <div className="min-w-0">
              <p className="font-semibold text-ink-900">{title}</p>
              <p className="mt-1 text-sm text-ink-500">{body}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
