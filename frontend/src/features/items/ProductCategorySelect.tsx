import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useCategories } from '@/hooks/useTaxonomy'

/**
 * A product's own category (the owners' ticket, 16 Nov 2026). It starts
 * from the shop's; picking the shop's again means "follow the shop", which
 * the API stores as no category of its own.
 */
export function ProductCategorySelect({
  value,
  onChange,
  labelledBy,
  id,
  disabled,
}: {
  value: string
  onChange: (categoryId: string) => void
  labelledBy?: string
  id?: string
  disabled?: boolean
}) {
  const { data } = useCategories()
  const categories = (data ?? []).filter((category) => category.is_active || category.id === value)
  return (
    <Select value={value || undefined} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger id={id} aria-labelledby={labelledBy}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {categories.map((category) => (
          <SelectItem key={category.id} value={category.id}>
            {category.name_ar}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
