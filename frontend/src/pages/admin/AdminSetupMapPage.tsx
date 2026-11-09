import { ChevronDown } from 'lucide-react'
import { useState } from 'react'

import { Card, CardBody } from '@/components/ui/Card'
import { useT, type TranslationKey } from '@/i18n'
import { cn } from '@/utils/cn'

type SetupStatus = 'ok' | 'partial' | 'missing'
type SetupSection = 'entry' | 'center' | 'harness' | 'tools' | 'checks' | 'ship' | 'knowledge'

/**
 * How the team works with Claude, as a map (the owners' request, 9 Nov
 * 2026): from where a request starts, through the rules and checks around
 * it, to the live site. Each item opens a short explanation. The statuses
 * are kept by hand here: update this list when a piece is added.
 */
export const SETUP_MAP: { section: SetupSection; items: { key: string; status: SetupStatus }[] }[] = [
  { section: 'entry', items: [{ key: 'app', status: 'ok' }, { key: 'board', status: 'ok' }, { key: 'routine', status: 'ok' }, { key: 'telegram', status: 'ok' }] },
  { section: 'center', items: [{ key: 'claude', status: 'ok' }, { key: 'subagents', status: 'partial' }] },
  { section: 'harness', items: [{ key: 'rules', status: 'ok' }, { key: 'skills', status: 'ok' }, { key: 'permissions', status: 'partial' }, { key: 'plan', status: 'ok' }, { key: 'memory', status: 'partial' }, { key: 'hooks', status: 'missing' }] },
  { section: 'tools', items: [{ key: 'github', status: 'ok' }, { key: 'railway', status: 'ok' }, { key: 'sentry', status: 'ok' }, { key: 'south', status: 'ok' }, { key: 'playwright', status: 'ok' }, { key: 'web', status: 'ok' }, { key: 'reviewer', status: 'missing' }] },
  { section: 'checks', items: [{ key: 'ci', status: 'ok' }, { key: 'guards', status: 'ok' }, { key: 'preflight', status: 'ok' }, { key: 'visual', status: 'partial' }, { key: 'localgate', status: 'missing' }] },
  { section: 'ship', items: [{ key: 'develop', status: 'ok' }, { key: 'master', status: 'ok' }, { key: 'backups', status: 'ok' }, { key: 'telegram', status: 'ok' }] },
  { section: 'knowledge', items: [{ key: 'repo', status: 'ok' }, { key: 'claude', status: 'ok' }, { key: 'docs', status: 'ok' }, { key: 'locales', status: 'ok' }, { key: 'design', status: 'missing' }, { key: 'handoff', status: 'missing' }, { key: 'board', status: 'ok' }] },
]

const STATUS_STYLE: Record<SetupStatus, string> = {
  ok: 'bg-emerald-500',
  partial: 'bg-amber-500',
  missing: 'bg-red-500',
}

export function AdminSetupMapPage() {
  const t = useT()
  const missing = SETUP_MAP.flatMap(({ section, items }) =>
    items.filter((item) => item.status === 'missing').map((item) => ({ section, ...item })),
  )

  // English for the developers whatever the site's language, so it reads
  // left to right too.
  return (
    <div className="space-y-6 text-left" dir="ltr">
      <header>
        <h1 className="text-3xl" dir="ltr">{t('setupMap.title')}</h1>
        <p className="mt-2 max-w-3xl text-ink-500">{t('setupMap.subtitle')}</p>
        <div className="mt-3 flex flex-wrap gap-4 text-sm text-ink-600">
          {(['ok', 'partial', 'missing'] as const).map((status) => (
            <span key={status} className="inline-flex items-center gap-1.5">
              <span className={cn('h-3 w-3 rounded-full', STATUS_STYLE[status])} aria-hidden="true" />
              {t(`setupMap.${status}` as TranslationKey)}
            </span>
          ))}
          <span className="text-ink-400">{t('setupMap.updated')}</span>
        </div>
      </header>

      <Card className="border-brand-200 bg-brand-50/50">
        <CardBody>
          <h2 className="font-bold">{t('setupMap.sec.you.title')}</h2>
          <p className="mt-1 text-sm text-ink-600">{t('setupMap.youText')}</p>
        </CardBody>
      </Card>

      <ol className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {SETUP_MAP.map(({ section, items }, index) => (
          <li key={section}>
            <Card className="h-full">
              <CardBody className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">
                  {index + 2}
                </p>
                <h2 className="text-lg font-bold">
                  {t(`setupMap.sec.${section}.title` as TranslationKey)}
                </h2>
                <p className="text-sm text-ink-500">
                  {t(`setupMap.sec.${section}.sub` as TranslationKey)}
                </p>
                <ul className="space-y-2 pt-1">
                  {items.map((item) => (
                    <SetupItem key={item.key} section={section} item={item.key} status={item.status} />
                  ))}
                </ul>
              </CardBody>
            </Card>
          </li>
        ))}
      </ol>

      {missing.length > 0 ? (
        <Card className="border-red-200">
          <CardBody>
            <h2 className="font-bold">{t('setupMap.missingTitle')}</h2>
            <ul className="mt-2 list-inside list-disc text-sm text-ink-600">
              {missing.map(({ section, key }) => (
                <li key={`${section}.${key}`}>
                  {t(`setupMap.${section}.${key}.title` as TranslationKey)}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      ) : null}
    </div>
  )
}

function SetupItem({
  section,
  item,
  status,
}: {
  section: SetupSection
  item: string
  status: SetupStatus
}) {
  const t = useT()
  const [open, setOpen] = useState(false)
  const base = `setupMap.${section}.${item}`
  return (
    <li className="rounded-xl border border-ink-100">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-start gap-3 px-3 py-2.5 text-left"
      >
        <span
          className={cn('mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full', STATUS_STYLE[status])}
          aria-label={t(`setupMap.${status}` as TranslationKey)}
        />
        <span className="min-w-0 flex-1">
          <span className="block font-semibold">
            {t(`${base}.title` as TranslationKey)}
          </span>
          <span className="block text-sm text-ink-500">{t(`${base}.short` as TranslationKey)}</span>
        </span>
        <ChevronDown
          className={cn('mt-1 h-4 w-4 shrink-0 text-ink-400 transition-transform', open && 'rotate-180')}
          aria-hidden="true"
        />
      </button>
      {open ? (
        <p className="border-t border-ink-100 px-3 py-2.5 text-sm leading-relaxed text-ink-700">
          {t(`${base}.details` as TranslationKey)}
        </p>
      ) : null}
    </li>
  )
}
