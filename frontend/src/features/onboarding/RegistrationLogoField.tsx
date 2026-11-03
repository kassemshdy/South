/**
 * The shop's logo on the public application form.
 *
 * Required: a shop cannot be approved without a logo (the owners' decision,
 * 29 Oct 2026), so the applicant gives it with the application rather than
 * the reviewer having to add it afterwards (30 Oct 2026). A camera-sized
 * photo is shrunk here first, as the dashboard does, because the API
 * refuses anything over its upload limit.
 */

import { Upload } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Field } from '@/components/ui/Field'
import { MAX_IMAGE_BYTES } from '@/features/images/ImageManager'
import { useT } from '@/i18n'
import { shrinkImage } from '@/utils/shrinkImage'

/** What the API accepts as an image; anything else would be refused there. */
const LOGO_TYPES = ['image/jpeg', 'image/png', 'image/webp']

interface RegistrationLogoFieldProps {
  file: File | null
  error: string | undefined
  onPick: (file: File | null, error: string | null) => void
}

export function RegistrationLogoField({ file, error, onPick }: RegistrationLogoFieldProps) {
  const t = useT()
  const [preview, setPreview] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  return (
    <Field label={t('business.field.logo')} hint={t('images.logoHint')} required error={error}>
      {(props) => (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border-2 border-dashed border-sand-300 bg-sand-50 p-3">
          {preview ? (
            <img
              src={preview}
              alt=""
              className="size-16 shrink-0 rounded-xl border border-ink-100 bg-white object-cover"
            />
          ) : null}
          <input
            {...props}
            type="file"
            accept={LOGO_TYPES.join(',')}
            className="sr-only"
            data-testid="register-logo"
            onChange={async (event) => {
              const picked = event.target.files?.[0] ?? null
              if (!picked) {
                onPick(null, null)
                return
              }
              try {
                const small = await shrinkImage(picked, { maxBytes: MAX_IMAGE_BYTES })
                if (small.size > MAX_IMAGE_BYTES) {
                  onPick(null, t('register.logoTooLarge'))
                  return
                }
                onPick(small, null)
              } catch {
                onPick(null, t('register.logoUnreadable'))
              }
            }}
          />
          <label
            htmlFor={props.id}
            className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800"
          >
            <Upload className="h-4 w-4" aria-hidden="true" />
            {t('register.documentChoose')}
          </label>
          <span className="min-w-0 flex-1 truncate text-sm text-ink-500">
            {file ? file.name : t('register.documentNone')}
          </span>
        </div>
      )}
    </Field>
  )
}
