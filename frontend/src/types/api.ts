/**
 * API contract types.
 *
 * These mirror the Pydantic schemas in `backend/app/schemas`. Keeping them in
 * one module means components never hand-roll response shapes, and a backend
 * change surfaces as a type error in exactly one place.
 */

export type BusinessStatus =
  | 'DRAFT'
  | 'PENDING_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUSPENDED'

export type UserRole = 'OWNER' | 'ADMIN'

export type SocialPlatform =
  | 'INSTAGRAM'
  | 'FACEBOOK'
  | 'TIKTOK'
  | 'YOUTUBE'
  | 'WHATSAPP'
  | 'WEBSITE'

export type Currency = 'USD' | 'LBP'

export type ImageKind = 'LOGO' | 'COVER' | 'GALLERY' | 'ITEM'

export type LocationType = 'GOVERNORATE' | 'DISTRICT' | 'TOWN'

export type ModerationActionType =
  | 'SUBMIT'
  | 'APPROVE'
  | 'REJECT'
  | 'SUSPEND'
  | 'REACTIVATE'

export interface User {
  id: string
  phone_number: string | null
  email: string | null
  display_name: string | null
  /** A second, private contact number used only for identity verification. */
  personal_phone_number: string | null
  role: UserRole
  created_at: string
}

/** Metadata only — the document bytes are never exposed by a URL. */
export interface VerificationDocument {
  id: string
  content_type: string
  original_filename: string | null
  size_bytes: number | null
  created_at: string
}

export interface AuthToken {
  access_token: string
  token_type: string
  expires_at: string
  user: User
}

export interface RequestOtpResponse {
  message: string
  expires_in_seconds: number
  /** Present only when the backend runs in development mode. */
  debug_code: string | null
}

export interface Category {
  id: string
  name_ar: string
  slug: string
  icon: string | null
  sort_order: number
  is_active: boolean
  business_count: number
}

export interface LocationNode {
  id: string
  name_ar: string
  slug: string
  type: LocationType
  parent_id: string | null
  sort_order: number
  is_active: boolean
  business_count: number
}

export interface BusinessImage {
  id: string
  url: string
  kind: ImageKind
  caption: string | null
  sort_order: number
  width: number | null
  height: number | null
}

export interface SocialLink {
  platform: SocialPlatform
  url: string
}

export interface BusinessItem {
  id: string
  title: string
  description: string | null
  /** Decimal serialized as a string to avoid float rounding on prices. */
  price: string | null
  currency: Currency
  image_url: string | null
  is_available: boolean
  sort_order: number
}

export interface BusinessSummary {
  id: string
  name: string
  slug: string
  short_description: string | null
  logo_url: string | null
  cover_url: string | null
  phone: string | null
  whatsapp: string | null
  category: Category | null
  /** The owner's own words, shown instead of the literal "Other" category name. */
  custom_category_text: string | null
  location: LocationNode | null
  created_at: string
}

export interface BusinessDetail extends BusinessSummary {
  description: string | null
  email: string | null
  website: string | null
  address_text: string | null
  latitude: number | null
  longitude: number | null
  maps_url: string | null
  images: BusinessImage[]
  social_links: SocialLink[]
  items: BusinessItem[]
  approved_at: string | null
}

/** The owner's own view of a listing, including moderation state. */
export interface OwnerBusiness extends BusinessDetail {
  status: BusinessStatus
  rejection_reason: string | null
  submitted_at: string | null
  updated_at: string
}

export interface ModerationAction {
  id: string
  action: ModerationActionType
  from_status: BusinessStatus | null
  to_status: BusinessStatus
  reason: string | null
  created_at: string
}

/** Adds account details that only administrators may see. */
export interface AdminBusiness extends OwnerBusiness {
  owner_id: string
  owner_phone: string | null
  owner_personal_phone: string | null
  owner_has_verification_document: boolean
  owner_display_name: string | null
  moderation_actions: ModerationAction[]
}

export interface AdminUser {
  id: string
  phone_number: string | null
  email: string | null
  display_name: string | null
  personal_phone_number: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  business_count: number
}

export interface PageMeta {
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface Paginated<T> {
  items: T[]
  meta: PageMeta
}

export interface PlatformStats {
  total_businesses: number
  pending_businesses: number
  approved_businesses: number
  rejected_businesses: number
  suspended_businesses: number
  draft_businesses: number
  total_users: number
  total_admins: number
  total_items: number
}

export interface ApiErrorPayload {
  error: {
    code: string
    message: string
    details?: {
      fields?: { field: string; message: string }[]
      missing?: string[]
      retry_after_seconds?: number
    }
  }
}

export type SortOption = 'newest' | 'name' | 'oldest'

export interface BusinessQuery {
  q?: string
  category?: string
  location?: string
  sort?: SortOption
  page?: number
  page_size?: number
}
