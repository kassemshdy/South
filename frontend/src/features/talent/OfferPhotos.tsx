import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImageUp, Package, Trash2 } from 'lucide-react'
import { useRef } from 'react'

import { Button } from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { ownerTalentApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { OwnerTalent, TalentServiceOffer } from '@/types/api'
import { formatPrice } from '@/utils/format'

/**
 * A photo for each saved priced service, so it shows like a product card on
 * the profile and the services page (the owners' review, 12 Nov 2026).
 * Services are added and priced in the details tab; a photo can be added
 * once a service is saved, as for a shop's products.
 */
export function OfferPhotos({ profile }: { profile: OwnerTalent }) {
  const t = useT()
  const offers = profile.service_offers ?? []

  if (offers.length === 0) {
    return (
      <div className="rounded-xl border-2 border-dashed border-ink-100 p-6 text-center">
        <Package className="mx-auto h-7 w-7 text-ink-300" aria-hidden="true" />
        <p className="mt-2 text-ink-700">{t('offerPhotos.empty')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-500">{t('offerPhotos.intro')}</p>
      <ul className="grid gap-3 sm:grid-cols-2">
        {offers.map((offer) => (
          <li key={offer.id}>
            <OfferPhotoRow offer={offer} />
          </li>
        ))}
      </ul>
    </div>
  )
}

function OfferPhotoRow({ offer }: { offer: TalentServiceOffer }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const price = formatPrice(offer.price_from, offer.currency)

  const done = (result: OwnerTalent) => queryClient.setQueryData(queryKeys.myTalent, result)
  const fail = (error: unknown) =>
    toast.error(t('states.errorFallback'), error instanceof ApiError ? error.message : undefined)

  const upload = useMutation({
    mutationFn: (file: File) => ownerTalentApi.uploadOfferImage(offer.id, file),
    onSuccess: done,
    onError: fail,
  })
  const remove = useMutation({
    mutationFn: () => ownerTalentApi.deleteOfferImage(offer.id),
    onSuccess: done,
    onError: fail,
  })

  return (
    <div className="flex items-center gap-3 rounded-xl border border-ink-100 bg-white p-3">
      <span className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-sand-100">
        {offer.image_url ? (
          <img
            src={offer.image_thumb_url ?? offer.image_url}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          <span className="flex h-full items-center justify-center text-sand-500">
            <Package className="h-6 w-6" aria-hidden="true" />
          </span>
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold">{offer.title}</p>
        {price ? <p className="ltr-nums text-sm text-brand-800">{price}</p> : null}
        <div className="mt-1.5 flex flex-wrap gap-1">
          <Button
            size="sm"
            variant="outline"
            loading={upload.isPending}
            onClick={() => fileRef.current?.click()}
          >
            <ImageUp className="h-4 w-4" aria-hidden="true" />
            {offer.image_url ? t('offerPhotos.replace') : t('offerPhotos.add')}
          </Button>
          {offer.image_url ? (
            <Button
              size="sm"
              variant="ghost"
              className="text-clay-600"
              loading={remove.isPending}
              onClick={() => remove.mutate()}
              aria-label={t('offerPhotos.remove')}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </Button>
          ) : null}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) upload.mutate(file)
            event.target.value = ''
          }}
        />
      </div>
    </div>
  )
}
