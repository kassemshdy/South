import { CardImage } from '@/components/ui/CardImage'
import { cn } from '@/utils/cn'

/** Background and text pairs from the site's own palette. */
const TONES = [
  'bg-brand-100 text-brand-800',
  'bg-sea-100 text-sea-700',
  'bg-wheat-100 text-wheat-700',
  'bg-clay-100 text-clay-700',
  'bg-olive-100 text-olive-800',
  'bg-sand-200 text-ink-700',
] as const

/** The first letter of the first and the last word. */
export function initialsOf(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (words.length === 0) return '?'
  const first = Array.from(words[0] ?? '')[0] ?? ''
  const last = words.length > 1 ? (Array.from(words[words.length - 1] ?? '')[0] ?? '') : ''
  return `${first}${last}`.toUpperCase()
}

/** The same colour for the same name, on every page and every visit. */
function toneOf(name: string): string {
  let hash = 0
  for (const char of name) hash = (hash * 31 + (char.codePointAt(0) ?? 0)) >>> 0
  return TONES[hash % TONES.length] ?? TONES[0]
}

/**
 * A candidate's photo, or their initials in a colour when there is none or
 * they chose to hide it (the API then sends no photo at all). Never the grey
 * silhouette, which made every card in the list look the same.
 */
export function CandidateAvatar({
  name,
  photoUrl,
  thumbUrl,
  className,
  textClassName = 'text-xl',
}: {
  name: string
  photoUrl: string | null | undefined
  thumbUrl?: string | null | undefined
  className?: string
  textClassName?: string
}) {
  return (
    <div className={cn('shrink-0 overflow-hidden rounded-full', className)}>
      {photoUrl ? (
        <CardImage
          src={photoUrl}
          thumbSrc={thumbUrl ?? undefined}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover"
        />
      ) : (
        <div
          className={cn(
            'flex h-full w-full items-center justify-center font-bold',
            toneOf(name),
            textClassName,
          )}
          aria-hidden="true"
        >
          <bdi>{initialsOf(name)}</bdi>
        </div>
      )}
    </div>
  )
}
