import { ArrowLeft, Briefcase, Wrench } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { useSeo } from '@/hooks/useSeo'
import { useT } from '@/i18n'

/** Work's front page: what the site is, and the two ways in. */
export function WorkHomePage() {
  const t = useT()
  useSeo({ title: `${t('work.brand')} | ${t('work.tagline')}`, canonicalPath: '/' })

  return (
    <>
      <section className="bg-brand-800 text-white">
        <div className="container-page py-16 sm:py-24">
          <p className="text-lg font-semibold text-brand-100" dir="ltr">
            {t('work.brand')}
          </p>
          <h1 className="mt-2 max-w-3xl text-3xl text-white sm:text-5xl">{t('work.tagline')}</h1>
          <p className="mt-4 max-w-2xl text-lg text-brand-100">{t('work.intro')}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg" variant="outline" className="bg-white text-brand-800">
              <Link to="/services">
                <Wrench className="h-5 w-5" aria-hidden="true" />
                {t('nav.services')}
                <ArrowLeft className="h-4 w-4 ltr:rotate-180" aria-hidden="true" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-white bg-transparent text-white hover:bg-white/10 hover:text-white"
            >
              <Link to="/jobs">
                <Briefcase className="h-5 w-5" aria-hidden="true" />
                {t('nav.jobs')}
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </>
  )
}
