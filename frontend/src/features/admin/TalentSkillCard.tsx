import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useToast } from '@/components/ui/Toast'
import { useT } from '@/i18n'
import { ApiError } from '@/services/api/client'
import { adminApi, taxonomyApi } from '@/services/api/endpoints'
import { queryKeys } from '@/services/api/queryKeys'
import type { AdminTalent } from '@/types/api'

/**
 * The skill a service profile is filed under, corrected by an administrator
 * when the applicant picked the wrong one. "Other" keeps its own words, as
 * on the owner's form.
 */
export function TalentSkillCard({ profile }: { profile: AdminTalent }) {
  const t = useT()
  const toast = useToast()
  const queryClient = useQueryClient()
  const skills = useQuery({ queryKey: queryKeys.talentSkills, queryFn: taxonomyApi.talentSkills })
  const [skillId, setSkillId] = useState(profile.skill?.id ?? '')
  const [custom, setCustom] = useState(profile.custom_skill_text ?? '')

  const chosen = skills.data?.find((skill) => skill.id === skillId)
  const isOther = chosen?.slug === 'other'
  const unchanged =
    skillId === (profile.skill?.id ?? '') && custom === (profile.custom_skill_text ?? '')

  const save = useMutation({
    mutationFn: () =>
      adminApi.setTalentSkill(profile.id, skillId, isOther ? custom.trim() || null : null),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminTalent(profile.id) })
      toast.success(t('admin.correctionSaved'))
    },
    onError: (error) =>
      toast.error(t('admin.correctionFailed'), error instanceof ApiError ? error.message : undefined),
  })

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-bold">{t('admin.correctionsTitle')}</h2>
      </CardHeader>
      <CardBody className="space-y-3">
        <label className="block text-sm font-semibold" htmlFor="admin-talent-skill">
          {t('talent.field.skill')}
        </label>
        <Select value={skillId || undefined} onValueChange={setSkillId}>
          <SelectTrigger id="admin-talent-skill">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {skills.data?.map((skill) => (
              <SelectItem key={skill.id} value={skill.id}>
                {skill.name_ar}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isOther ? (
          <Input
            aria-label={t('talent.field.custom_skill')}
            placeholder={t('talent.field.custom_skill')}
            value={custom}
            maxLength={120}
            onChange={(event) => setCustom(event.target.value)}
          />
        ) : null}
        <Button
          size="sm"
          onClick={() => save.mutate()}
          loading={save.isPending}
          disabled={!skillId || unchanged || (isOther && !custom.trim())}
        >
          {t('common.save')}
        </Button>
      </CardBody>
    </Card>
  )
}
