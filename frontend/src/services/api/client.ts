/**
 * The single HTTP client.
 *
 * Everything the app sends goes through here so that auth headers, the error
 * envelope and network-failure handling exist in exactly one place.
 */

import { DEFAULT_LOCALE, translate } from '@/i18n'
import type { ApiErrorPayload } from '@/types/api'

const TOKEN_STORAGE_KEY = 'south.auth.token'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: { field: string; message: string }[]
  readonly missing: string[]
  readonly retryAfterSeconds: number | null

  constructor(status: number, payload: ApiErrorPayload | null, fallback: string) {
    super(payload?.error?.message ?? fallback)
    this.name = 'ApiError'
    this.status = status
    this.code = payload?.error?.code ?? 'unknown_error'
    this.fields = payload?.error?.details?.fields ?? []
    this.missing = payload?.error?.details?.missing ?? []
    this.retryAfterSeconds = payload?.error?.details?.retry_after_seconds ?? null
  }

  /** True when the request never reached the server. */
  get isNetworkError(): boolean {
    return this.status === 0
  }

  get isUnauthorized(): boolean {
    return this.status === 401
  }
}

export const tokenStorage = {
  get(): string | null {
    try {
      return window.localStorage.getItem(TOKEN_STORAGE_KEY)
    } catch {
      // Private browsing modes can throw on storage access.
      return null
    }
  },
  set(token: string): void {
    try {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } catch {
      /* non-fatal: the session simply will not survive a reload */
    }
  },
  clear(): void {
    try {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY)
    } catch {
      /* ignore */
    }
  },
}

type Query = Record<string, string | number | boolean | undefined | null>

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Query
  formData?: FormData
  signal?: AbortSignal
}

function buildUrl(path: string, query?: Query): string {
  const url = new URL(path, window.location.origin)
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    }
  }
  return url.pathname + url.search
}

/** Raised so callers can react to an expired or revoked session. */
export const UNAUTHORIZED_EVENT = 'south:unauthorized'

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, formData, signal } = options

  const headers: Record<string, string> = {}
  const token = tokenStorage.get()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal,
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError(0, null, translate(DEFAULT_LOCALE, 'api.networkError'))
  }

  if (response.status === 204) return undefined as T

  const isJson = response.headers.get('content-type')?.includes('application/json')
  const payload: unknown = isJson ? await response.json() : await response.text()

  if (!response.ok) {
    const error = new ApiError(
      response.status,
      isJson ? (payload as ApiErrorPayload) : null,
      translate(DEFAULT_LOCALE, 'api.unexpectedError'),
    )
    if (error.isUnauthorized) {
      tokenStorage.clear()
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
    }
    throw error
  }

  return payload as T
}

/**
 * For endpoints that return a file body rather than JSON (e.g. the admin
 * verification-document download) — `apiRequest` always decodes as
 * JSON/text, which would corrupt binary content.
 */
export async function apiDownload(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const headers: Record<string, string> = {}
  const token = tokenStorage.get()
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(buildUrl(path), { headers })
  } catch {
    throw new ApiError(0, null, translate(DEFAULT_LOCALE, 'api.networkError'))
  }

  if (!response.ok) {
    const isJson = response.headers.get('content-type')?.includes('application/json')
    const payload = isJson ? ((await response.json()) as ApiErrorPayload) : null
    const error = new ApiError(response.status, payload, translate(DEFAULT_LOCALE, 'api.unexpectedError'))
    if (error.isUnauthorized) {
      tokenStorage.clear()
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
    }
    throw error
  }

  const disposition = response.headers.get('content-disposition')
  const match = disposition?.match(/filename="?([^"]+)"?/)
  return { blob: await response.blob(), filename: match?.[1] ?? null }
}
