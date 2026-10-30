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

/** An administrator's staff role; see `features/admin/staffAccess.ts`. */
export type StaffRole = 'MANAGER' | 'REVIEWER' | 'SUPPORT' | 'EDITOR' | 'VIEWER'

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
  /** Currently displaced from the South: asked on the application, for the team only. */
  is_displaced: boolean | null
  /** Where a displaced account holder lived before; null for anyone else. */
  pre_displacement_place: string | null
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
  /**
   * The holder's own choice to show buyers where they were displaced from.
   * The one identity value that can become public, and only through this.
   */
  show_displacement?: boolean
  phone_number: string | null
  email: string | null
  display_name: string | null
  /** A second, private contact number used only for identity verification. */
  personal_phone_number: string | null
  role: UserRole
  /** Administrators only: what they may do in the admin area. */
  staff_role?: StaffRole | null
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
/** A short read-only session on an owner's account, for an administrator. */
export interface ViewAsToken {
  access_token: string
  expires_at: string
  user_id: string
  display_name: string | null
}

export interface IssuedPassword {
  phone_number: string
  password: string
  /** Which issue this is; the browser keeps the password while it is current. */
  version: number
}

export interface CredentialState {
  version: number
  has_password: boolean
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
  /** Products on sale in its shops, as the catalogue counts them. */
  item_count: number
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
  item_count: number
  service_count: number
  job_count: number
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
  /** The product page's address, `/product/<slug>`. */
  slug: string
  title: string
  description: string | null
  /** Decimal serialized as a string to avoid float rounding on prices. */
  price: string | null
  currency: Currency
  image_url: string | null
  /** The card-sized copy, when there is one; fall back to the full image. */
  image_thumb_url?: string | null
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
  /** The product on the shop's own Shopify store, when it has one. */
  buy_url?: string | null
}

export interface BusinessSummary {
  id: string
  name: string
  slug: string
  short_description: string | null
  logo_url: string | null
  cover_url: string | null
  /** The card-sized copy, when there is one; fall back to the full image. */
  logo_thumb_url?: string | null
  cover_thumb_url?: string | null
  phone: string | null
  whatsapp: string | null
  category: Category | null
  /** The owner's own words, shown instead of the literal "Other" category name. */
  custom_category_text: string | null
  location: LocationNode | null
  /**
   * The stars on the published testimonials -- an average of what the page
   * shows, owner-selected like the text. Null until one is rated.
   */
  rating_average: number | null
  rating_count: number
  goods_origin: GoodsOrigin
  /**
   * Where the owner was displaced from, only when they chose to show it on
   * their account page; null otherwise.
   */
  displaced_from?: string | null
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
  /** The shop's own Shopify store, where payment and delivery happen. */
  online_store_url?: string | null
}

/** The owner's own view of a listing, including moderation state. */
export interface OwnerBusiness extends BusinessDetail {
  /** Orders still marked new; filled on the owner's list of listings only. */
  new_orders: number
  /** Never on BusinessDetail -- a reviewer's question, not a public one. */
  owner_relation: OwnerRelation | null
  /** Whether visitors see the numbers; the owner always does. */
  phone_public: boolean
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

/** A member of staff, as the manager's staff page lists them. */
export interface StaffMember {
  id: string
  email: string | null
  display_name: string | null
  staff_role: StaffRole | null
  is_active: boolean
  personal_phone_number: string | null
  created_at: string
}

/** A staff password, shown exactly once. */
export interface StaffPassword {
  staff: StaffMember
  password: string
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
  service_count: number
  job_count: number
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

/**
 * Which of the two directories a talent profile is listed in: services, or
 * job applications. Chosen by the profile's owner.
 */
export type TalentKind = 'SERVICE' | 'JOB_SEEKER'
/** How a service is delivered. `BOTH` matches either filter. */
export type WorkMode = 'REMOTE' | 'ON_SITE' | 'BOTH'

export interface TalentSummary {
  id: string
  display_name: string
  slug: string
  kind: TalentKind
  photo_url: string | null
  /** The wide image across the top of the profile page. */
  cover_url?: string | null
  /** The card-sized copy, when there is one; fall back to the full image. */
  photo_thumb_url?: string | null
  phone: string | null
  whatsapp: string | null
  years_experience: number | null
  skill: TalentSkill | null
  /** The person's own words, shown instead of the literal "Other" skill name. */
  custom_skill_text: string | null
  /** The trade in their own words, one level below the taxonomy skill. */
  skill_specialty: string | null
  /** Remotely, in person or both; null on a profile from before it was asked. */
  work_mode: WorkMode | null
  /** The stars on the published testimonials; null until one is rated. */
  rating_average: number | null
  rating_count: number
  location: LocationNode | null
  /**
   * Where the owner was displaced from, only when they chose to show it on
   * their account page; null otherwise.
   */
  displaced_from?: string | null
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
  /** Published ones only; a job application never has any. */
  testimonials: Testimonial[]
  /** The owner's own pin on the map, as a business has. */
  latitude: number | null
  longitude: number | null
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
  /** Whether visitors see the numbers; the owner always does. */
  phone_public: boolean
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

/** Running totals per UTC day, oldest first (`/api/admin/stats/growth`). */
export interface GrowthTotals {
  businesses: number[]
  talents: number[]
  products: number[]
  orders: number[]
}

export interface PlatformGrowth {
  days: string[]
  totals: GrowthTotals
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
  pending_testimonials: number
  approved_talents: number
}

/**
 * The homepage stats strip — approved-only, safe for an anonymous visitor.
 *
 * The three directories, in the order the browse strip lists them. It used to
 * count towns instead of products, which measured the map rather than the
 * directory.
 */
/** The home page's sections, in the order the API knows them. */
export type HomeSectionId =
  | 'cover'
  | 'hero'
  | 'slogan'
  | 'activities'
  | 'search'
  | 'categories'
  | 'stories'
  | 'reels'
  | 'stats'
  | 'products'
  | 'top_rated_products'
  | 'top_viewed_products'
  | 'most_ordered_products'
  | 'testimonials'
  | 'workshops'
  | 'online_workshops'
  | 'category_products'
  | 'shops'
  | 'talents'
  | 'news'
  | 'blog'

export interface HomeSection {
  id: HomeSectionId
  visible: boolean
}

export interface HomeLayout {
  sections: HomeSection[]
}

export type MenuItemId =
  | 'home'
  | 'products'
  | 'services'
  | 'jobs'
  | 'vacancies'
  | 'blog'
  | 'news'
  | 'workshops'
  | 'activities'
  | 'about'
  | 'contact'

/** One entry of the site menu; a null label means the catalog's own. */
export interface MenuItem {
  id: MenuItemId
  visible: boolean
  label_ar: string | null
  label_en: string | null
}

export interface SiteMenu {
  items: MenuItem[]
}

/**
 * A YouTube Short or an Instagram post on the home page. `url` and
 * `embed_url` are rebuilt by the server from the video's id, never the
 * pasted link.
 */
export interface Reel {
  id: string
  provider: 'youtube' | 'instagram'
  url: string
  embed_url: string
  caption_ar: string | null
  caption_en: string | null
  cover_url: string | null
}

export interface AdminReel extends Reel {
  is_published: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface ReelInput {
  url: string
  caption_ar: string | null
  caption_en: string | null
  is_published: boolean
}

export type StoryStatus = 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED'

/** A photo story as its owner sees it, whatever its state. */
export interface Story {
  id: string
  image_url: string
  caption: string | null
  status: StoryStatus
  approved_at: string | null
  /** A day after approval; null until approved. */
  expires_at: string | null
  created_at: string
}

/** A story in the review queue, with the listing it belongs to. */
export interface AdminStory extends Story {
  listing_kind: 'business' | 'talent'
  listing_id: string
  listing_name: string
  listing_slug: string
}

/** One circle of the home page's stories row: a listing and its photos. */
export interface StoryGroup {
  kind: 'business' | 'talent'
  slug: string
  name: string
  image_url: string | null
  stories: { id: string; image_url: string; caption: string | null; approved_at: string }[]
}

/** One suggestion under the search box while someone types. */
export interface SearchSuggestion {
  kind: 'category' | 'product' | 'shop' | 'service'
  label: string
  slug: string
  image_url: string | null
  /** A second line: the shop of a product, the category of a shop. */
  detail: string | null
}

export interface PublicStats {
  total_businesses: number
  total_products: number
  total_talents: number
}

export type FeedbackStatus = 'BACKLOG' | 'TODO' | 'IN_PROGRESS' | 'NEEDS_FEEDBACK' | 'DONE'

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

/**
 * `nearest` orders by distance from the visitor, and needs `lat`/`lng` sent
 * alongside it; without them the server falls back to newest.
 */
export type SortOption = 'newest' | 'name' | 'oldest' | 'nearest'

/** Businesses and products can also sort by their stars, rated first. */
export type BusinessSortOption = SortOption | 'rating'

/** The talent directory can also sort by years of experience, most first,
 * and services by their stars, rated first. */
export type TalentSortOption = SortOption | 'experience' | 'rating'

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
export type ProductSortOption = BusinessSortOption | 'price_asc' | 'price_desc'

export interface BusinessQuery {
  q?: string
  category?: string
  location?: string
  origin?: GoodsOrigin
  /** Only shops with at least one product on sale -- the products page. */
  with_products?: boolean
  /** Only owners who chose to show they are displaced. */
  displaced?: boolean
  sort?: BusinessSortOption
  /** The visitor's position, for `nearest` only. Never put in the page URL. */
  lat?: number
  lng?: number
  page?: number
  page_size?: number
}

/** Same as a business search, but its `sort` can also order by price. */
export interface ProductQuery extends Omit<BusinessQuery, 'sort'> {
  sort?: ProductSortOption
  /** Each shop's newest product only, while enough shops have one: home rows. */
  one_per_shop?: boolean
}

export interface TalentQuery {
  q?: string
  skill?: string
  location?: string
  kind?: TalentKind
  /** Remotely or in person; a profile that does both matches either. */
  work_mode?: Exclude<WorkMode, 'BOTH'>
  /** Only owners who chose to show they are displaced. */
  displaced?: boolean
  sort?: TalentSortOption
  /** The visitor's position, for `nearest` only. Never put in the page URL. */
  lat?: number
  lng?: number
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
  /**
   * Where the owner was displaced from, only when they chose to show it on
   * their account page; null otherwise.
   */
  displaced_from?: string | null
}

export interface ProductSummary {
  id: string
  slug: string
  title: string
  price: string | null
  currency: Currency
  image_url: string | null
  /** The card-sized copy, when there is one; fall back to the full image. */
  image_thumb_url?: string | null
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
  /** The product on the shop's own Shopify store, when it has one. */
  buy_url?: string | null
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
 * A visitor's praise, published once an administrator has read it. The
 * author is not verified, so no surface may present it as a verified review.
 */
export interface Testimonial {
  id: string
  author_name: string
  body: string
  /** One to five stars, when the visitor gave any. */
  rating: number | null
  created_at: string
}

/** A published testimonial on the home page, with the listing it praises. */
export interface FeaturedTestimonial extends Testimonial {
  subject_kind: 'business' | 'talent'
  subject_name: string
  subject_slug: string
}

export interface OwnerTestimonial extends Testimonial {
  status: TestimonialStatus
  approved_at: string | null
}

/**
 * The platform's view: the moderation state plus which listing the
 * testimonial is on -- a business or a service profile, exactly one -- so an
 * admin can survey every submission in one place. Carries only the
 * listing's public identity, never the owner's.
 */
export interface AdminTestimonial extends OwnerTestimonial {
  business_id: string | null
  business_name: string | null
  business_slug: string | null
  talent_id: string | null
  talent_name: string | null
  talent_slug: string | null
}

/** A partner-form submission; administrators only. */
export interface AdminPartnerRequest {
  id: string
  name: string
  phone: string
  occupation: string
  residence: string
  offer: string
  created_at: string
  /** Set once marked solved: the request is then in the archive. */
  solved_at: string | null
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
  /** What it is about, if anything: its page ends with these listings. */
  category: Category | null
  location: LocationNode | null
}

/** What an administrator sends; null clears a link, '' is never sent. */
export interface ArticleInput {
  section: ArticleSection
  title: string
  body: string
  slug?: string
  category_id: string | null
  location_id: string | null
}

/** A listing's town and map pin, as an administrator corrects them. */
export interface AdminPlace {
  location_id: string
  latitude: number
  longitude: number
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

/** An order read without its listing in the URL: the link a customer sends
 *  the shop, and the administrators' list of every order. */
export interface OrderWithBusiness extends Order {
  business_id: string
  business_name: string
  business_slug: string
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
/** Pages whose cover photograph an administrator can replace. */
/** The site's own contact details and social accounts; unset is null. */
export interface SiteSettings {
  contact_phone: string | null
  contact_whatsapp: string | null
  contact_email: string | null
  social_facebook: string | null
  social_instagram: string | null
  /** The homepage video, as a YouTube id; null plays the one the site shipped with. */
  home_video: string | null
  offer_video: string | null
}

/** The site's static pages; see `PageText`. `home` is the homepage's
 * photograph section and the line under its video. */
export type PageKey = 'about' | 'offer_eligibility' | 'home' | 'offer_video'

/**
 * A static page's administrator-written text. A null field means the page
 * shows its built-in text from the locale catalog in its place.
 */
export interface PageText {
  key: PageKey
  title_ar: string | null
  title_en: string | null
  summary_ar: string | null
  summary_en: string | null
  body_ar: string | null
  body_en: string | null
}

export type PageTextInput = Omit<PageText, 'key'>

export type PageCoverKey =
  | 'home_video'
  | 'offer_video'
  | 'home'
  | 'offer'
  | 'browse'
  | 'products'
  | 'products_local'
  | 'products_imported'
  | 'talent'
  | 'jobs'
  | 'contact'

/** One of the six places in the about page's team section. */
export interface TeamMember {
  slot: number
  photo_url: string | null
  caption_ar: string | null
  caption_en: string | null
  updated_at: string | null
}

export interface TeamCaptionInput {
  caption_ar: string | null
  caption_en: string | null
}

export interface PageCover {
  page_key: PageCoverKey
  /** Null when the page shows the site's default photograph. */
  image_url: string | null
  updated_at: string | null
}

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

/** A set-aside application, now a listing pending review on its account. */
export interface AttachedApplication {
  application: DiscardedApplication
  kind: DiscardedApplication['kind']
  listing_id: string
}

/** `GET /api/admin/growth-report`: the value equation read off live data. */
export type GrowthLever = 'outcome' | 'likelihood' | 'time' | 'effort'

export interface GrowthShopLine {
  name: string
  slug: string
  orders: number
  views: number
}

export interface GrowthRecommendation {
  key: string
  lever: GrowthLever
  priority: 'high' | 'medium' | 'low'
  count: number | null
}

export interface GrowthReport {
  generated_at: string
  week_starts: string[]
  approved_shops: number
  approved_talents: number
  public_products: number
  pending_reviews: number
  pending_over_48h: number
  shops_with_order_7d: number
  shops_with_order_30d: number
  orders_7d: number
  orders_30d: number
  service_requests_30d: number
  views_30d: number
  orders_per_1000_views: number | null
  median_approval_hours: number | null
  approved_testimonials: number
  goal_usd: number
  order_value_usd: number
  order_value_usd_30d: number
  order_value_lbp: number
  thin_catalogue_shops: number
  shops_without_logo: number
  weekly: {
    orders: number[]
    service_requests: number[]
    views: number[]
    new_sellers: number[]
    new_products: number[]
  }
  health: { with_orders: number; viewed_no_orders: number; unseen: number }
  top_shops: GrowthShopLine[]
  quiet_shops: GrowthShopLine[]
  recommendations: GrowthRecommendation[]
}

export interface GrowthPlan {
  goal_usd: number
  /** Null while the site's default wording stands. */
  offer: string | null
  /** Whether visitors are shown the offer in a popup. */
  offer_popup: boolean
}

export interface OfferPopup {
  enabled: boolean
  offer: string | null
}

/** A development activity announced on the home page, as a visitor reads it. */
export interface Activity {
  id: string
  slug: string
  title: string
  summary: string | null
  body: string
  starts_at: string | null
  ends_at: string | null
  location: string | null
  image_url: string | null
}

export interface AdminActivity extends Activity {
  is_archived: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface ActivityInput {
  title: string
  body: string
  summary: string | null
  starts_at: string | null
  ends_at: string | null
  location: string | null
  sort_order: number
}

export type WorkshopMode = 'ONLINE' | 'IN_PERSON'

/** A published workshop, as a visitor reads it. */
export interface Workshop {
  id: string
  slug: string
  title: string
  description: string
  trainer_name: string | null
  starts_at: string
  ends_at: string | null
  mode: WorkshopMode
  venue: string | null
  /** Null is free. */
  price: string | null
  currency: Currency
  cover_url: string | null
  category: Category | null
  location: LocationNode | null
}

export interface AdminWorkshop extends Workshop {
  is_published: boolean
  registration_count: number
  created_at: string
  updated_at: string
}

export interface WorkshopInput {
  title: string
  description: string
  trainer_name: string | null
  starts_at: string
  ends_at: string | null
  mode: WorkshopMode
  venue: string | null
  price: string | null
  currency: Currency
  category_id: string | null
  location_id: string | null
}

export interface WorkshopRegistration {
  id: string
  full_name: string
  phone_number: string
  created_at: string
}

export type JobType = 'FULL_TIME' | 'PART_TIME' | 'REMOTE' | 'FREELANCE' | 'INTERNSHIP'

/** A job opening the platform posts; published and open ones only, publicly. */
export interface JobOpening {
  id: string
  slug: string
  title: string
  description: string
  employer_name: string | null
  job_type: JobType
  salary: string | null
  /** ISO date; the last day applications are taken. */
  deadline: string | null
  location: LocationNode | null
  work_place: string | null
  work_mode: WorkMode | null
  /** A thumbnail staff chose; null shows the plain card. */
  cover_url?: string | null
  created_at: string
}

export interface AdminJobOpening extends JobOpening {
  is_published: boolean
  application_count: number
  updated_at: string
  /** Set when an employer offered the job on the public form. */
  submitter_name: string | null
  submitter_phone: string | null
  has_id_document: boolean
}

export interface JobOpeningInput {
  title: string
  description: string
  employer_name: string | null
  job_type: JobType
  salary: string | null
  deadline: string | null
  location_id: string | null
  work_place: string | null
  work_mode: WorkMode | null
}

/** An employer's offer from the public form; the ID scan travels beside it. */
export interface JobOfferInput {
  submitter_name: string
  phone_number: string
  employer_name: string
  work_place: string
  work_mode: WorkMode
  title: string
  description: string
}

/** An application as staff read it; the CV is downloaded separately. */
export interface JobApplication {
  id: string
  full_name: string
  email: string
  phone_number: string
  original_filename: string | null
  content_type: string
  size_bytes: number
  created_at: string
}

/** The owner's view of their Shopify store's connection. Never the token. */
export interface ShopifyStatus {
  connected: boolean
  subdomains_available: boolean
  subdomain_base: string
  shop_domain: string | null
  status: 'CONNECTED' | 'UNINSTALLED' | 'ERROR' | null
  storefront_url: string | null
  currency: string | null
  subdomain: string | null
  subdomain_hostname: string | null
  /** True once the owner connected the subdomain inside Shopify. */
  subdomain_live: boolean
  connected_at: string | null
  last_sync_at: string | null
  last_error: string | null
  synced_products: number
  pending_pushes: number
}

/** A company holding a key to the read-only partner feed. */
export interface ApiPartner {
  id: string
  name: string
  key_prefix: string
  scopes: string[]
  active: boolean
  created_at: string
  last_used_at: string | null
}

export interface ApiPartnerIssued extends ApiPartner {
  /** Shown once; only its hash is kept. */
  api_key: string
}
