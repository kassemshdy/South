import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useDefaultJobLinks } from '@/features/jobs/JobLinksSidebar'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi, siteSettingsApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { JobLink, JobLinkAudience } from '@/types/api'

const AUDIENCES: [JobLinkAudience, TranslationKey][] = [
  ['both', 'admin.jobLinkAudienceBoth'],
  ['employers', 'admin.jobLinkAudienceEmployers'],
  ['seekers', 'admin.jobLinkAudienceSeekers'],
]

/**
 * The useful links beside the candidates and the vacancies (the owners'
 * request, 9 Nov 2026). Starts from the site's own list until staff save
 * theirs; saving an empty list hides the sidebar, and the reset button goes
 * back to the starting list.
 */
export function JobLinksEditor() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const fallback = useDefaultJobLinks()
  const saved = useQuery({ queryKey: queryKeys.jobLinks, queryFn: siteSettingsApi.jobLinks })
  const [links, setLinks] = useState<JobLink[] | null>(null)
  useEffect(() => {
    if (saved.data && links === null) setLinks(saved.data.links ?? fallback)
  }, [saved.data, links, fallback])

  const save = useMutation({
    mutationFn: (next: JobLink[] | null) => adminApi.setJobLinks(next),
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.jobLinks, result)
      setLinks(result.links ?? fallback)
      toast.success(t('wizard.saved'))
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })

  const edit = (index: number, change: Partial<JobLink>) =>
    setLinks((prev) => (prev ?? []).map((link, i) => (i === index ? { ...link, ...change } : link)))
  const move = (index: number, by: number) =>
    setLinks((prev) => {
      const next = [...(prev ?? [])]
      const [item] = next.splice(index, 1)
      if (item) next.splice(index + by, 0, item)
      return next
    })

  return (
    <Card>
      <CardBody className="space-y-4">
        <div>
          <h2 className="text-xl font-bold">{t('admin.jobLinksHeading')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('admin.jobLinksHint')}</p>
        </div>
        {saved.isError ? (
          <ErrorState error={saved.error} onRetry={() => void saved.refetch()} />
        ) : links === null ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <>
            {links.map((link, index) => (
              <fieldset
                key={index}
                className="grid gap-3 rounded-xl border border-ink-100 p-4 sm:grid-cols-2"
              >
                <Field label={t('admin.jobLinkTitle')}>
                  {(props) => (
                    <Input
                      {...props}
                      dir="auto"
                      maxLength={80}
                      value={link.title}
                      onChange={(event) => edit(index, { title: event.target.value })}
                    />
                  )}
                </Field>
                <Field label={t('admin.jobLinkUrl')}>
                  {(props) => (
                    <Input
                      {...props}
                      dir="ltr"
                      maxLength={500}
                      value={link.url}
                      placeholder="https://"
                      onChange={(event) => edit(index, { url: event.target.value })}
                    />
                  )}
                </Field>
                <Field label={t('admin.jobLinkNote')}>
                  {(props) => (
                    <Input
                      {...props}
                      dir="auto"
                      maxLength={160}
                      value={link.note ?? ''}
                      onChange={(event) => edit(index, { note: event.target.value || null })}
                    />
                  )}
                </Field>
                <Field label={t('admin.jobLinkAudience')}>
                  {(props) => (
                    <select
                      {...props}
                      className="min-h-12 w-full rounded-xl border-2 border-ink-100 bg-white px-3"
                      value={link.audience}
                      onChange={(event) =>
                        edit(index, { audience: event.target.value as JobLinkAudience })
                      }
                    >
                      {AUDIENCES.map(([value, label]) => (
                        <option key={value} value={value}>
                          {t(label)}
                        </option>
                      ))}
                    </select>
                  )}
                </Field>
                <div className="flex gap-2 sm:col-span-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={index === 0}
                    aria-label={t('admin.jobLinkUp')}
                    onClick={() => move(index, -1)}
                  >
                    <ArrowUp className="h-4 w-4" aria-hidden="true" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={index === links.length - 1}
                    aria-label={t('admin.jobLinkDown')}
                    onClick={() => move(index, 1)}
                  >
                    <ArrowDown className="h-4 w-4" aria-hidden="true" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setLinks(links.filter((_, i) => i !== index))}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                    {t('admin.jobLinkRemove')}
                  </Button>
                </div>
              </fieldset>
            ))}
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  setLinks([...links, { title: '', url: '', note: null, audience: 'both' }])
                }
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                {t('admin.jobLinkAdd')}
              </Button>
              <Button loading={save.isPending} onClick={() => save.mutate(links)}>
                {t('common.save')}
              </Button>
              <Button variant="ghost" disabled={save.isPending} onClick={() => save.mutate(null)}>
                {t('admin.jobLinksReset')}
              </Button>
            </div>
          </>
        )}
      </CardBody>
    </Card>
  )
}
