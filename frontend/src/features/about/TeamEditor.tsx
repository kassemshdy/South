import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ImagePlus, Trash2, UserRound } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Textarea } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { TeamMember } from '@/types/api'

/** The six places of the about page's team section, for an administrator. */
export function TeamEditor() {
  const t = useT()
  const team = useQuery({ queryKey: queryKeys.adminTeam, queryFn: adminApi.team })

  return (
    <Card>
      <CardBody className="space-y-5">
        <div>
          <h2 className="text-xl font-bold">{t('about.teamHeading')}</h2>
          <p className="mt-1 text-sm text-ink-500">{t('admin.teamSubtitle')}</p>
        </div>
        {team.isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2">
            {(team.data ?? []).map((member) => (
              <TeamSlot key={member.slot} member={member} />
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  )
}

function TeamSlot({ member }: { member: TeamMember }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [captionAr, setCaptionAr] = useState(member.caption_ar ?? '')
  const [captionEn, setCaptionEn] = useState(member.caption_en ?? '')

  useEffect(() => {
    setCaptionAr(member.caption_ar ?? '')
    setCaptionEn(member.caption_en ?? '')
  }, [member.caption_ar, member.caption_en])

  const saved = (next: TeamMember) => {
    queryClient.setQueryData<TeamMember[]>(queryKeys.adminTeam, (previous) =>
      previous?.map((entry) => (entry.slot === next.slot ? next : entry)),
    )
    void queryClient.invalidateQueries({ queryKey: queryKeys.team })
    toast.success(t('wizard.saved'))
  }
  const failed = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : t('states.errorFallback'))

  const caption = useMutation({
    mutationFn: () =>
      adminApi.setTeamCaption(member.slot, {
        caption_ar: captionAr || null,
        caption_en: captionEn || null,
      }),
    onSuccess: saved,
    onError: failed,
  })
  const photo = useMutation({
    mutationFn: (file: File) => adminApi.setTeamPhoto(member.slot, file),
    onSuccess: saved,
    onError: failed,
  })
  const removePhoto = useMutation({
    mutationFn: () => adminApi.removeTeamPhoto(member.slot),
    onSuccess: saved,
    onError: failed,
  })

  return (
    <li className="space-y-3 rounded-xl border border-ink-100 p-4">
      <p className="text-sm font-bold text-ink-700">
        {t('admin.teamSlot', { number: String(member.slot) })}
      </p>
      <div className="flex items-center gap-3">
        {member.photo_url ? (
          <img src={member.photo_url} alt="" className="h-20 w-20 rounded-full object-cover" />
        ) : (
          <span className="flex h-20 w-20 items-center justify-center rounded-full bg-sand-100 text-sand-500">
            <UserRound className="h-8 w-8" aria-hidden="true" />
          </span>
        )}
        <div className="flex flex-wrap gap-2">
          <input
            ref={input}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) photo.mutate(file)
              event.target.value = ''
            }}
          />
          <Button size="sm" variant="outline" loading={photo.isPending} onClick={() => input.current?.click()}>
            <ImagePlus className="h-4 w-4" aria-hidden="true" />
            {member.photo_url ? t('admin.pageCoversReplace') : t('admin.pageCoversUpload')}
          </Button>
          {member.photo_url ? (
            <Button size="sm" variant="ghost" loading={removePhoto.isPending} onClick={() => removePhoto.mutate()}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {t('admin.teamRemovePhoto')}
            </Button>
          ) : null}
        </div>
      </div>
      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault()
          caption.mutate()
        }}
      >
        <Field label={t('admin.teamCaptionAr')}>
          {(props) => (
            <Textarea
              {...props}
              dir="rtl"
              rows={2}
              maxLength={300}
              value={captionAr}
              onChange={(event) => setCaptionAr(event.target.value)}
            />
          )}
        </Field>
        <Field label={t('admin.teamCaptionEn')}>
          {(props) => (
            <Textarea
              {...props}
              dir="ltr"
              rows={2}
              maxLength={300}
              value={captionEn}
              onChange={(event) => setCaptionEn(event.target.value)}
            />
          )}
        </Field>
        <Button type="submit" size="sm" loading={caption.isPending}>
          {t('common.save')}
        </Button>
      </form>
    </li>
  )
}
