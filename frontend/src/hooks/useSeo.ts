import { useEffect } from 'react'

interface SeoOptions {
  title: string
  description?: string
  image?: string | null
  canonicalPath?: string
  /** Keeps non-public pages out of search results. */
  noIndex?: boolean
}

function setMeta(selector: string, attribute: 'name' | 'property', key: string, content: string) {
  let tag = document.head.querySelector<HTMLMetaElement>(selector)
  if (!tag) {
    tag = document.createElement('meta')
    tag.setAttribute(attribute, key)
    document.head.appendChild(tag)
  }
  tag.setAttribute('content', content)
}

/**
 * Client-side document metadata.
 *
 * In production the backend also injects these tags into index.html before it
 * is served, so crawlers and WhatsApp link previews — which do not run
 * JavaScript — see the right values. This hook keeps the tags correct during
 * in-app navigation.
 */
export function useSeo({ title, description, image, canonicalPath, noIndex }: SeoOptions): void {
  useEffect(() => {
    document.title = title
    setMeta('meta[property="og:title"]', 'property', 'og:title', title)

    if (description) {
      setMeta('meta[name="description"]', 'name', 'description', description)
      setMeta('meta[property="og:description"]', 'property', 'og:description', description)
    }

    if (image) {
      setMeta('meta[property="og:image"]', 'property', 'og:image', new URL(image, window.location.origin).toString())
    }

    const url = new URL(canonicalPath ?? window.location.pathname, window.location.origin).toString()
    setMeta('meta[property="og:url"]', 'property', 'og:url', url)

    let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.rel = 'canonical'
      document.head.appendChild(canonical)
    }
    canonical.href = url

    const robots = document.head.querySelector<HTMLMetaElement>('meta[name="robots"]')
    if (noIndex) {
      setMeta('meta[name="robots"]', 'name', 'robots', 'noindex, nofollow')
    } else if (robots) {
      robots.remove()
    }
  }, [title, description, image, canonicalPath, noIndex])
}
