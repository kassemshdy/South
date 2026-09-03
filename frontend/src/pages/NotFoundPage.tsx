import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

export function NotFoundPage() {
  const t = useT()
  useSeo({ title: t('notFound.seoTitle'), noIndex: true })

  return (
    <div className="container-page flex flex-col items-center justify-center py-24 text-center">
      <p className="text-6xl font-bold text-clay-300">404</p>
      <h1 className="mt-4 text-2xl">{t('notFound.title')}</h1>
      <p className="mt-2 max-w-md text-ink-500">{t('notFound.body')}</p>
      <div className="mt-8 flex gap-3">
        <Button asChild>
          <Link to="/">{t('notFound.home')}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/businesses">{t('nav.directory')}</Link>
        </Button>
      </div>
    </div>
  )
}
