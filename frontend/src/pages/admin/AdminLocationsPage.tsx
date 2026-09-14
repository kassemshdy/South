import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useT, type TranslationKey } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { LocationNode, LocationType } from '@/types/api'

const TYPE_KEYS: Record<LocationType, TranslationKey> = {
  GOVERNORATE: 'admin.typeGovernorate',
  DISTRICT: 'admin.typeDistrict',
  TOWN: 'admin.typeTown',
}

export function AdminLocationsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [name, setName] = useState('')
  const [type, setType] = useState<LocationType>('TOWN')
  const [parentId, setParentId] = useState<string>('')
  const t = useT()

  const locations = useQuery({ queryKey: queryKeys.adminLocations, queryFn: adminApi.locations })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminLocations })
    void queryClient.invalidateQueries({ queryKey: queryKeys.locations })
  }

  const handleError = (error: unknown, fallback: string) =>
    toast.error(fallback, error instanceof ApiError ? error.message : undefined)

  const create = useMutation({
    mutationFn: () =>
      adminApi.createLocation({ name_ar: name.trim(), type, parent_id: parentId || null }),
    onSuccess: () => {
      setName('')
      toast.success(t('admin.locationAdded'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.locationAddFailed')),
  })

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<LocationNode> }) => adminApi.updateLocation(id, body),
    onSuccess: () => {
      toast.success(t('admin.locationSaved'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.locationSaveFailed')),
  })

  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteLocation(id),
    onSuccess: () => {
      toast.success(t('admin.locationDeleted'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.locationDeleteFailed')),
  })

  // Render the tree in reading order: governorate, then its districts, then towns.
  const tree = useMemo(() => {
    const all = locations.data ?? []
    const rows: { location: LocationNode; depth: number }[] = []
    const walk = (parent: string | null, depth: number) => {
      for (const location of all.filter((item) => item.parent_id === parent)) {
        rows.push({ location, depth })
        walk(location.id, depth + 1)
      }
    }
    walk(null, 0)
    return rows
  }, [locations.data])

  const parents = (locations.data ?? []).filter((item) => item.type !== 'TOWN')

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.locationsHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.locationsSubtitle')}</p>
      </header>

      <Card>
        <CardBody>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              if (name.trim().length >= 2) create.mutate()
            }}
            className="grid gap-3 sm:grid-cols-[1fr_auto_auto_auto]"
          >
            <div>
              <label htmlFor="new-location" className="sr-only">
                {t('admin.locationNameLabel')}
              </label>
              <Input id="new-location" value={name} onChange={(event) => setName(event.target.value)} placeholder={t('admin.locationNameLabel')} />
            </div>

            <Select value={type} onValueChange={(value) => setType(value as LocationType)}>
              <SelectTrigger className="sm:w-32" aria-label={t('admin.locationTypeAria')}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(TYPE_KEYS) as LocationType[]).map((option) => (
                  <SelectItem key={option} value={option}>
                    {t(TYPE_KEYS[option])}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={parentId || 'none'} onValueChange={(value) => setParentId(value === 'none' ? '' : value)}>
              <SelectTrigger className="sm:w-40" aria-label={t('admin.locationParentAria')}>
                <SelectValue placeholder={t('admin.locationNoParent')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">{t('admin.locationNoParent')}</SelectItem>
                {parents.map((parent) => (
                  <SelectItem key={parent.id} value={parent.id}>
                    {parent.name_ar}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button type="submit" loading={create.isPending} disabled={name.trim().length < 2}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t('admin.add')}
            </Button>
          </form>
        </CardBody>
      </Card>

      {locations.isLoading ? (
        <Skeleton className="h-96 rounded-2xl" />
      ) : locations.isError ? (
        <ErrorState error={locations.error} onRetry={() => void locations.refetch()} />
      ) : (
        <Card>
          <CardBody className="p-2">
            <ul>
              {tree.map(({ location, depth }) => (
                <li
                  key={location.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2.5 hover:bg-sand-50"
                  style={{ paddingInlineStart: `${depth * 20 + 12}px` }}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{location.name_ar}</span>
                    <Badge className="bg-sand-100 text-brand-700">
                      {t(TYPE_KEYS[location.type])}
                    </Badge>
                    {!location.is_active ? (
                      <Badge className="bg-ink-100 text-ink-700">{t('common.inactive')}</Badge>
                    ) : null}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => update.mutate({ id: location.id, body: { is_active: !location.is_active } })}
                    >
                      {location.is_active ? t('common.deactivate') : t('common.activate')}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="text-clay-600"
                      onClick={() => remove.mutate(location.id)}
                      aria-label={t('admin.deleteAria', { name: location.name_ar })}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}
    </div>
  )
}
