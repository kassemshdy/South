import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Users } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi, taxonomyApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'

/**
 * Move a shop that really offers a service into a services profile, the
 * other direction of ConvertToShopCard (the owners' review, 12 Nov 2026).
 * Its products become priced services with their photos.
 */
export function ConvertToServicesCard({ businessId }: { businessId: string }) {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const skills = useQuery({ queryKey: queryKeys.talentSkills, queryFn: taxonomyApi.talentSkills })
  const [skillId, setSkillId] = useState('')

  const convert = useMutation({
    mutationFn: () => adminApi.convertBusinessToTalent(businessId, skillId),
    onSuccess: ({ profile_id }) => {
      void queryClient.invalidateQueries({ queryKey: ['admin'] })
      toast.success(t('admin.correctionSaved'))
      navigate(`/admin/talent/${profile_id}`)
    },
    onError: (error) =>
      toast.error(t('admin.correctionFailed'), error instanceof ApiError ? error.message : undefined),
  })

  return (
    <Card>
      <CardHeader>
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <Users className="size-5 text-brand-700" aria-hidden />
          {t('admin.convertToServicesTitle')}
        </h2>
      </CardHeader>
      <CardBody className="space-y-3">
        <p className="text-sm text-ink-500">{t('admin.convertToServicesHint')}</p>
        <label className="block text-sm font-semibold" htmlFor="admin-convert-skill">
          {t('admin.convertToServicesSkill')}
        </label>
        <Select value={skillId || undefined} onValueChange={setSkillId}>
          <SelectTrigger id="admin-convert-skill">
            <SelectValue placeholder={t('admin.convertToServicesSkill')} />
          </SelectTrigger>
          <SelectContent>
            {skills.data?.map((skill) => (
              <SelectItem key={skill.id} value={skill.id}>
                {skill.name_ar}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="sm"
          disabled={!skillId}
          loading={convert.isPending}
          onClick={() => {
            if (window.confirm(t('admin.convertToServicesConfirm'))) convert.mutate()
          }}
        >
          {t('admin.convertToServicesButton')}
        </Button>
      </CardBody>
    </Card>
  )
}
