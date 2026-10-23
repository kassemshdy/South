import { Download } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { useToast } from '@/components/ui/Toast'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi, type ExportDataset } from '@/services/api/endpoints'

const DATASETS: { key: ExportDataset; labelKey: TranslationKey }[] = [
  { key: 'businesses', labelKey: 'admin.exportBusinesses' },
  { key: 'products', labelKey: 'admin.exportProducts' },
  { key: 'users', labelKey: 'admin.exportUsers' },
  { key: 'talent', labelKey: 'admin.exportTalent' },
  { key: 'orders', labelKey: 'admin.exportOrders' },
]

/**
 * The site's data as spreadsheets: one CSV per dataset, opened by Excel with
 * the Arabic intact (the API writes a byte-order mark for that). The files
 * carry what the review screens carry, owners' identity and customers'
 * phone numbers included.
 */
export function AdminExportPage() {
  const t = useT()
  const toast = useToast()
  const [busy, setBusy] = useState<ExportDataset | null>(null)

  const download = async (dataset: ExportDataset) => {
    setBusy(dataset)
    try {
      const { blob, filename } = await adminApi.exportCsv(dataset)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename ?? `${dataset}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      toast.error(t('admin.exportFailed'), error instanceof ApiError ? error.message : undefined)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.exportHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.exportSubtitle')}</p>
      </header>
      <Card>
        <CardBody className="divide-y divide-ink-100 p-0">
          {DATASETS.map(({ key, labelKey }) => (
            <div key={key} className="flex items-center justify-between gap-3 p-4">
              <span className="font-semibold">{t(labelKey)}</span>
              <Button
                size="sm"
                variant="outline"
                loading={busy === key}
                onClick={() => void download(key)}
              >
                <Download className="h-4 w-4" aria-hidden="true" />
                {t('admin.exportDownload')}
              </Button>
            </div>
          ))}
        </CardBody>
      </Card>
    </div>
  )
}
