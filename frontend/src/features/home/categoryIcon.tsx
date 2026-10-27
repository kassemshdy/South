import {
  Cake,
  Camera,
  Car,
  Gift,
  GraduationCap,
  Hammer,
  Home,
  Laptop,
  LayoutGrid,
  Shirt,
  ShoppingBasket,
  Sparkles,
  Sprout,
  Tag,
  Utensils,
  Wrench,
  type LucideIcon,
} from 'lucide-react'

/**
 * A category's `icon` is a Lucide name chosen in the admin (`hammer`,
 * `cake`, ...). Mapped explicitly rather than looked up dynamically, so the
 * bundle carries only these icons; an unknown name shows a tag.
 */
const ICONS: Record<string, LucideIcon> = {
  cake: Cake,
  camera: Camera,
  car: Car,
  gift: Gift,
  'graduation-cap': GraduationCap,
  grid: LayoutGrid,
  hammer: Hammer,
  home: Home,
  laptop: Laptop,
  shirt: Shirt,
  'shopping-basket': ShoppingBasket,
  sparkles: Sparkles,
  sprout: Sprout,
  utensils: Utensils,
  wrench: Wrench,
}

export function CategoryIcon({ name, className }: { name: string | null | undefined; className?: string }) {
  const Icon = (name && ICONS[name]) || Tag
  return <Icon className={className} aria-hidden="true" />
}
