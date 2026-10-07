import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Input, Textarea } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useI18n, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { PageKey, PageText, PageTextInput } from '@/types/api'

/**
 * Where each page lives on the public site, what the admin screen calls it,
 * and the built-in text each field falls back to -- shown as the empty
 * field's placeholder, so the admin can see what a blank field means.
 */
const PAGES: Record<
  PageKey,
  {
    path: string
    labelKey: TranslationKey
    /** One key, or several shown one per line (a list's built-in items). */
    defaults: Record<Field, TranslationKey | TranslationKey[]>
    /** What each field is called and says about itself, where it differs
     * from a whole page's title, summary and body. */
    labels?: Partial<Record<Field, TranslationKey>>
    hints?: Partial<Record<Field, TranslationKey>>
  }
> = {
  about: {
    path: '/about',
    labelKey: 'nav.about',
    defaults: { title: 'about.title', summary: 'footer.aboutBody', body: 'about.intro' },
  },
  offer_eligibility: {
    path: '/offer',
    labelKey: 'offerPage.eligibilityTitle',
    defaults: {
      title: 'offerPage.eligibilityTitle',
      summary: 'offerPage.eligibilityNote',
      body: ['offerPage.eligibilityOne', 'offerPage.eligibilityTwo'],
    },
    labels: { summary: 'admin.pageEligibilityNoteLabel', body: 'admin.pageEligibilityListLabel' },
    hints: { summary: 'admin.pageEligibilityNoteHint', body: 'admin.pageEligibilityListHint' },
  },
}

type Field = 'title' | 'summary' | 'body'
type Lang = 'ar' | 'en'

const LANGUAGES: { lang: Lang; labelKey: TranslationKey }[] = [
  { lang: 'ar', labelKey: 'nav.localeArabic' },
  { lang: 'en', labelKey: 'nav.localeEnglish' },
]

const EMPTY: PageTextInput = {
  title_ar: null,
  title_en: null,
  summary_ar: null,
  summary_en: null,
  body_ar: null,
  body_en: null,
}

export function AdminPagesPage() {
  const { t } = useI18n()
  const pages = useQuery({ queryKey: queryKeys.adminPages, queryFn: adminApi.pages })

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl">{t('admin.navPages')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.pagesSubtitle')}</p>
      </div>

      {pages.isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : pages.isError ? (
        <ErrorState error={pages.error} onRetry={() => void pages.refetch()} />
      ) : (
        pages.data?.map((page) => <PageForm key={page.key} page={page} />)
      )}
    </div>
  )
}

function PageForm({ page }: { page: PageText }) {
  const { t, locale } = useI18n()
  const toast = useToast()
  const queryClient = useQueryClient()
  const meta = PAGES[page.key]
  const [values, setValues] = useState<PageTextInput>(EMPTY)

  useEffect(() => {
    const { key: _key, ...text } = page
    setValues(text)
  }, [page])

  const save = useMutation({
    mutationFn: (input: PageTextInput) => adminApi.updatePage(page.key, input),
    onSuccess: (saved) => {
      queryClient.setQueryData<PageText[]>(queryKeys.adminPages, (previous) =>
        previous?.map((item) => (item.key === saved.key ? saved : item)),
      )
      // The page itself, and the footer on every page, read the public copy.
      void queryClient.invalidateQueries({ queryKey: queryKeys.page(page.key) })
      toast.success(t('wizard.saved'))
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : t('states.errorFallback')),
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate(values)
  }

  const set = (name: keyof PageTextInput, value: string) =>
    setValues((previous) => ({ ...previous, [name]: value || null }))

  // Only the catalog in use is loaded, so the built-in text can be shown as a
  // placeholder in the reader's own language and not the other one.
  const placeholder = (lang: Lang, field: Field) => {
    if (lang !== locale) return undefined
    const keys = meta.defaults[field]
    return Array.isArray(keys) ? keys.map((key) => t(key)).join('\n') : t(keys)
  }

  return (
    <Card>
      <CardBody>
        <form onSubmit={submit} className="space-y-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl font-bold">{t(meta.labelKey)}</h2>
            <Link
              to={meta.path}
              target="_blank"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:text-brand-600"
            >
              {t('admin.pageView')}
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>

          {LANGUAGES.map(({ lang, labelKey }) => (
            <fieldset key={lang} className="space-y-4 rounded-xl border border-ink-100 p-4">
              <legend className="px-1 text-sm font-bold text-ink-700">{t(labelKey)}</legend>
              <Field label={t('admin.pageTitleLabel')}>
                {(props) => (
                  <Input
                    {...props}
                    dir={lang === 'ar' ? 'rtl' : 'ltr'}
                    maxLength={200}
                    value={values[`title_${lang}`] ?? ''}
                    placeholder={placeholder(lang, 'title')}
                    onChange={(event) => set(`title_${lang}`, event.target.value)}
                  />
                )}
              </Field>
              <Field
                label={t(meta.labels?.summary ?? 'admin.pageSummaryLabel')}
                hint={t(meta.hints?.summary ?? 'admin.pageSummaryHint')}
              >
                {(props) => (
                  <Textarea
                    {...props}
                    dir={lang === 'ar' ? 'rtl' : 'ltr'}
                    rows={4}
                    maxLength={1500}
                    value={values[`summary_${lang}`] ?? ''}
                    placeholder={placeholder(lang, 'summary')}
                    onChange={(event) => set(`summary_${lang}`, event.target.value)}
                  />
                )}
              </Field>
              <Field
                label={t(meta.labels?.body ?? 'admin.pageBodyLabel')}
                hint={t(meta.hints?.body ?? 'admin.pageBodyHint')}
              >
                {(props) => (
                  <Textarea
                    {...props}
                    dir={lang === 'ar' ? 'rtl' : 'ltr'}
                    rows={14}
                    maxLength={20000}
                    value={values[`body_${lang}`] ?? ''}
                    placeholder={placeholder(lang, 'body')}
                    onChange={(event) => set(`body_${lang}`, event.target.value)}
                  />
                )}
              </Field>
            </fieldset>
          ))}

          <Button type="submit" disabled={save.isPending}>
            {t('common.save')}
          </Button>
        </form>
      </CardBody>
    </Card>
  )
}
