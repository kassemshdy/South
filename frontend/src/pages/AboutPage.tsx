import { ClipboardCheck, HandHeart, MapPin } from 'lucide-react'

import { Card, CardBody } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ArticleBody } from '@/features/articles/ArticleBody'
import { usePageText } from '@/hooks/usePageText'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

export function AboutPage() {
  const t = useT()
  const page = usePageText('about')
  const title = page.title ?? t('about.title')
  useSeo({
    title: `${title} | ${t('app.name')}`,
    description: page.summary ?? page.body?.slice(0, 160) ?? t('about.intro'),
  })

  // Wait for the administrator's text rather than flash the built-in page
  // and swap it out a moment later.
  if (!page.ready) {
    return (
      <div className="container-page py-14">
        <Skeleton className="mx-auto h-96 max-w-2xl" />
      </div>
    )
  }

  // Once an administrator has written the page, it is theirs: their text
  // replaces the built-in introduction, points and closing line entirely.
  if (page.body) {
    return (
      <div className="container-page py-14">
        <article className="mx-auto max-w-2xl">
          <h1 className="text-center text-2xl sm:text-3xl">{title}</h1>
          <div className="mt-8 whitespace-pre-line text-lg leading-loose text-ink-700">
            <ArticleBody text={page.body} />
          </div>
        </article>
      </div>
    )
  }

  const points = [
    { icon: MapPin, title: t('about.pointLocalTitle'), body: t('about.pointLocalBody') },
    { icon: ClipboardCheck, title: t('about.pointReviewTitle'), body: t('about.pointReviewBody') },
    { icon: HandHeart, title: t('about.pointCommunityTitle'), body: t('about.pointCommunityBody') },
  ]

  return (
    <div className="container-page py-14">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-2xl sm:text-3xl">{title}</h1>
        <p className="mt-4 leading-relaxed text-ink-700">{t('about.intro')}</p>
      </div>

      <div className="mx-auto mt-10 grid max-w-4xl gap-4 sm:grid-cols-3">
        {points.map(({ icon: Icon, title, body }) => (
          <Card key={title}>
            <CardBody className="text-center">
              <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-sand-100 text-brand-700">
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
