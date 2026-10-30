import { useQuery } from '@tanstack/react-query'
import { CalendarDays, CalendarPlus, Download, MapPin } from 'lucide-react'
import { useParams } from 'react-router-dom'

import { BackLink } from '@/components/ui/BackLink'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { downloadIcs, googleCalendarHref } from '@/features/activities/calendar'
import { useSeo } from '@/hooks/useSeo'
import { useI18n } from '@/i18n'
import { activityApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import { formatDateTime } from '@/utils/format'

/**
 * One development activity: its photograph, what it is, when and where,
 * and -- when it has a date -- a way to put it in the visitor's own
 * calendar, as Google Calendar's page or as an `.ics` file for any other.
 */
export function ActivityPage() {
  const { slug = '' } = useParams()
  const { t, locale } = useI18n()
  const activity = useQuery({
    queryKey: queryKeys.activity(slug),
    queryFn: () => activityApi.bySlug(slug),
    enabled: slug.length > 0,
  })
  const data = activity.data
  const canonicalPath = `/activities/${encodeURIComponent(slug)}`
  useSeo({
    title: data ? `${data.title} | ${t('app.name')}` : t('activities.title'),
    description: (data?.summary ?? data?.body)?.slice(0, 160),
    canonicalPath,
  })

  if (activity.isLoading) {
    return (
      <div className="container-page py-10">
        <Skeleton className="h-96 rounded-2xl" />
      </div>
    )
  }
  if (activity.isError || !data) {
    return (
      <div className="container-page py-16">
        <ErrorState error={activity.error} onRetry={() => void activity.refetch()} />
      </div>
    )
  }

  const pageUrl = `${window.location.origin}${canonicalPath}`
  const google = googleCalendarHref(data, pageUrl)

  return (
    <article className="container-page py-10">
      <BackLink fallback="/activities" />
      <div className="mt-4 grid gap-8 lg:grid-cols-3">
        <div className="min-w-0 lg:col-span-2">
          {data.image_url ? (
            <img
              src={data.image_url}
              alt=""
              className="aspect-[16/9] w-full rounded-2xl object-cover"
            />
          ) : null}
          <h1 className="mt-6 text-2xl sm:text-3xl" dir="auto">
            {data.title}
          </h1>
          {data.summary ? (
            <p className="mt-3 text-lg text-ink-500" dir="auto">
              {data.summary}
            </p>
          ) : null}
          <p className="mt-6 whitespace-pre-line leading-loose text-ink-700" dir="auto">
            {data.body}
          </p>
        </div>

        <aside>
          <Card>
            <CardBody className="space-y-4 p-5">
              {data.starts_at ? (
                <p className="flex items-start gap-2 text-ink-700">
                  <CalendarDays className="mt-0.5 h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                  <span>
                    {formatDateTime(data.starts_at, locale)}
                    {data.ends_at ? ` – ${formatDateTime(data.ends_at, locale)}` : null}
                  </span>
                </p>
              ) : null}
              {data.location ? (
                <p className="flex items-start gap-2 text-ink-700" dir="auto">
                  <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-clay-600" aria-hidden="true" />
                  {data.location}
                </p>
              ) : null}
              {google ? (
                <div className="space-y-2 border-t border-ink-100 pt-4">
                  <h2 className="text-lg">{t('activities.addToCalendar')}</h2>
                  <Button asChild block>
                    <a href={google} target="_blank" rel="noopener noreferrer">
                      <CalendarPlus className="h-5 w-5" aria-hidden="true" />
                      {t('activities.googleCalendar')}
                    </a>
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    block
                    onClick={() => downloadIcs(data, pageUrl)}
                  >
                    <Download className="h-5 w-5" aria-hidden="true" />
                    {t('activities.icsFile')}
                  </Button>
                </div>
              ) : null}
              {!data.starts_at && !data.location ? (
                <p className="text-ink-500">{t('activities.noDate')}</p>
              ) : null}
            </CardBody>
          </Card>
        </aside>
      </div>
    </article>
  )
}
