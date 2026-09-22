import { useEffect } from 'react'

/**
 * Put the top of the page back in view when an in-page step changes.
 *
 * `ScrollToTop` handles navigation, but it keys off the pathname — and the
 * steps inside `/offer` and `/browse` are state, not routes. Pressing a door
 * swaps a long page for a short panel while the scroll position stays where
 * the door was, which put the notice's own heading 458 pixels above the
 * viewport: the visitor pressed a card and, as far as they could see,
 * nothing happened.
 *
 * Instant rather than smooth. A smooth scroll from the foot of a long page
 * animates through everything between, which reads as the page moving on its
 * own; this is the same reset a real navigation does, and a navigation does
 * not animate.
 */
export function useScrollToStep(step: string): void {
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
  }, [step])
}
