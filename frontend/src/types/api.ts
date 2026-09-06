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

export interface TalentSkill {
  id: string
  name_ar: string
  slug: string
  icon: string | null
  sort_order: number
  is_active: boolean
  talent_count: number
}

export interface TalentImage {
  id: string
  url: string
  kind: ImageKind
  caption: string | null
  sort_order: number
  width: number | null
  height: number | null
}

export interface TalentSummary {
  id: string
  display_name: string
  slug: string
  headline: string | null
  photo_url: string | null
  phone: string | null
  whatsapp: string | null
  years_experience: number | null
  skill: TalentSkill | null
  /** The person's own words, shown instead of the literal "Other" skill name. */
  custom_skill_text: string | null
  location: LocationNode | null
  created_at: string
}

export interface TalentDetail extends TalentSummary {
  bio: string | null
  email: string | null
  website: string | null
  images: TalentImage[]
  approved_at: string | null
}

/** The person's own view of their profile, including moderation state. */
export interface OwnerTalent extends TalentDetail {
  status: BusinessStatus
  rejection_reason: string | null
  submitted_at: string | null
  updated_at: string
}

/** Adds account details that only administrators may see. */
export interface AdminTalent extends OwnerTalent {
  owner_id: string
  owner_phone: string | null
  owner_personal_phone: string | null
  owner_has_verification_document: boolean
  owner_display_name: string | null
  moderation_actions: ModerationAction[]
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
  total_talents: number
  pending_talents: number
  approved_talents: number
}

/** The homepage stats strip — approved-only, safe for an anonymous visitor. */
export interface PublicStats {
  total_businesses: number
  total_towns: number
  total_talents: number
}

export type FeedbackStatus = 'BACKLOG' | 'TODO' | 'IN_PROGRESS' | 'DONE'

export type FeedbackPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'

export type FeedbackAttachmentKind = 'SCREENSHOT' | 'PHOTO' | 'DOCUMENT'

export interface FeedbackUser {
  id: string
  display_name: string | null
  email: string | null
}

export interface FeedbackAttachment {
  id: string
  kind: FeedbackAttachmentKind
  content_type: string
  original_filename: string | null
  size_bytes: number | null
  created_at: string
}

export interface FeedbackComment {
  id: string
  body: string
  author_id: string | null
  author_display_name: string | null
  created_at: string
}

export interface FeedbackTicketSummary {
  id: string
  title: string
  status: FeedbackStatus
  priority: FeedbackPriority
  sort_order: number
  reporter: FeedbackUser
  assignee: FeedbackUser | null
  attachment_count: number
  comment_count: number
  created_at: string
  updated_at: string
}

export interface FeedbackTicketDetail extends FeedbackTicketSummary {
  description: string | null
  page_path: string | null
  client_context: string | null
  resolved_at: string | null
  attachments: FeedbackAttachment[]
  comments: FeedbackComment[]
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

export interface TalentQuery {
  q?: string
  skill?: string
  location?: string
  sort?: SortOption
  page?: number
  page_size?: number
}

/** Just enough of the parent business for a product card/page to link back. */
export interface ProductBusinessRef {
  name: string
  slug: string
  phone: string | null
  whatsapp: string | null
  category: Category | null
  location: LocationNode | null
}

export interface ProductSummary {
  id: string
  slug: string
  title: string
  price: string | null
  currency: Currency
  image_url: string | null
  business: ProductBusinessRef
}

export interface ProductDetail extends ProductSummary {
  description: string | null
  created_at: string
}
