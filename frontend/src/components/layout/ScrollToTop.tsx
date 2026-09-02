import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Restores scroll position on navigation, which SPAs otherwise get wrong. */
export function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
  }, [pathname])

  return null
}
