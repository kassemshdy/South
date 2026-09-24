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

export type Gender = 'MALE' | 'FEMALE'
export type MaritalStatus = 'SINGLE' | 'MARRIED' | 'DIVORCED' | 'WIDOWED'

/**
 * How the person listing a business stands to the establishment itself —
 * owner, manager, or an employee listing on the business's behalf. A
 * reviewer's question, not a shopper's: present on `OwnerBusiness` and
 * `AdminBusiness`, never on the public `BusinessDetail`.
 */
export type OwnerRelation = 'OWNER' | 'MANAGER' | 'WORKER'

/**
 * Made in the South, or imported and sold by a southern store. One mark per
 * business, set by the door its owner came through, and public: it is what
 * the two goods doors on `/browse` filter on.
 */
export type GoodsOrigin = 'LOCAL' | 'IMPORTED'

/**
 * The account holder's identity.
 *
 * Belongs to the person, not to any one listing — one account holds a single
 * copy, shared by its talent profile and every business it owns. Never part
 * of a public payload: the account reads its own through `User`, an admin
 * reads it through `owner_identity` on a review payload.
 */
export interface OwnerIdentity {
  full_name: string | null
  birth_year: number | null
  gender: Gender | null
  marital_status: MaritalStatus | null
  registration_place: string | null
  residence_place: string | null
  /**
   * The account holder's own photo — a face, not a logo, and admin-only for
   * the same reason as every field beside it. It is in this block rather than
   * on a listing because one account owns one face however many shops it has.
   */
  photo_url: string | null
}

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

export interface User extends OwnerIdentity {
  id: string
  phone_number: string | null
  email: string | null
  display_name: string | null
  /** A second, private contact number used only for identity verification. */
  personal_phone_number: string | null
  role: UserRole
  /**
   * Set when an administrator issued the password this session was opened
   * with. While it is true the API answers 403 `password_change_required` on
   * every owner route, so the app has nowhere to send the person but the
   * change-password screen.
   */
  must_change_password: boolean
  created_at: string
}

/**
 * A password an administrator generated, returned by the API exactly once.
 *
 * There is no route that reads it back: it is stored only as a hash, so
 * closing the panel that shows it means issuing a new one. It is never put in
 * component state that outlives the panel, never persisted, and never sent
 * anywhere by this app — the administrator relays it from their own WhatsApp.
 */
export interface IssuedPassword {
  phone_number: string
  password: string
}

/** Metadata only — the document bytes are never exposed by a URL. */
export interface VerificationDocument {
  id: string
  content_type: string
  original_filename: string | null
  size_bytes: number | null
  created_at: string
}

/**
 * One of a listing's official papers -- commercial register, licence, permit.
 * Metadata only: there is no url, because the bytes are reachable through the
 * admin-gated download route and nowhere else.
 */
export interface BusinessDocument {
  id: string
  content_type: string
  original_filename: string | null
  /** The owner's own words for what the paper is. */
  label: string | null
  size_bytes: number | null
  created_at: string
}

export interface AuthToken {
  access_token: string
  token_type: string
  expires_at: string
  user: User
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

export interface ItemImage {
  id: string
  url: string
  caption: string | null
  sort_order: number
  width: number | null
  height: number | null
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
  /** The fields below only ever apply to a physical good, not a service or menu item. */
  good_type: string | null
  brand_name: string | null
  ingredients: string | null
  /** ISO date (YYYY-MM-DD). */
  manufactured_at: string | null
  /** ISO date (YYYY-MM-DD). */
  expiry_date: string | null
  net_weight: string | null
  external_link: string | null
  /** Per product: a shop selling both has each good under its own door. */
  goods_origin: GoodsOrigin
  /** Separate from image_url, which is the card thumbnail. */
  images: ItemImage[]
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
  goods_origin: GoodsOrigin
  created_at: string
}

export interface BusinessDetail extends BusinessSummary {
  description: string | null
  /** Producer detail — published, unlike the owner's own identity. */
  institution_name: string | null
  /** ISO date (YYYY-MM-DD): founded, or started producing. */
  founding_date: string | null
  production_nature: string | null
  /** Years in this trade -- not the establishment's age; see founding_date. */
  years_of_experience: number | null
  email: string | null
  website: string | null
  /**
   * The owner's introduction video, as a YouTube id — never a URL. The page
   * composes the embed address from it, so nothing an owner typed is handed
   * to a browser.
   */
  youtube_video_id: string | null
  address_text: string | null
  latitude: number | null
  longitude: number | null
  maps_url: string | null
  images: BusinessImage[]
  social_links: SocialLink[]
  items: BusinessItem[]
  /** Approved only. The API never sends a pending or hidden one here. */
  testimonials: Testimonial[]
  approved_at: string | null
}

/** The owner's own view of a listing, including moderation state. */
export interface OwnerBusiness extends BusinessDetail {
  /** Never on BusinessDetail -- a reviewer's question, not a public one. */
  owner_relation: OwnerRelation | null
  status: BusinessStatus
  rejection_reason: string | null
  submitted_at: string | null
  updated_at: string
  /** Optional, and absent from every public payload. */
  documents: BusinessDocument[]
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
  /** Null when the owner has filled in nothing — distinct from all-null. */
  owner_identity: OwnerIdentity | null
  owner_has_verification_document: boolean
  owner_has_verification_document_back: boolean
  owner_has_cv_document: boolean
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
  identity: OwnerIdentity | null
}

/** The account's row, plus everything it owns — every business, in any
 * status, and its talent profile if it has one. */
export interface AdminUserDetail extends AdminUser {
  businesses: AdminBusiness[]
  talent_profile: AdminTalent | null
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
  photo_url: string | null
  phone: string | null
  whatsapp: string | null
  years_experience: number | null
  skill: TalentSkill | null
  /** The person's own words, shown instead of the literal "Other" skill name. */
  custom_skill_text: string | null
  /** The trade in their own words, one level below the taxonomy skill. */
  skill_specialty: string | null
  location: LocationNode | null
  created_at: string
}

export type LanguageProficiency = 'BASIC' | 'GOOD' | 'FLUENT' | 'NATIVE'
export type EmploymentType = 'FULL_TIME' | 'PART_TIME'

export interface TalentLanguage {
  id: string
  name: string
  proficiency: LanguageProficiency
  sort_order: number
}

export type ContactChannel = 'PHONE' | 'WHATSAPP' | 'EMAIL' | 'WEBSITE'

export interface TalentDetail extends TalentSummary {
  bio: string | null
  /** Which contact detail the page leads with. Never narrows what is shown. */
  preferred_contact: ContactChannel | null
  email: string | null
  website: string | null
  /**
   * The owner's introduction video, as a YouTube id — never a URL. The page
   * composes the embed address from it, so nothing an owner typed is handed
   * to a browser.
   */
  youtube_video_id: string | null
  /** Professional detail — published on the public profile. */
  highest_degree: string | null
  specialization: string | null
  university: string | null
  /** Years spent earning that degree/training, not years worked. */
  education_years: number | null
  /** ISO date (YYYY-MM-DD). */
  graduation_date: string | null
  study_focus: string | null
  experience: string | null
  professional_training: string | null
  skills_text: string | null
  services_offered: string | null
  hobbies: string | null
  employment_type: EmploymentType | null
  remote_capable: boolean
  languages: TalentLanguage[]
  /** Optional, published: the person's own accounts. */
  social_links: SocialLink[]
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
  owner_identity: OwnerIdentity | null
  owner_has_verification_document: boolean
  owner_has_verification_document_back: boolean
  owner_has_cv_document: boolean
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

/**
 * The homepage stats strip — approved-only, safe for an anonymous visitor.
 *
 * The three directories, in the order the browse strip lists them. It used to
 * count towns instead of products, which measured the map rather than the
 * directory.
 */
export interface PublicStats {
  total_businesses: number
  total_products: number
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
  /** The roadmap issue serving this ticket, when one does. A number, not a
   *  URL: GitHub owns the issue, the board only records which one. */
  github_issue_number: number | null
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

/**
 * The products directory sorts by price as well, which the other two cannot:
 * a business and a talent profile have no price to sort on.
 *
 * There is no matching *filter*. A price range has to name a currency to
 * mean anything — this directory lists in dollars and in lira and holds no
 * exchange rate — and it has to decide what becomes of the products whose
 * owner named no price. An ordering asks neither question: nothing is
 * removed, and an unpriced product sorts last in both directions.
 */
export type ProductSortOption = SortOption | 'price_asc' | 'price_desc'

export interface BusinessQuery {
  q?: string
  category?: string
  location?: string
  origin?: GoodsOrigin
  sort?: SortOption
  page?: number
  page_size?: number
}

/** Same as a business search, but its `sort` can also order by price. */
export interface ProductQuery extends Omit<BusinessQuery, 'sort'> {
  sort?: ProductSortOption
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
  goods_origin: GoodsOrigin
  business: ProductBusinessRef
}

export interface ProductDetail extends ProductSummary {
  description: string | null
  created_at: string
  good_type: string | null
  brand_name: string | null
  ingredients: string | null
  manufactured_at: string | null
  expiry_date: string | null
  net_weight: string | null
  external_link: string | null
  images: ItemImage[]
}

/**
 * How often a listing was looked at.
 *
 * `series` is one integer per day of the window, oldest first, zeroes
 * included — a sparkline drawn from only the busy days shows a busier
 * listing than the one that exists.
 */
export interface ListingViews {
  subject_type: 'BUSINESS' | 'TALENT' | 'PRODUCT'
  subject_id: string
  views_recent: number
  views_window: number
  series: number[]
  series_start: string
}

export interface OwnerViews {
  /** Returned rather than assumed, so the wording and the span cannot drift. */
  window_days: number
  recent_days: number
  listings: ListingViews[]
}

export type TestimonialStatus =
  | 'PENDING_REVIEW'
  | 'PENDING_OWNER'
  | 'APPROVED'
  | 'HIDDEN'
  | 'REJECTED'

/**
 * Owner-selected praise, never a review — the owner decides what appears, so
 * a testimonial is not independent evidence and no surface may imply it is.
 */
export interface Testimonial {
  id: string
  author_name: string
  body: string
  created_at: string
}

export interface OwnerTestimonial extends Testimonial {
  status: TestimonialStatus
  approved_at: string | null
}

/**
 * The platform's view: the owner's moderation fields plus which listing the
 * testimonial is on, so an admin can survey every submission in one place.
 * Carries only the business's public identity, never the owner's.
 */
export interface AdminTestimonial extends OwnerTestimonial {
  business_id: string
  business_name: string
  business_slug: string
}

export type ArticleSection = 'BLOG' | 'NEWS'

/**
 * Admin-authored content behind the `/blog` and `/news` pages. Nothing here
 * is owner- or visitor-submitted, so a public payload carries no moderation
 * state — only what a published article actually is.
 */
export interface Article {
  id: string
  section: ArticleSection
  slug: string
  title: string
  body: string
  cover_url: string | null
  published_at: string | null
}

export interface AdminArticle extends Article {
  is_published: boolean
  created_at: string
  updated_at: string
}

export type OrderStatus = 'NEW' | 'CONTACTED' | 'DONE'

/** A line as it was when the order was placed, not as the product is now. */
export interface OrderLine {
  title: string
  price: string | null
  currency: Currency
  quantity: number
}

/**
 * An order request. Only ever the owner's — a customer's name and phone
 * reach the owner who has to reply and nobody else, so there is no public
 * and no admin counterpart to this type.
 */
export interface Order {
  id: string
  customer_name: string
  customer_phone: string
  note: string | null
  status: OrderStatus
  lines: OrderLine[]
  created_at: string
  updated_at: string
}

/**
 * A request for a piece of work, sent to a talent profile.
 *
 * The counterpart to an `Order`, and only ever the provider's for the same
 * reason: it carries a stranger's name and phone number, so there is no
 * public and no admin counterpart to this type. It shares `OrderStatus`
 * because new/contacted/done is the same three-step the same person works
 * through.
 *
 * `details` is required where an order's `note` is optional — an order has
 * line items that say what is wanted, and this has nothing else.
 */
export interface ServiceRequest {
  id: string
  customer_name: string
  customer_phone: string
  details: string
  status: OrderStatus
  created_at: string
  updated_at: string
}

/**
 * An application set aside because its phone number already had an account.
 * Administrator-only: `payload` carries the applicant's identity as typed.
 */
export interface DiscardedApplication {
  id: string
  kind: 'BUSINESS' | 'TALENT'
  login_phone: string
  existing_user_id: string | null
  payload: {
    identity?: { full_name?: string | null } | null
    business?: { name?: string | null; short_description?: string | null; description?: string | null } | null
    talent?: { display_name?: string | null; bio?: string | null } | null
  }
  created_at: string
  dismissed_at: string | null
}
