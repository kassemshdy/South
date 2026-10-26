import { useI18n } from '@/i18n'
import { formatDate } from '@/utils/format'

/** The descriptive fields a physical good may carry; all optional. */
export interface ProductFactFields {
  good_type: string | null
  brand_name: string | null
  ingredients: string | null
  manufactured_at: string | null
  expiry_date: string | null
  net_weight: string | null
  external_link: string | null
}

/**
 * Only http(s) becomes a link. The server refuses anything else now, but a
 * link saved before that rule could still be ``javascript:``, and an
 * ``href`` is where it would run.
 */
function isWebLink(value: string): boolean {
  return /^https?:\/\//i.test(value.trim())
}

export function hasProductFacts(item: ProductFactFields): boolean {
  return Boolean(
    item.good_type ||
      item.brand_name ||
      item.ingredients ||
      item.manufactured_at ||
      item.expiry_date ||
      item.net_weight ||
      item.external_link,
  )
}

/**
 * A product's details as a definition list -- on its own page and in the
 * quick view a shop page opens, so the two never describe a product
 * differently. Renders only the fields the owner filled in.
 */
export function ProductFacts({ item }: { item: ProductFactFields }) {
  const { t, locale } = useI18n()
  return (
    <dl className="grid gap-4 sm:grid-cols-2">
      {item.good_type ? (
        <div>
          <dt className="text-sm font-semibold text-ink-500">{t('products.goodTypeLabel')}</dt>
          <dd className="mt-1 text-ink-700">{item.good_type}</dd>
        </div>
      ) : null}
      {item.brand_name ? (
        <div>
          <dt className="text-sm font-semibold text-ink-500">{t('products.brandNameLabel')}</dt>
          <dd className="mt-1 text-ink-700">{item.brand_name}</dd>
        </div>
      ) : null}
      {item.net_weight ? (
        <div>
          <dt className="text-sm font-semibold text-ink-500">{t('products.netWeightLabel')}</dt>
          <dd className="mt-1 text-ink-700">{item.net_weight}</dd>
        </div>
      ) : null}
      {item.manufactured_at ? (
        <div>
          <dt className="text-sm font-semibold text-ink-500">{t('products.manufacturedAtLabel')}</dt>
          <dd className="mt-1 text-ink-700">{formatDate(item.manufactured_at, locale)}</dd>
        </div>
      ) : null}
      {item.expiry_date ? (
        <div>
          <dt className="text-sm font-semibold text-ink-500">{t('products.expiryDateLabel')}</dt>
          <dd className="mt-1 text-ink-700">{formatDate(item.expiry_date, locale)}</dd>
        </div>
      ) : null}
      {item.ingredients ? (
        <div className="sm:col-span-2">
          <dt className="text-sm font-semibold text-ink-500">{t('products.ingredientsLabel')}</dt>
          <dd className="mt-1 whitespace-pre-line leading-relaxed text-ink-700" dir="auto">
            {item.ingredients}
          </dd>
        </div>
      ) : null}
      {item.external_link ? (
        <div className="sm:col-span-2">
          <dt className="text-sm font-semibold text-ink-500">{t('products.externalLinkLabel')}</dt>
          <dd className="mt-1">
            {isWebLink(item.external_link) ? (
              <a
                href={item.external_link}
                target="_blank"
                rel="noopener noreferrer"
                className="break-all text-brand-700 underline"
              >
                {item.external_link}
              </a>
            ) : (
              <span className="break-all text-ink-700">{item.external_link}</span>
            )}
          </dd>
        </div>
      ) : null}
    </dl>
  )
}
