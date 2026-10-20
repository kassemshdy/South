/**
 * Bring the first error on a form into view, and focus the control it is about.
 *
 * The registration pages are several screens tall on a phone, with the send
 * button at the very bottom and the login phone, identity, ID scans and
 * consent at the top. A tap on send that fails validation used to put red
 * text in a card three screens up and leave the page where it was, which read
 * to applicants as a button that does nothing.
 *
 * Every error here is rendered with `role="alert"` (see `Field`), and the
 * control it describes points back at it through `aria-describedby`, so the
 * first alert in document order is the topmost thing to fix and its control
 * is found without each field having to register itself. A control that
 * cannot take focus (a radio fieldset) is simply scrolled to.
 */
export function revealFirstError(root: HTMLElement | null): void {
  const alert = root?.querySelector<HTMLElement>('[role="alert"]')
  if (!root || !alert) return

  alert.scrollIntoView({ block: 'center', behavior: 'smooth' })
  const control = alert.id
    ? root.querySelector<HTMLElement>(`[aria-describedby~="${CSS.escape(alert.id)}"]`)
    : null
  control?.focus({ preventScroll: true })
}
