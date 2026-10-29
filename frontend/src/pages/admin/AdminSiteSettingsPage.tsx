import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { CoverUpload } from '@/features/admin/CoverUpload'
import { WELCOME_POSTERS, WELCOME_VIDEO_ID } from '@/features/home/WelcomeVideo'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { SiteSettings } from '@/types/api'

/**
 * The site's own contact details and social accounts, shown in the header,
 * the footer and on /contact. A field left empty is not shown anywhere.
 *
 * Every label is the one the public site already uses for the same thing, so
 * the admin reads the same words a visitor will.
 */
const FIELDS: {
  key: keyof SiteSettings
  labelKey: TranslationKey
  // 'text' for the links: a browser's own url check refuses facebook.com/…
  // without a scheme, which the server adds itself.
  type: 'tel' | 'email' | 'text'
  placeholder: string
}[] = [
  {
    key: 'contact_phone',
    labelKey: 'contactChannel.PHONE',
    type: 'tel',
    placeholder: '+961 …',
  },
  {
    key: 'contact_whatsapp',
    labelKey: 'platform.WHATSAPP',
    type: 'tel',
    placeholder: '+961 …',
  },
  {
    key: 'contact_email',
    labelKey: 'contactChannel.EMAIL',
    type: 'email',
    placeholder: '@',
  },
  {
    key: 'social_facebook',
    labelKey: 'platform.FACEBOOK',
    type: 'text',
    placeholder: 'https://facebook.com/…',
  },
  {
    key: 'social_instagram',
    labelKey: 'platform.INSTAGRAM',
    type: 'text',
    placeholder: 'https://instagram.com/…',
  },
  {
    // The homepage video (round 3). Stored as an id; shown as a link.
    key: 'home_video',
    labelKey: 'admin.homeVideoLabel',
    type: 'text',
    placeholder: 'https://www.youtube.com/watch?v=…',
  },
  {
    // The "how to register" video on /offer. Its heading and text are on the
    // pages screen.
    key: 'offer_video',
    labelKey: 'admin.offerVideoLabel',
    type: 'text',
    placeholder: 'https://www.youtube.com/watch?v=…',
  },
]

const asLink = (id: string | null) => (id ? `https://www.youtube.com/watch?v=${id}` : null)

/** The API returns each video as an id; the field holds a link, as pasted. */
const asForm = (settings: SiteSettings): SiteSettings => ({
  ...settings,
  home_video: asLink(settings.home_video),
  offer_video: asLink(settings.offer_video),
})

const EMPTY: SiteSettings = {
  contact_phone: null,
  contact_whatsapp: null,
  contact_email: null,
  social_facebook: null,
  social_instagram: null,
  home_video: null,
  offer_video: null,
}

export function AdminSiteSettingsPage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const current = useQuery({
    queryKey: queryKeys.adminSiteSettings,
    queryFn: adminApi.siteSettings,
  })
  const [values, setValues] = useState<SiteSettings>(EMPTY)

  useEffect(() => {
    if (current.data) setValues(asForm(current.data))
  }, [current.data])

  const save = useMutation({
    mutationFn: adminApi.updateSiteSettings,
    onSuccess: (saved) => {
      setValues(asForm(saved))
      queryClient.setQueryData(queryKeys.adminSiteSettings, saved)
      // The header and footer read the public copy; refresh it too.
      void queryClient.invalidateQueries({ queryKey: queryKeys.siteSettings })
      toast.success(t('wizard.saved'))
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate(values)
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-3xl">{t('nav.contact')}</h1>

      {current.isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : current.isError ? (
        <ErrorState error={current.error} onRetry={() => void current.refetch()} />
      ) : (
        <Card>
          <CardBody>
            <form onSubmit={submit} className="space-y-5">
              {FIELDS.map((field) => (
                <Field key={field.key} label={t(field.labelKey)}>
                  {(props) => (
                    <Input
                      {...props}
                      type={field.type}
                      dir="ltr"
                      value={values[field.key] ?? ''}
                      placeholder={field.placeholder}
                      onChange={(event) =>
                        setValues((prev) => ({
                          ...prev,
                          [field.key]: event.target.value || null,
                        }))
                      }
                    />
                  )}
                </Field>
              ))}
              <Button type="submit" disabled={save.isPending}>
                {t('common.save')}
              </Button>
            </form>
          </CardBody>
        </Card>
      )}

      <CredentialsMessage />

      <VideoPosters homeVideo={current.data?.home_video ?? null} />
    </div>
  )
}

/**
 * The WhatsApp message a new password is sent in, in the administrator's
 * own words -- a welcome, a link to the site's channel or group (the owners'
 * request). It must keep {phone} and {password}; the server refuses one that
 * drops either. Empty goes back to the site's default, which the box starts
 * from. Admin-only on the server, since a group link may be private.
 */
function CredentialsMessage() {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const saved = useQuery({
    queryKey: queryKeys.adminCredentialsMessage,
    queryFn: adminApi.credentialsMessage,
  })
  const fallback = t('credentials.whatsappMessage')
  const [text, setText] = useState('')
  useEffect(() => {
    if (saved.data) setText(saved.data.message ?? fallback)
  }, [saved.data, fallback])

  const save = useMutation({
    mutationFn: (message: string | null) => adminApi.setCredentialsMessage(message),
    onSuccess: (result) => {
      queryClient.setQueryData(queryKeys.adminCredentialsMessage, result)
      toast.success(t('wizard.saved'))
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })

  return (
    <Card>
      <CardBody className="space-y-3">
        <h2 className="text-xl font-bold">{t('admin.credentialsMessageHeading')}</h2>
        <p className="text-sm text-ink-500">{t('admin.credentialsMessageHint')}</p>
        {saved.isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : saved.isError ? (
          <ErrorState error={saved.error} onRetry={() => void saved.refetch()} />
        ) : (
          <>
            <Textarea
              aria-label={t('admin.credentialsMessageHeading')}
              dir="auto"
              rows={8}
              maxLength={2000}
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                loading={save.isPending}
                onClick={() => save.mutate(text.trim() === fallback.trim() ? null : text)}
              >
                {t('common.save')}
              </Button>
              <Button
                variant="ghost"
                disabled={save.isPending}
                onClick={() => {
                  setText(fallback)
                  save.mutate(null)
                }}
              >
                {t('admin.credentialsMessageReset')}
              </Button>
            </div>
          </>
        )}
      </CardBody>
    </Card>
  )
}

/**
 * The still each video shows before it is played. Kept with the videos'
 * links because the two go together: a new recording usually wants a new
 * picture, and one of somebody else must not keep the old face.
 */
function VideoPosters({ homeVideo }: { homeVideo: string | null }) {
  const t = useT()
  const covers = useQuery({ queryKey: queryKeys.adminPageCovers, queryFn: adminApi.pageCovers })
  const cover = (key: 'home_video' | 'offer_video') =>
    covers.data?.find((item) => item.page_key === key)
  const home = cover('home_video')
  const offer = cover('offer_video')

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">{t('admin.videoPostersHeading')}</h2>
        <p className="mt-1 text-sm text-ink-500">{t('admin.videoPostersHint')}</p>
      </div>
      {covers.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : covers.isError ? (
        <ErrorState error={covers.error} onRetry={() => void covers.refetch()} />
      ) : (
        <>
          {home ? (
            <CoverUpload
              cover={home}
              title={t('admin.pageHomeLabel')}
              hint={t('admin.videoPosterHint')}
              fallbackSrc={WELCOME_POSTERS[homeVideo ?? WELCOME_VIDEO_ID] ?? null}
              resetLabel={t('admin.videoPosterRemove')}
            />
          ) : null}
          {offer ? (
            <CoverUpload
              cover={offer}
              title={t('admin.pageOfferVideoLabel')}
              hint={t('admin.videoPosterHint')}
              fallbackSrc={null}
              resetLabel={t('admin.videoPosterRemove')}
            />
          ) : null}
        </>
      )}
    </section>
  )
}
