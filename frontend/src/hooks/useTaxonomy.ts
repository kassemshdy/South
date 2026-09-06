import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { queryKeys } from '@/services/api/queryKeys'
import { taxonomyApi } from '@/services/api/endpoints'
import type { Category, LocationNode, TalentSkill } from '@/types/api'

/** Categories and locations change rarely, so they are cached aggressively. */
const STATIC_DATA_OPTIONS = { staleTime: 5 * 60_000, gcTime: 30 * 60_000 }

export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories,
    queryFn: taxonomyApi.categories,
    ...STATIC_DATA_OPTIONS,
  })
}

export function useLocations() {
  return useQuery({
    queryKey: queryKeys.locations,
    queryFn: taxonomyApi.locations,
    ...STATIC_DATA_OPTIONS,
  })
}

export function useTalentSkills() {
  return useQuery({
    queryKey: queryKeys.talentSkills,
    queryFn: taxonomyApi.talentSkills,
    ...STATIC_DATA_OPTIONS,
  })
}

export interface LocationGroup {
  district: LocationNode
  towns: LocationNode[]
}

/**
 * Flat location rows arranged into the district → towns shape the pickers and
 * filters need. Doing it here keeps the grouping logic out of components.
 */
export function useLocationGroups(): {
  groups: LocationGroup[]
  districts: LocationNode[]
  byId: Map<string, LocationNode>
  isLoading: boolean
} {
  const { data, isLoading } = useLocations()

  return useMemo(() => {
    const locations = data ?? []
    const byId = new Map(locations.map((location) => [location.id, location]))
    const districts = locations.filter((location) => location.type === 'DISTRICT')
    const groups = districts.map((district) => ({
      district,
      towns: locations.filter((location) => location.parent_id === district.id),
    }))
    return { groups, districts, byId, isLoading }
  }, [data, isLoading])
}

export function useCategoryMap(): Map<string, Category> {
  const { data } = useCategories()
  return useMemo(() => new Map((data ?? []).map((category) => [category.id, category])), [data])
}

export function useTalentSkillMap(): Map<string, TalentSkill> {
  const { data } = useTalentSkills()
  return useMemo(() => new Map((data ?? []).map((skill) => [skill.id, skill])), [data])
}
