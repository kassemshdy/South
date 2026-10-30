import { AlertTriangle, Check } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useAuth } from '@/features/auth/AuthContext'
import { ChoicePageShell } from '@/features/onboarding/ChoicePageShell'
import { DoorBody, doorCard } from '@/features/onboarding/DoorCard'
import { destinationFor, JOBS_DOORS, type Door } from '@/features/onboarding/destinations'
import { useScrollToStep } from '@/hooks/useScrollToStep'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

/**
 * Jobs: the homepage's third door, at `/jobs-hub` (the owners' ticket, 29 Oct
 * 2026). Jobs used to be a door on each of `/offer` and `/browse`; they are
 * gathered here instead, with three choices -- post an offer, see who is
 * looking for work, or ask for a job.
 *
 * Asking for a job is listing yourself, so it behaves as the doors on
 * `/offer` do: a link to the public application for somebody with no
 * account, and the responsibility notice before the dashboard for an owner
 * who has one. The other two are plain links.
 */
export function JobsHubPage() {
  const t = useT()
  const { isAuthenticated } = useAuth()
  useSeo({ title: `${t('jobsHub.title')} | ${t('app.name')}`, description: t('jobsHub.subtitle') })

  const [pending, setPending] = useState<Door | null>(null)
  useScrollToStep(pending ? `pending:${pending.key}` : 'doors')

  if (pending) {
    return (
      <ChoicePageShell page="jobs" title={t('consent.heading')} subtitle={t(pending.titleKey)}>
        <div className="mx-auto max-w-2xl rounded-2xl border-2 border-clay-300 bg-white p-6 sm:p-8">
          <span
            className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-brand-800"
            aria-hidden="true"
          >
            <AlertTriangle className="h-6 w-6" />
          </span>
          <p className="mt-5 leading-relaxed text-ink-700 sm:text-lg">{t('consent.body')}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link to={destinationFor(pending, isAuthenticated)}>
                <Check className="h-5 w-5" aria-hidden="true" />
                {t('consent.agree')}
              </Link>
            </Button>
            <Button type="button" variant="ghost" size="lg" onClick={() => setPending(null)}>
              {t('onboarding.back')}
            </Button>
          </div>
        </div>
      </ChoicePageShell>
    )
  }

  return (
    <ChoicePageShell page="jobs" title={t('jobsHub.title')} subtitle={t('jobsHub.subtitle')}>
      <div className="mx-auto max-w-3xl">
        <h2 className="text-lg font-bold text-ink-900">{t('jobsHub.doorsTitle')}</h2>
        <ul className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {JOBS_DOORS.map((door) => (
            <li key={door.key} className="min-w-0">
              {isAuthenticated && door.applyHref ? (
                <button type="button" className={doorCard('jobs')} onClick={() => setPending(door)}>
                  <DoorBody door={door} />
                </button>
              ) : (
                <Link to={destinationFor(door, isAuthenticated)} className={doorCard('jobs')}>
                  <DoorBody door={door} />
                </Link>
              )}
            </li>
          ))}
        </ul>
      </div>
    </ChoicePageShell>
  )
}
