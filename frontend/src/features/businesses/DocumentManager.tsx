import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Loader2, Trash2, Upload } from 'lucide-react'
import { useRef, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { ownerApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { OwnerBusiness } from '@/types/api'

const MAX_BYTES = 10 * 1024 * 1024
const ACCEPTED = 'application/pdf,image/jpeg,image/png'

/**
 * The listing's official papers — commercial register, licence, permit.
 *
 * **Optional, and the screen says so twice**: once in the hint under the
 * heading and once where the list would be. That is not padding. A shop with
 * no paperwork is still a shop, and somebody who reads an empty upload box as
 * an obligation will either invent a document or abandon the application —
 * both worse than an empty list. Nothing here blocks submission, and
 * `backend/tests/test_business_documents.py` pins that it never starts to.
 *
 * Type and size are checked here so the answer is immediate and in Arabic;
 * the server checks again by reading the real bytes, because a check in a
 * browser is a courtesy, not a control.
 */
export function DocumentManager({
  business,
  maxDocuments = 6,
}: {
  business: OwnerBusiness
  maxDocuments?: number
}) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const t = useT()
  const inputRef = useRef<HTMLInputElement>(null)
  const [label, setLabel] = useState('')

  const documents = business.documents ?? []
  const atLimit = documents.length >= maxDocuments

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusiness(business.id) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.myBusinesses })
  }

  const upload = useMutation({
    mutationFn: (file: File) =>
      ownerApi.uploadDocument(business.id, file, label.trim() || undefined),
    onSuccess: () => {
      toast.success(t('businessDocuments.uploaded'))
      setLabel('')
      invalidate()
    },
    onError: (error) =>
      toast.error(
        t('businessDocuments.uploadFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  const remove = useMutation({
    mutationFn: (documentId: string) => ownerApi.deleteDocument(business.id, documentId),
    onSuccess: () => {
      toast.success(t('businessDocuments.deleted'))
      invalidate()
    },
    onError: (error) =>
      toast.error(
        t('businessDocuments.deleteFailed'),
        error instanceof ApiError ? error.message : undefined,
      ),
  })

  const handleFile = (file: File | undefined) => {
    if (!file) return
    if (!ACCEPTED.split(',').includes(file.type)) {
      toast.error(t('businessDocuments.badType'), t('businessDocuments.badTypeDescription'))
      return
    }
    if (file.size > MAX_BYTES) {
      toast.error(t('businessDocuments.tooLarge'), t('businessDocuments.tooLargeDescription'))
      return
    }
    upload.mutate(file)
  }

  return (
    <section className="space-y-4">
      <div>
        <h3 className="font-bold">
          {t('businessDocuments.title')}
          <span className="ms-2 rounded-full bg-sand-100 px-2 py-0.5 text-xs font-normal text-ink-500">
            {t('wizard.optionalStep')}
          </span>
        </h3>
        <p className="mt-1 text-sm leading-relaxed text-ink-500">
          {t('businessDocuments.hint')}
        </p>
      </div>

      <div className="rounded-xl border-2 border-dashed border-ink-100 bg-sand-50 p-4">
        <label className="block text-sm font-semibold text-ink-700" htmlFor="document-label">
          {t('businessDocuments.labelField')}
        </label>
        <Input
          id="document-label"
          value={label}
          maxLength={120}
          placeholder={t('businessDocuments.labelPlaceholder')}
          onChange={(event) => setLabel(event.target.value)}
          className="mt-1"
        />

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="sr-only"
          onChange={(event) => {
            handleFile(event.target.files?.[0])
            // Reset so selecting the same file twice still fires a change.
            event.target.value = ''
          }}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-3"
          disabled={atLimit || upload.isPending}
          onClick={() => inputRef.current?.click()}
        >
          {upload.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              {t('businessDocuments.uploading')}
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" aria-hidden="true" />
              {t('businessDocuments.add')}
            </>
          )}
        </Button>
        <p className="mt-2 text-xs text-ink-400">
          {atLimit
            ? t('businessDocuments.limitReached', { max: maxDocuments })
            : t('businessDocuments.formats')}
        </p>
      </div>

      {documents.length === 0 ? (
        <p className="text-sm text-ink-500">{t('businessDocuments.empty')}</p>
      ) : (
        <ul className="space-y-2">
          {documents.map((document) => (
            <li
              key={document.id}
              className="flex items-center gap-3 rounded-xl border border-ink-100 bg-white p-3"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-olive-100 text-olive-700">
                <FileText className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-semibold text-ink-900">
                  {document.label ?? document.original_filename ?? t('businessDocuments.untitled')}
                </span>
                {document.label && document.original_filename ? (
                  <span className="block truncate text-xs text-ink-400">
                    {document.original_filename}
                  </span>
                ) : null}
              </span>
              <button
                type="button"
                onClick={() => remove.mutate(document.id)}
                disabled={remove.isPending}
                className="rounded-lg p-2 text-clay-600 hover:bg-clay-50 disabled:opacity-40"
                aria-label={t('businessDocuments.delete')}
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
