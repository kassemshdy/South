import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImagePlus } from 'lucide-react'
import { useRef, type RefObject } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminBusiness, GoodsOrigin } from '@/types/api'
import { cn } from '@/utils/cn'

/**
 * Corrections an administrator makes on the owner's behalf: which door the
 * listing sits behind (its products move with it), and a logo or cover for a
 * listing that went live without one. The gallery and the products stay the
 * owner's; an administrator deletes a product, but does not add one.
 */
export function AdminCorrectionsCard({ business }: { business: AdminBusiness }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const logoInput = useRef<HTMLInputElement>(null)
  const coverInput = useRef<HTMLInputElement>(null)

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminBusiness(business.id) })
  }
  const failed = (error: unknown) =>
    toast.error(t('admin.correctionFailed'), error instanceof ApiError ? error.message : undefined)

  const origin = useMutation({
    mutationFn: (value: GoodsOrigin) => adminApi.setGoodsOrigin(business.id, value),
    onSuccess: () => {
      refresh()
      toast.success(t('admin.correctionSaved'))
    },
    onError: failed,
  })

  const image = useMutation({
    mutationFn: ({ file, kind }: { file: File; kind: 'LOGO' | 'COVER' }) =>
      adminApi.uploadBrandImage(business.id, file, kind),
    onSuccess: () => {
      refresh()
      toast.success(t('admin.correctionSaved'))
    },
    onError: failed,
  })

  const options: { value: GoodsOrigin; label: string }[] = [
    { value: 'LOCAL', label: t('directory.originLocal') },
    { value: 'IMPORTED', label: t('onboarding.importedTitle') },
  ]

  const picker = (kind: 'LOGO' | 'COVER', ref: RefObject<HTMLInputElement>) => (
    <>
      <input
        ref={ref}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        aria-label={t(kind === 'LOGO' ? 'images.logoTitle' : 'images.coverTitle')}
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) image.mutate({ file, kind })
          event.target.value = ''
        }}
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        loading={image.isPending && image.variables?.kind === kind}
        onClick={() => ref.current?.click()}
      >
        <ImagePlus className="h-4 w-4" aria-hidden="true" />
        {t(kind === 'LOGO' ? 'images.logoTitle' : 'images.coverTitle')}
      </Button>
    </>
  )

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-bold">{t('admin.correctionsTitle')}</h2>
      </CardHeader>
      <CardBody className="space-y-5">
        <div>
          <p className="text-sm font-semibold">{t('directory.origin')}</p>
          <p className="mt-0.5 text-sm text-ink-500">{t('admin.goodsOriginHint')}</p>
          <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label={t('directory.origin')}>
            {options.map((option) => {
              const active = business.goods_origin === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={active}
                  disabled={active || origin.isPending}
                  onClick={() => origin.mutate(option.value)}
                  className={cn(
                    'rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors',
                    active
                      ? 'bg-brand-700 text-white'
                      : 'bg-white text-ink-600 ring-1 ring-ink-100 hover:bg-sand-50',
                  )}
                >
                  {option.label}
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {picker('LOGO', logoInput)}
          {picker('COVER', coverInput)}
        </div>
      </CardBody>
    </Card>
  )
}
