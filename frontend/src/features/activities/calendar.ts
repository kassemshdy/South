import type { Activity } from '@/types/api'

/** An activity with no end is put in a calendar as two hours long. */
const DEFAULT_LENGTH_MS = 2 * 60 * 60 * 1000

/** `20261105T160000Z`: the UTC form both Google Calendar and iCalendar read. */
function utcStamp(date: Date): string {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
}

function span(activity: Activity): { start: Date; end: Date } | null {
  if (!activity.starts_at) return null
  const start = new Date(activity.starts_at)
  const end = activity.ends_at
    ? new Date(activity.ends_at)
    : new Date(start.getTime() + DEFAULT_LENGTH_MS)
  return { start, end }
}

/** Google Calendar's own "add event" page, filled in; nothing is sent until the visitor saves it. */
export function googleCalendarHref(activity: Activity, pageUrl: string): string | null {
  const when = span(activity)
  if (!when) return null
  const details = [activity.summary, pageUrl].filter(Boolean).join('\n\n')
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: activity.title,
    dates: `${utcStamp(when.start)}/${utcStamp(when.end)}`,
    details,
  })
  if (activity.location) params.set('location', activity.location)
  return `https://calendar.google.com/calendar/render?${params.toString()}`
}

/** RFC 5545 text: backslash, semicolon, comma and newline escaped. */
function icsText(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n')
}

/**
 * The activity as an `.ics` file, built in the browser: Apple Calendar,
 * Outlook and most phones open it straight into their own calendar.
 */
export function icsFile(activity: Activity, pageUrl: string): Blob | null {
  const when = span(activity)
  if (!when) return null
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Janoubona//Activities//EN',
    'CALSCALE:GREGORIAN',
    'BEGIN:VEVENT',
    `UID:${activity.id}@janoubona`,
    `DTSTAMP:${utcStamp(new Date())}`,
    `DTSTART:${utcStamp(when.start)}`,
    `DTEND:${utcStamp(when.end)}`,
    `SUMMARY:${icsText(activity.title)}`,
    `DESCRIPTION:${icsText([activity.summary, pageUrl].filter(Boolean).join('\n\n'))}`,
    `URL:${pageUrl}`,
    ...(activity.location ? [`LOCATION:${icsText(activity.location)}`] : []),
    'END:VEVENT',
    'END:VCALENDAR',
  ]
  return new Blob([lines.join('\r\n') + '\r\n'], { type: 'text/calendar;charset=utf-8' })
}

/** Hands the `.ics` file to the browser as a download. */
export function downloadIcs(activity: Activity, pageUrl: string): void {
  const blob = icsFile(activity, pageUrl)
  if (!blob) return
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = `${activity.slug}.ics`
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(href), 1000)
}
