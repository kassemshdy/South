import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/States'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { TalentSkill } from '@/types/api'

export function AdminTalentSkillsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')
  const t = useT()

  const skills = useQuery({ queryKey: queryKeys.adminTalentSkills, queryFn: adminApi.talentSkills })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminTalentSkills })
    void queryClient.invalidateQueries({ queryKey: queryKeys.talentSkills })
  }

  const handleError = (error: unknown, fallback: string) =>
    toast.error(fallback, error instanceof ApiError ? error.message : undefined)

  const create = useMutation({
    mutationFn: (name_ar: string) => adminApi.createTalentSkill({ name_ar }),
    onSuccess: () => {
      setNewName('')
      toast.success(t('admin.skillAdded'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.skillAddFailed')),
  })

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<TalentSkill> }) => adminApi.updateTalentSkill(id, body),
    onSuccess: () => {
      setEditingId(null)
      toast.success(t('admin.skillSaved'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.skillSaveFailed')),
  })

  const remove = useMutation({
    mutationFn: (id: string) => adminApi.deleteTalentSkill(id),
    onSuccess: () => {
      toast.success(t('admin.skillDeleted'))
      invalidate()
    },
    onError: (error) => handleError(error, t('admin.skillDeleteFailed')),
  })

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl">{t('admin.skillsHeading')}</h1>
        <p className="mt-2 text-ink-500">{t('admin.skillsSubtitle')}</p>
      </header>

      <Card>
        <CardBody>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              if (newName.trim().length >= 2) create.mutate(newName.trim())
            }}
            className="flex gap-2"
          >
            <label htmlFor="new-skill" className="sr-only">
              {t('admin.newSkillLabel')}
            </label>
            <Input
              id="new-skill"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              placeholder={t('admin.newSkillLabel')}
            />
            <Button type="submit" loading={create.isPending} disabled={newName.trim().length < 2}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t('admin.add')}
            </Button>
          </form>
        </CardBody>
      </Card>

      {skills.isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : skills.isError ? (
        <ErrorState error={skills.error} onRetry={() => void skills.refetch()} />
      ) : (
        <ul className="space-y-2">
          {skills.data?.map((skill) => (
            <li key={skill.id}>
              <Card>
                <CardBody className="flex flex-wrap items-center justify-between gap-3 p-4">
                  {editingId === skill.id ? (
                    <form
                      onSubmit={(event) => {
                        event.preventDefault()
                        update.mutate({ id: skill.id, body: { name_ar: editingName } })
                      }}
                      className="flex flex-1 gap-2"
                    >
                      <Input value={editingName} onChange={(event) => setEditingName(event.target.value)} autoFocus />
                      <Button type="submit" size="icon" loading={update.isPending} aria-label={t('admin.saveAria')}>
                        <Check className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button type="button" size="icon" variant="ghost" onClick={() => setEditingId(null)} aria-label={t('admin.cancelAria')}>
                        <X className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </form>
                  ) : (
                    <>
                      <div className="flex items-center gap-3">
                        <span className="font-semibold">{skill.name_ar}</span>
                        <span className="ltr-nums text-xs text-ink-300">{skill.slug}</span>
                        {!skill.is_active ? (
                          <Badge className="bg-ink-100 text-ink-700">
                            {t('common.inactive')}
                          </Badge>
                        ) : null}
                      </div>

                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            update.mutate({ id: skill.id, body: { is_active: !skill.is_active } })
                          }
                        >
                          {skill.is_active ? t('common.deactivate') : t('common.activate')}
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            setEditingId(skill.id)
                            setEditingName(skill.name_ar)
                          }}
                          aria-label={t('admin.editAria', { name: skill.name_ar })}
                        >
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="text-clay-600"
                          onClick={() => remove.mutate(skill.id)}
                          aria-label={t('admin.deleteAria', { name: skill.name_ar })}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                    </>
                  )}
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
