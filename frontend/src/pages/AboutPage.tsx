import { ClipboardCheck, HandHeart, MapPin } from 'lucide-react'

import { Card, CardBody } from '@/components/ui/Card'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

export function AboutPage() {
  const t = useT()
  useSeo({ title: `${t('about.title')} | ${t('app.name')}`, description: t('about.intro') })

  const points = [
    { icon: MapPin, title: t('about.pointLocalTitle'), body: t('about.pointLocalBody') },
    { icon: ClipboardCheck, title: t('about.pointReviewTitle'), body: t('about.pointReviewBody') },
    { icon: HandHeart, title: t('about.pointCommunityTitle'), body: t('about.pointCommunityBody') },
  ]

  return (
    <div className="container-page py-14">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-2xl sm:text-3xl">{t('about.title')}</h1>
        <p className="mt-4 leading-relaxed text-ink-700">{t('about.intro')}</p>
      </div>

      <div className="mx-auto mt-10 grid max-w-4xl gap-4 sm:grid-cols-3">
        {points.map(({ icon: Icon, title, body }) => (
          <Card key={title}>
            <CardBody className="text-center">
              <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-sand-100 text-clay-600">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <h2 className="mt-3 font-bold">{title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-ink-500">{body}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      <p className="mx-auto mt-10 max-w-2xl text-center leading-relaxed text-ink-500">
        {t('about.closing')}
      </p>
    </div>
  )
}
