import {
  Armchair,
  Axe,
  Baby,
  BookOpen,
  BrickWall,
  Cherry,
  CookingPot,
  Flame,
  Frame,
  Gem,
  Hexagon,
  Moon,
  Palette,
  Scissors,
  Smartphone,
  SprayCan,
  Sun,
  Truck,
  Wifi,
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
  'armchair': Armchair,
  'axe': Axe,
  'baby': Baby,
  'book-open': BookOpen,
  'brick-wall': BrickWall,
  'cherry': Cherry,
  'cooking-pot': CookingPot,
  'flame': Flame,
  'frame': Frame,
  'gem': Gem,
  'hexagon': Hexagon,
  'moon': Moon,
  'palette': Palette,
  'scissors': Scissors,
  'smartphone': Smartphone,
  'spray-can': SprayCan,
  'sun': Sun,
  'truck': Truck,
  'wifi': Wifi,
}

/** Every icon an administrator may pick, in the order the picker lists them. */
export const CATEGORY_ICON_NAMES = Object.keys(ICONS).sort()

export function CategoryIcon({ name, className }: { name: string | null | undefined; className?: string }) {
  const Icon = (name && ICONS[name]) || Tag
  return <Icon className={className} aria-hidden="true" />
}
