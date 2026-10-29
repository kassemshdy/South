/**
 * Every backend call the app can make, typed end to end.
 *
 * Components import from here rather than calling `apiRequest` directly, so
 * paths and payload shapes are defined once.
 */

import { apiDownload, apiRequest } from '@/services/api/client'
import type {
  SearchSuggestion,
  AdminReel,
  Reel,
  ReelInput,
  PageCover,
  PageCoverKey,
  TeamCaptionInput,
  TeamMember,
  PageKey,
  PageText,
  PageTextInput,
  TalentKind,
  WorkMode,
  SiteSettings,
  DiscardedApplication,
  GoodsOrigin,
  ContactChannel,
  AdminArticle,
  AdminBusiness,
  AdminPlace,
  AdminTalent,
  AdminTestimonial,
  AdminPartnerRequest,
  AdminUser,
  AdminUserDetail,
  Article,
  ArticleInput,
  AttachedApplication,
  ArticleSection,
  AuthToken,
  BusinessDetail,
  BusinessItem,
  BusinessQuery,
  BusinessStatus,
  BusinessSummary,
  Category,
  Currency,
  EmploymentType,
  Gender,
  ImageKind,
  CredentialState,
  SiteMenu,
  HomeLayout,
  AdminStory,
  Story,
  StoryGroup,
  StoryStatus,
  IssuedPassword,
  LanguageProficiency,
  LocationNode,
  MaritalStatus,
  OwnerBusiness,
  OwnerRelation,
  OwnerTalent,
  Order,
  OrderStatus,
  OrderWithBusiness,
  OwnerTestimonial,
  OwnerViews,
  Paginated,
  PlatformGrowth,
  GrowthReport,
  FeaturedTestimonial,
  AdminWorkshop,
  Workshop,
  WorkshopInput,
  WorkshopRegistration,
  AdminJobOpening,
  JobApplication,
  JobOpening,
  JobOfferInput,
  JobOpeningInput,
  WorkshopMode,
  GrowthPlan,
  ViewAsToken,
  OfferPopup,
  StaffMember,
  StaffPassword,
  StaffRole,
  PlatformStats,
  ProductDetail,
  ProductQuery,
  ProductSummary,
  PublicStats,
  FeedbackAttachmentKind,
  FeedbackPriority,
  FeedbackTicketDetail,
  FeedbackTicketSummary,
  FeedbackUser,
  ServiceRequest,
  SocialPlatform,
  TalentDetail,
  TalentQuery,
  TalentSkill,
  TalentSummary,
  TestimonialStatus,
  User,
  VerificationDocument,
} from '@/types/api'

export interface BusinessPayload {
  name: string
  short_description?: string | null
  description?: string | null
  // Producer detail — published.
  institution_name?: string | null
  /** ISO date (YYYY-MM-DD). */
  founding_date?: string | null
  production_nature?: string | null
  years_of_experience?: number | null
  owner_relation?: OwnerRelation | null
  goods_origin?: GoodsOrigin
  category_id?: string | null
  custom_category_text?: string | null
  location_id?: string | null
  phone?: string | null
  whatsapp?: string | null
  phone_public?: boolean
  email?: string | null
  website?: string | null
  /** A link; the server stores the video id it resolves to. */
  video_url?: string | null
  address_text?: string | null
  latitude?: number | null
  longitude?: number | null
  maps_url?: string | null
  social_links?: { platform: SocialPlatform; url: string }[]
}

export interface ItemPayload {
  title: string
  description?: string | null
  price?: string | null
  currency?: Currency
  is_available?: boolean
  sort_order?: number
  good_type?: string | null
  brand_name?: string | null
  ingredients?: string | null
  manufactured_at?: string | null
  expiry_date?: string | null
  net_weight?: string | null
  external_link?: string | null
  goods_origin?: GoodsOrigin
}

export interface TalentPayload {
  display_name: string
  kind?: TalentKind
  bio?: string | null
  years_experience?: number | null
  skill_id?: string | null
  custom_skill_text?: string | null
  skill_specialty?: string | null
  preferred_contact?: ContactChannel | null
  location_id?: string | null
  latitude?: number | null
  longitude?: number | null
  phone?: string | null
  whatsapp?: string | null
  phone_public?: boolean
  email?: string | null
  website?: string | null
  /** A link; the server stores the video id it resolves to. */
  video_url?: string | null

  // Published professional detail.
  highest_degree?: string | null
  specialization?: string | null
  university?: string | null
  education_years?: number | null
  graduation_date?: string | null
  study_focus?: string | null
  experience?: string | null
  professional_training?: string | null
  skills_text?: string | null
  services_offered?: string | null
  hobbies?: string | null
  employment_type?: EmploymentType | null
  remote_capable?: boolean
  /** Required of a service; the API derives `remote_capable` from it. */
  work_mode?: WorkMode | null
  languages?: { name: string; proficiency: LanguageProficiency }[]
  social_links?: { platform: SocialPlatform; url: string }[]
}

/**
 * The identity fields an account sets on itself.
 *
 * Not part of TalentPayload or BusinessPayload on purpose: identity belongs
 * to the person, so it is written once through PATCH /api/me however many
 * listings the account owns.
 */
export interface IdentityPayload {
  full_name?: string | null
  birth_year?: number | null
  gender?: Gender | null
  marital_status?: MaritalStatus | null
  registration_place?: string | null
  residence_place?: string | null
  is_displaced?: boolean | null
  pre_displacement_place?: string | null
}

/**
 * Who an applicant says they are, as `POST /api/register/*` wants it.
 *
 * Required rather than optional, unlike `IdentityPayload` above: the
 * reviewer is deciding whether this is a real person from the South, and
 * these are what they decide on. Gender and marital status are not here,
 * because nothing in that decision turns on them.
 */
export interface ApplicantIdentity {
  full_name: string
  birth_year: number
  registration_place: string
  residence_place: string
  is_displaced: boolean
  /** Required when `is_displaced`; the API refuses the application without it. */
  pre_displacement_place: string | null
}

/** Both sides of the applicant's ID card. */
export interface ApplicantDocuments {
  front: File | null
  back: File | null
}

/** An applicant, before they have an account. */
export interface Applicant {
  phone: string
  identity: ApplicantIdentity
  /** The scans they attached. The API does not insist; the forms do. */
  documents: ApplicantDocuments
}

export const authApi = {
  /**
   * The only sign-in a client calls.
   *
   * `identifier` is whatever was typed into the form's one box — a phone
   * number for an owner, an email address for an administrator — and the API
   * tells them apart. It answers both kinds of failure with the same
   * sentence, so there is nothing here to branch on.
   */
  login: (identifier: string, password: string) =>
    apiRequest<AuthToken>('/api/auth/login', {
      method: 'POST',
      body: { identifier, password },
    }),
  /**
   * The administrators-only door, behind a URL nothing links to.
   *
   * `login` signs an administrator in too, so this is not the way in — it is
   * the way in when the other one is broken, and an administrator locked out
   * of a deployment has nobody to ask.
   */
  adminLogin: (email: string, password: string) =>
    apiRequest<AuthToken>('/api/auth/admin/login', {
      method: 'POST',
      body: { email, password },
    }),
  /** Replaces one's own password, which ends every other session. */
  changePassword: (current_password: string, new_password: string) =>
    apiRequest<User>('/api/me/password', {
      method: 'POST',
      body: { current_password, new_password },
    }),
  /** Deletes the account and everything it published. Not undoable. */
  deleteAccount: (password: string) =>
    apiRequest<{ message: string }>('/api/me/delete', { method: 'POST', body: { password } }),
  me: () => apiRequest<User>('/api/me'),
  updateProfile: (
    payload: IdentityPayload & {
      display_name?: string | null
      personal_phone_number?: string | null
    },
  ) => apiRequest<User>('/api/me', { method: 'PATCH', body: payload }),

  /** Replaces the account holder's photo; the previous file is deleted. */
  uploadPhoto: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<User>('/api/me/photo', { method: 'POST', formData: form })
  },
  deletePhoto: () => apiRequest<User>('/api/me/photo', { method: 'DELETE' }),

  getVerificationDocument: () =>
    apiRequest<VerificationDocument | null>('/api/me/verification-document'),
  uploadVerificationDocument: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<VerificationDocument>('/api/me/verification-document', {
      method: 'POST',
      formData: form,
    })
  },

  getVerificationDocumentBack: () =>
    apiRequest<VerificationDocument | null>('/api/me/verification-document-back'),
  uploadVerificationDocumentBack: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<VerificationDocument>('/api/me/verification-document-back', {
      method: 'POST',
      formData: form,
    })
  },

  getCvDocument: () => apiRequest<VerificationDocument | null>('/api/me/cv-document'),
  uploadCvDocument: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<VerificationDocument>('/api/me/cv-document', {
      method: 'POST',
      formData: form,
    })
  },
}

export const taxonomyApi = {
  categories: () => apiRequest<Category[]>('/api/categories'),
  locations: () => apiRequest<LocationNode[]>('/api/locations'),
  talentSkills: () => apiRequest<TalentSkill[]>('/api/talent-skills'),
}

export const publicBusinessApi = {
  search: (query: BusinessQuery) =>
    apiRequest<Paginated<BusinessSummary>>('/api/businesses', { query: { ...query } }),
  latest: (limit = 8) =>
    apiRequest<BusinessSummary[]>('/api/businesses/latest', { query: { limit } }),
  stats: () => apiRequest<PublicStats>('/api/businesses/stats'),
  bySlug: (slug: string) =>
    apiRequest<BusinessDetail>(`/api/businesses/${encodeURIComponent(slug)}`),
}

export const publicItemApi = {
  search: (query: ProductQuery) =>
    apiRequest<Paginated<ProductSummary>>('/api/items', { query: { ...query } }),
  bySlug: (slug: string) =>
    apiRequest<ProductDetail>(`/api/items/${encodeURIComponent(slug)}`),
  topRated: () => apiRequest<ProductSummary[]>('/api/items/top-rated'),
  topViewed: () => apiRequest<ProductSummary[]>('/api/items/top-viewed'),
  mostOrdered: () => apiRequest<ProductSummary[]>('/api/items/most-ordered'),
  related: (slug: string) =>
    apiRequest<ProductSummary[]>(`/api/items/${encodeURIComponent(slug)}/related`),
}

/** The partner form (round 3). */
export interface PartnerPayload {
  name: string
  phone: string
  occupation: string
  residence: string
  offer: string
}

export const partnerApi = {
  send: (payload: PartnerPayload, captchaToken: string | null) =>
    apiRequest<{ message: string }>('/api/partners', {
      method: 'POST',
      body: { ...payload, captcha_token: captchaToken },
    }),
}

/** Job openings: anyone reads and applies with a CV; applications are staff-only. */
export const jobApi = {
  list: () => apiRequest<JobOpening[]>('/api/job-openings'),
  bySlug: (slug: string) => apiRequest<JobOpening>(`/api/job-openings/${encodeURIComponent(slug)}`),
  apply: (
    slug: string,
    payload: { full_name: string; email: string; phone_number: string },
    cv: File,
    captchaToken: string | null,
  ) => {
    const form = new FormData()
    form.append('full_name', payload.full_name)
    form.append('email', payload.email)
    form.append('phone_number', payload.phone_number)
    if (captchaToken) form.append('captcha_token', captchaToken)
    form.append('cv', cv)
    return apiRequest<{ message: string }>(
      `/api/job-openings/${encodeURIComponent(slug)}/apply`,
      { method: 'POST', formData: form },
    )
  },
  /** An employer offers a job; it waits as a draft for an administrator. */
  offer: (payload: JobOfferInput, idDocument: File, captchaToken: string | null) => {
    const form = new FormData()
    for (const [key, value] of Object.entries(payload)) form.append(key, value)
    if (captchaToken) form.append('captcha_token', captchaToken)
    form.append('id_document', idDocument)
    return apiRequest<{ message: string }>('/api/job-openings/offer', {
      method: 'POST',
      formData: form,
    })
  },
}

/** Workshops: anyone reads and signs up; who signed up is for staff only. */
export const workshopApi = {
  list: (
    query: {
      when?: 'upcoming' | 'past'
      mode?: WorkshopMode
      category?: string
      location?: string
      limit?: number
    } = {},
  ) =>
    apiRequest<Workshop[]>('/api/workshops', { query: { ...query } }),
  bySlug: (slug: string) => apiRequest<Workshop>(`/api/workshops/${encodeURIComponent(slug)}`),
  register: (
    slug: string,
    payload: { full_name: string; phone_number: string },
    captchaToken: string | null,
  ) =>
    apiRequest<{ message: string }>(`/api/workshops/${encodeURIComponent(slug)}/register`, {
      method: 'POST',
      body: { ...payload, captcha_token: captchaToken },
    }),
}

export const siteSettingsApi = {
  get: () => apiRequest<SiteSettings>('/api/site-settings'),
  offerPopup: () => apiRequest<OfferPopup>('/api/site-settings/offer-popup'),
}

export const menuApi = {
  get: () => apiRequest<SiteMenu>('/api/menu'),
}

export const homeApi = {
  layout: () => apiRequest<HomeLayout>('/api/home/layout'),
  stories: () => apiRequest<StoryGroup[]>('/api/home/stories'),
}

export const pageApi = {
  get: (key: PageKey) => apiRequest<PageText>(`/api/pages/${key}`),
}

export const searchApi = {
  /** Suggestions for what has been typed so far; none under two letters. */
  suggest: (q: string) => apiRequest<SearchSuggestion[]>('/api/search/suggest', { query: { q } }),
}

export const reelApi = {
  /** The published reels, in the administrator's order. */
  list: () => apiRequest<Reel[]>('/api/reels'),
}

export const teamApi = {
  /** The filled slots of the about page's team section, in order. */
  list: () => apiRequest<TeamMember[]>('/api/team'),
}

export const pageCoverApi = {
  /** `{page_key: image_url}` for every page whose cover has been replaced. */
  all: () => apiRequest<Partial<Record<PageCoverKey, string>>>('/api/page-covers'),
}

export const publicArticleApi = {
  list: (section: ArticleSection) =>
    apiRequest<Article[]>('/api/articles', { query: { section } }),
  bySlug: (slug: string) => apiRequest<Article>(`/api/articles/${encodeURIComponent(slug)}`),
}

export const publicTalentApi = {
  search: (query: TalentQuery) =>
    apiRequest<Paginated<TalentSummary>>('/api/talent', { query: { ...query } }),
  latest: (limit = 8) => apiRequest<TalentSummary[]>('/api/talent/latest', { query: { limit } }),
  bySlug: (slug: string) => apiRequest<TalentDetail>(`/api/talent/${encodeURIComponent(slug)}`),
}

/**
 * The caller's own talent profile. No id in any path: a profile is
 * one-per-account, so the authenticated user is the lookup key.
 */
export const ownerTalentApi = {
  stories: () => apiRequest<Story[]>('/api/my/talent/stories'),
  postStory: (file: File, caption: string | null) => {
    const form = new FormData()
    form.append('file', file)
    if (caption) form.append('caption', caption)
    return apiRequest<Story>('/api/my/talent/stories', { method: 'POST', formData: form })
  },
  /** Answers with the stories that remain. */
  deleteStory: (id: string) =>
    apiRequest<Story[]>(`/api/my/talent/stories/${id}`, { method: 'DELETE' }),
  get: () => apiRequest<OwnerTalent>('/api/my/talent'),
  create: (payload: TalentPayload) =>
    apiRequest<OwnerTalent>('/api/talent', { method: 'POST', body: payload }),
  update: (payload: Partial<TalentPayload>) =>
    apiRequest<OwnerTalent>('/api/my/talent', { method: 'PUT', body: payload }),
  remove: () => apiRequest<{ message: string }>('/api/my/talent', { method: 'DELETE' }),
  submit: () => apiRequest<OwnerTalent>('/api/my/talent/submit', { method: 'POST' }),
  readiness: () => apiRequest<string[]>('/api/my/talent/readiness'),

  uploadImage: (file: File, kind: ImageKind, caption?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('kind', kind)
    if (caption) form.append('caption', caption)
    return apiRequest<OwnerTalent>('/api/my/talent/images', { method: 'POST', formData: form })
  },
  deleteImage: (imageId: string) =>
    apiRequest<OwnerTalent>(`/api/my/talent/images/${imageId}`, { method: 'DELETE' }),
  reorderImages: (image_ids: string[]) =>
    apiRequest<OwnerTalent>('/api/my/talent/images/order', {
      method: 'PUT',
      body: { image_ids },
    }),
}

/**
 * What an owner can see about their own listings being looked at.
 *
 * One request for the whole dashboard rather than one per card, so a page
 * with several listings does not fan out.
 */
export const insightsApi = {
  myViews: () => apiRequest<OwnerViews>('/api/my/views'),
}

export interface TestimonialPayload {
  author_name: string
  body: string
  rating?: number | null
}

/** Which kind of listing a testimonial is about. */
export type TestimonialTarget = 'business' | 'talent'

/**
 * Submitting is anonymous and rate limited; reading a testimonial publicly
 * happens through the listing's own page, which carries approved ones only.
 * An owner only reads: an administrator's approval publishes one.
 */
export const testimonialApi = {
  submit: (slug: string, payload: TestimonialPayload, target: TestimonialTarget = 'business') =>
    apiRequest<{ message: string }>(
      `/api/${target === 'talent' ? 'talent' : 'businesses'}/${encodeURIComponent(slug)}/testimonials`,
      { method: 'POST', body: payload },
    ),
  listMine: (businessId: string) =>
    apiRequest<OwnerTestimonial[]>(`/api/businesses/${businessId}/testimonials`),
  listMyTalent: () => apiRequest<OwnerTestimonial[]>('/api/my/talent/testimonials'),
  /** The home page's three best published testimonials. */
  featured: () => apiRequest<FeaturedTestimonial[]>('/api/testimonials/featured'),
}

export interface OrderPayload {
  customer_name: string
  customer_phone: string
  note?: string | undefined
  lines: { item_id: string; quantity: number }[]
}

/**
 * Placing an order needs no account; reading one is the owner's (and the
 * administrators'). Nothing here can fetch an order publicly, which is the
 * point: the id `place` returns opens the order only for its shop's owner.
 */
export const orderApi = {
  place: (slug: string, payload: OrderPayload) =>
    apiRequest<{ message: string; order_id: string }>(`/api/businesses/${encodeURIComponent(slug)}/orders`, {
      method: 'POST',
      body: payload,
    }),
  listMine: (businessId: string) =>
    apiRequest<Order[]>(`/api/businesses/${businessId}/orders`),
  getMine: (orderId: string) => apiRequest<OrderWithBusiness>(`/api/my/orders/${orderId}`),
  setStatus: (businessId: string, orderId: string, status: OrderStatus) =>
    apiRequest<Order>(`/api/businesses/${businessId}/orders/${orderId}/status`, {
      method: 'POST',
      body: { status },
    }),
}

export interface ServiceRequestPayload {
  customer_name: string
  customer_phone: string
  details: string
}

/**
 * Asking a talent profile for work needs no account; reading a request is
 * that person's alone. No profile id in any owner path — a profile is
 * one-per-account, so the token is the lookup key and there is no id a
 * caller could substitute.
 */
export const serviceRequestApi = {
  place: (slug: string, payload: ServiceRequestPayload) =>
    apiRequest<{ message: string }>(`/api/talent/${encodeURIComponent(slug)}/requests`, {
      method: 'POST',
      body: payload,
    }),
  listMine: () => apiRequest<ServiceRequest[]>('/api/my/talent/requests'),
  setStatus: (requestId: string, status: OrderStatus) =>
    apiRequest<ServiceRequest>(`/api/my/talent/requests/${requestId}/status`, {
      method: 'POST',
      body: { status },
    }),
}

export const ownerApi = {
  stories: (businessId: string) => apiRequest<Story[]>(`/api/my/businesses/${businessId}/stories`),
  postStory: (businessId: string, file: File, caption: string | null) => {
    const form = new FormData()
    form.append('file', file)
    if (caption) form.append('caption', caption)
    return apiRequest<Story>(`/api/my/businesses/${businessId}/stories`, {
      method: 'POST',
      formData: form,
    })
  },
  /** Answers with the stories that remain. */
  deleteStory: (businessId: string, id: string) =>
    apiRequest<Story[]>(`/api/my/businesses/${businessId}/stories/${id}`, { method: 'DELETE' }),
  list: () => apiRequest<OwnerBusiness[]>('/api/my/businesses'),
  get: (id: string) => apiRequest<OwnerBusiness>(`/api/businesses/${id}/manage`),
  create: (payload: BusinessPayload) =>
    apiRequest<OwnerBusiness>('/api/businesses', { method: 'POST', body: payload }),
  update: (id: string, payload: Partial<BusinessPayload>) =>
    apiRequest<OwnerBusiness>(`/api/businesses/${id}`, { method: 'PUT', body: payload }),
  remove: (id: string) =>
    apiRequest<{ message: string }>(`/api/businesses/${id}`, { method: 'DELETE' }),
  submit: (id: string) =>
    apiRequest<OwnerBusiness>(`/api/businesses/${id}/submit`, { method: 'POST' }),
  readiness: (id: string) => apiRequest<string[]>(`/api/businesses/${id}/readiness`),

  uploadImage: (id: string, file: File, kind: ImageKind, caption?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('kind', kind)
    if (caption) form.append('caption', caption)
    return apiRequest<OwnerBusiness>(`/api/businesses/${id}/images`, {
      method: 'POST',
      formData: form,
    })
  },
  deleteImage: (id: string, imageId: string) =>
    apiRequest<OwnerBusiness>(`/api/businesses/${id}/images/${imageId}`, { method: 'DELETE' }),

  /**
   * Attach an official paper to the listing. Optional at every point -- a
   * business with no paperwork submits and publishes exactly as before.
   */
  uploadDocument: (id: string, file: File, label?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (label) form.append('label', label)
    return apiRequest<OwnerBusiness>(`/api/businesses/${id}/documents`, {
      method: 'POST',
      formData: form,
    })
  },
  deleteDocument: (id: string, documentId: string) =>
    apiRequest<OwnerBusiness>(`/api/businesses/${id}/documents/${documentId}`, {
      method: 'DELETE',
    }),
  reorderImages: (id: string, image_ids: string[]) =>
    apiRequest<OwnerBusiness>(`/api/businesses/${id}/images/order`, {
      method: 'PUT',
      body: { image_ids },
    }),

  items: (id: string) => apiRequest<BusinessItem[]>(`/api/businesses/${id}/items`),
  createItem: (id: string, payload: ItemPayload) =>
    apiRequest<BusinessItem>(`/api/businesses/${id}/items`, { method: 'POST', body: payload }),
  updateItem: (id: string, itemId: string, payload: Partial<ItemPayload>) =>
    apiRequest<BusinessItem>(`/api/businesses/${id}/items/${itemId}`, {
      method: 'PUT',
      body: payload,
    }),
  deleteItem: (id: string, itemId: string) =>
    apiRequest<{ message: string }>(`/api/businesses/${id}/items/${itemId}`, {
      method: 'DELETE',
    }),
  uploadItemImage: (id: string, itemId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<BusinessItem>(`/api/businesses/${id}/items/${itemId}/image`, {
      method: 'POST',
      formData: form,
    })
  },
  uploadItemGalleryImage: (id: string, itemId: string, file: File, caption?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (caption) form.append('caption', caption)
    return apiRequest<BusinessItem>(`/api/businesses/${id}/items/${itemId}/gallery`, {
      method: 'POST',
      formData: form,
    })
  },
  deleteItemGalleryImage: (id: string, itemId: string, imageId: string) =>
    apiRequest<BusinessItem>(`/api/businesses/${id}/items/${itemId}/gallery/${imageId}`, {
      method: 'DELETE',
    }),
  reorderItemGalleryImages: (id: string, itemId: string, image_ids: string[]) =>
    apiRequest<BusinessItem>(`/api/businesses/${id}/items/${itemId}/gallery/order`, {
      method: 'PUT',
      body: { image_ids },
    }),
}

export type ExportDataset = 'businesses' | 'products' | 'users' | 'talent' | 'orders'

/** The admin user list's search, filters and order; empty means "all". */
export interface AdminUserFilters {
  q?: string
  role?: 'OWNER' | 'ADMIN'
  active?: boolean
  sort?: 'newest' | 'oldest' | 'name' | 'listings'
}

export const adminApi = {
  stats: () => apiRequest<PlatformStats>('/api/admin/stats'),
  growth: (days: number) =>
    apiRequest<PlatformGrowth>('/api/admin/stats/growth', { query: { days } }),
  growthReport: () => apiRequest<GrowthReport>('/api/admin/growth-report'),
  growthPlan: () => apiRequest<GrowthPlan>('/api/admin/growth-plan'),
  setGrowthPlan: (payload: GrowthPlan) =>
    apiRequest<GrowthPlan>('/api/admin/growth-plan', { method: 'PUT', body: payload }),
  exportCsv: (dataset: ExportDataset) => apiDownload(`/api/admin/export/${dataset}.csv`),
  staff: () => apiRequest<StaffMember[]>('/api/admin/staff'),
  inviteStaff: (payload: {
    email: string
    display_name: string
    staff_role: StaffRole
    phone?: string | undefined
  }) => apiRequest<StaffPassword>('/api/admin/staff', { method: 'POST', body: payload }),
  updateStaff: (id: string, payload: { staff_role?: StaffRole; is_active?: boolean }) =>
    apiRequest<StaffMember>(`/api/admin/staff/${id}`, { method: 'PATCH', body: payload }),
  reissueStaffPassword: (id: string) =>
    apiRequest<StaffPassword>(`/api/admin/staff/${id}/password`, { method: 'POST' }),
  orders: (status: OrderStatus | undefined) =>
    apiRequest<OrderWithBusiness[]>('/api/admin/orders', { query: { status } }),
  discardedApplications: (includeDismissed: boolean) =>
    apiRequest<DiscardedApplication[]>('/api/admin/discarded-applications', {
      query: { include_dismissed: includeDismissed },
    }),
  pageCovers: () => apiRequest<PageCover[]>('/api/admin/page-covers'),
  setPageCover: (key: PageCoverKey, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<PageCover>(`/api/admin/page-covers/${key}`, {
      method: 'POST',
      formData: form,
    })
  },
  resetPageCover: (key: PageCoverKey) =>
    apiRequest<PageCover>(`/api/admin/page-covers/${key}`, { method: 'DELETE' }),
  stories: (status: StoryStatus) =>
    apiRequest<AdminStory[]>('/api/admin/stories', { query: { status } }),
  approveStory: (id: string) =>
    apiRequest<Story>(`/api/admin/stories/${id}/approve`, { method: 'POST' }),
  rejectStory: (id: string) =>
    apiRequest<Story>(`/api/admin/stories/${id}/reject`, { method: 'POST' }),
  deleteStory: (id: string) => apiRequest<Story>(`/api/admin/stories/${id}`, { method: 'DELETE' }),
  reels: () => apiRequest<AdminReel[]>('/api/admin/reels'),
  addReel: (values: ReelInput) =>
    apiRequest<AdminReel>('/api/admin/reels', { method: 'POST', body: values }),
  updateReel: (id: string, values: ReelInput) =>
    apiRequest<AdminReel>(`/api/admin/reels/${id}`, { method: 'PUT', body: values }),
  /** Answers with the reels that remain. */
  deleteReel: (id: string) => apiRequest<AdminReel[]>(`/api/admin/reels/${id}`, { method: 'DELETE' }),
  reorderReels: (ids: string[]) =>
    apiRequest<AdminReel[]>('/api/admin/reels/order', { method: 'PUT', body: { ids } }),
  setReelCover: (id: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<AdminReel>(`/api/admin/reels/${id}/cover`, { method: 'POST', formData: form })
  },
  removeReelCover: (id: string) =>
    apiRequest<AdminReel>(`/api/admin/reels/${id}/cover`, { method: 'DELETE' }),
  team: () => apiRequest<TeamMember[]>('/api/admin/team'),
  setTeamCaption: (slot: number, values: TeamCaptionInput) =>
    apiRequest<TeamMember>(`/api/admin/team/${slot}`, { method: 'PUT', body: values }),
  setTeamPhoto: (slot: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<TeamMember>(`/api/admin/team/${slot}/photo`, {
      method: 'POST',
      formData: form,
    })
  },
  removeTeamPhoto: (slot: number) =>
    apiRequest<TeamMember>(`/api/admin/team/${slot}/photo`, { method: 'DELETE' }),
  pages: () => apiRequest<PageText[]>('/api/admin/pages'),
  updatePage: (key: PageKey, values: PageTextInput) =>
    apiRequest<PageText>(`/api/admin/pages/${key}`, { method: 'PUT', body: values }),
  siteSettings: () => apiRequest<SiteSettings>('/api/admin/site-settings'),
  credentialsMessage: () =>
    apiRequest<{ message: string | null }>('/api/admin/site-settings/credentials-message'),
  setCredentialsMessage: (message: string | null) =>
    apiRequest<{ message: string | null }>('/api/admin/site-settings/credentials-message', {
      method: 'PUT',
      body: { message },
    }),
  updateSiteSettings: (values: SiteSettings) =>
    apiRequest<SiteSettings>('/api/admin/site-settings', { method: 'PUT', body: values }),
  dismissApplication: (id: string) =>
    apiRequest<DiscardedApplication>(`/api/admin/discarded-applications/${id}/dismiss`, {
      method: 'POST',
    }),
  attachApplication: (id: string) =>
    apiRequest<AttachedApplication>(`/api/admin/discarded-applications/${id}/attach`, {
      method: 'POST',
    }),
  businesses: (params: { status?: BusinessStatus; q?: string; page?: number; page_size?: number }) =>
    apiRequest<Paginated<AdminBusiness>>('/api/admin/businesses', { query: { ...params } }),
  pending: (page = 1) =>
    apiRequest<Paginated<AdminBusiness>>('/api/admin/businesses/pending', { query: { page } }),
  get: (id: string) => apiRequest<AdminBusiness>(`/api/admin/businesses/${id}`),
  // Permanent: the rows and every file they pointed at. See DeleteForeverButton.
  deleteBusiness: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/businesses/${id}`, { method: 'DELETE' }),
  deleteItem: (businessId: string, itemId: string) =>
    apiRequest<{ message: string }>(`/api/admin/businesses/${businessId}/items/${itemId}`, {
      method: 'DELETE',
    }),
  convertTalentToBusiness: (profileId: string, category_id: string) =>
    apiRequest<{ business_id: string }>(`/api/admin/talent/${profileId}/convert-to-business`, {
      method: 'POST',
      body: { category_id },
    }),
  saveMenu: (menu: SiteMenu) => apiRequest<SiteMenu>('/api/admin/menu', { method: 'PUT', body: menu }),
  saveHomeLayout: (layout: HomeLayout) =>
    apiRequest<HomeLayout>('/api/admin/home/layout', { method: 'PUT', body: layout }),
  setTalentSkill: (profileId: string, skill_id: string, custom_skill_text: string | null) =>
    apiRequest<AdminTalent>(`/api/admin/talent/${profileId}/skill`, {
      method: 'POST',
      body: { skill_id, custom_skill_text },
    }),
  setBusinessCategory: (businessId: string, category_id: string, custom_category_text: string | null) =>
    apiRequest<AdminBusiness>(`/api/admin/businesses/${businessId}/category`, {
      method: 'POST',
      body: { category_id, custom_category_text },
    }),
  setBusinessPlace: (businessId: string, place: AdminPlace) =>
    apiRequest<AdminBusiness>(`/api/admin/businesses/${businessId}/place`, {
      method: 'POST',
      body: place,
    }),
  setTalentPlace: (profileId: string, place: AdminPlace) =>
    apiRequest<AdminTalent>(`/api/admin/talent/${profileId}/place`, {
      method: 'POST',
      body: place,
    }),
  setGoodsOrigin: (businessId: string, goods_origin: GoodsOrigin) =>
    apiRequest<AdminBusiness>(`/api/admin/businesses/${businessId}/goods-origin`, {
      method: 'POST',
      body: { goods_origin },
    }),
  uploadBrandImage: (businessId: string, file: File, kind: 'LOGO' | 'COVER') => {
    const form = new FormData()
    form.append('file', file)
    form.append('kind', kind)
    return apiRequest<AdminBusiness>(`/api/admin/businesses/${businessId}/images`, {
      method: 'POST',
      formData: form,
    })
  },
  deleteTalent: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/talent/${id}`, { method: 'DELETE' }),
  deleteUser: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/users/${id}`, { method: 'DELETE' }),
  partners: (solved = false) =>
    apiRequest<AdminPartnerRequest[]>('/api/admin/partners', { query: { solved } }),
  solvePartner: (id: string) =>
    apiRequest<AdminPartnerRequest>(`/api/admin/partners/${id}/solve`, { method: 'POST' }),
  reopenPartner: (id: string) =>
    apiRequest<AdminPartnerRequest>(`/api/admin/partners/${id}/reopen`, { method: 'POST' }),
  deletePartner: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/partners/${id}`, { method: 'DELETE' }),
  approve: (id: string) =>
    apiRequest<AdminBusiness>(`/api/admin/businesses/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason: string) =>
    apiRequest<AdminBusiness>(`/api/admin/businesses/${id}/reject`, {
      method: 'POST',
      body: { reason },
    }),
  suspend: (id: string, reason?: string) =>
    apiRequest<AdminBusiness>(`/api/admin/businesses/${id}/suspend`, {
      method: 'POST',
      body: { reason: reason ?? null },
    }),
  reactivate: (id: string) =>
    apiRequest<AdminBusiness>(`/api/admin/businesses/${id}/reactivate`, { method: 'POST' }),

  users: (page = 1, filters: AdminUserFilters = {}) =>
    apiRequest<Paginated<AdminUser>>('/api/admin/users', { query: { page, ...filters } }),
  user: (id: string) => apiRequest<AdminUserDetail>(`/api/admin/users/${id}`),
  /** A 30-minute, read-only session on an owner's account. */
  viewAs: (userId: string) =>
    apiRequest<ViewAsToken>(`/api/admin/users/${userId}/view-as`, { method: 'POST' }),
  /**
   * Generates a password for an account and returns it **once**. There is no
   * route that reads it back, so a second call replaces it rather than
   * repeating it — and invalidates any session opened with the first.
   */
  issueCredentials: (userId: string) =>
    apiRequest<IssuedPassword>(`/api/admin/users/${userId}/credentials`, { method: 'POST' }),
  credentialState: (userId: string) =>
    apiRequest<CredentialState>(`/api/admin/users/${userId}/credentials`),

  getVerificationDocument: (userId: string) =>
    apiRequest<VerificationDocument>(`/api/admin/users/${userId}/verification-document`),
  downloadVerificationDocument: (userId: string) =>
    apiDownload(`/api/admin/users/${userId}/verification-document/download`),
  downloadVerificationDocumentBack: (userId: string) =>
    apiDownload(`/api/admin/users/${userId}/verification-document-back/download`),
  downloadCvDocument: (userId: string) =>
    apiDownload(`/api/admin/users/${userId}/cv-document/download`),

  /** A listing's own paper. The only route to the bytes. */
  downloadBusinessDocument: (businessId: string, documentId: string) =>
    apiDownload(`/api/admin/businesses/${businessId}/documents/${documentId}/download`),

  categories: () => apiRequest<Category[]>('/api/admin/categories'),
  createCategory: (body: Partial<Category> & { name_ar: string }) =>
    apiRequest<Category>('/api/admin/categories', { method: 'POST', body }),
  updateCategory: (id: string, body: Partial<Category>) =>
    apiRequest<Category>(`/api/admin/categories/${id}`, { method: 'PUT', body }),
  deleteCategory: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/categories/${id}`, { method: 'DELETE' }),

  talent: (params: { status?: BusinessStatus; q?: string; page?: number; page_size?: number }) =>
    apiRequest<Paginated<AdminTalent>>('/api/admin/talent', { query: { ...params } }),
  pendingTalent: (page = 1) =>
    apiRequest<Paginated<AdminTalent>>('/api/admin/talent/pending', { query: { page } }),
  getTalent: (id: string) => apiRequest<AdminTalent>(`/api/admin/talent/${id}`),
  approveTalent: (id: string) =>
    apiRequest<AdminTalent>(`/api/admin/talent/${id}/approve`, { method: 'POST' }),
  rejectTalent: (id: string, reason: string) =>
    apiRequest<AdminTalent>(`/api/admin/talent/${id}/reject`, {
      method: 'POST',
      body: { reason },
    }),
  suspendTalent: (id: string, reason?: string) =>
    apiRequest<AdminTalent>(`/api/admin/talent/${id}/suspend`, {
      method: 'POST',
      body: { reason: reason ?? null },
    }),
  reactivateTalent: (id: string) =>
    apiRequest<AdminTalent>(`/api/admin/talent/${id}/reactivate`, { method: 'POST' }),

  talentSkills: () => apiRequest<TalentSkill[]>('/api/admin/talent-skills'),
  createTalentSkill: (body: Partial<TalentSkill> & { name_ar: string }) =>
    apiRequest<TalentSkill>('/api/admin/talent-skills', { method: 'POST', body }),
  updateTalentSkill: (id: string, body: Partial<TalentSkill>) =>
    apiRequest<TalentSkill>(`/api/admin/talent-skills/${id}`, { method: 'PUT', body }),
  deleteTalentSkill: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/talent-skills/${id}`, { method: 'DELETE' }),

  locations: () => apiRequest<LocationNode[]>('/api/admin/locations'),
  createLocation: (body: Partial<LocationNode> & { name_ar: string }) =>
    apiRequest<LocationNode>('/api/admin/locations', { method: 'POST', body }),
  updateLocation: (id: string, body: Partial<LocationNode>) =>
    apiRequest<LocationNode>(`/api/admin/locations/${id}`, { method: 'PUT', body }),
  deleteLocation: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/locations/${id}`, { method: 'DELETE' }),

  // Owner controls what is displayed; this is the platform's sight of what was
  // submitted — every testimonial in any state, optionally narrowed to one.
  testimonials: (status?: TestimonialStatus) =>
    apiRequest<AdminTestimonial[]>('/api/admin/testimonials', {
      query: status ? { status } : {},
    }),
  removeTestimonial: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/testimonials/${id}`, { method: 'DELETE' }),
  /** Pass the platform gate. Not a publish — the owner still decides. */
  approveTestimonial: (id: string) =>
    apiRequest<AdminTestimonial>(`/api/admin/testimonials/${id}/approve`, { method: 'POST' }),
  rejectTestimonial: (id: string) =>
    apiRequest<AdminTestimonial>(`/api/admin/testimonials/${id}/reject`, { method: 'POST' }),

  workshops: () => apiRequest<AdminWorkshop[]>('/api/admin/workshops'),
  addExampleWorkshops: () =>
    apiRequest<AdminWorkshop[]>('/api/admin/workshops/examples', { method: 'POST' }),
  createWorkshop: (body: WorkshopInput) =>
    apiRequest<AdminWorkshop>('/api/admin/workshops', { method: 'POST', body }),
  updateWorkshop: (id: string, body: Partial<WorkshopInput>) =>
    apiRequest<AdminWorkshop>(`/api/admin/workshops/${id}`, { method: 'PUT', body }),
  publishWorkshop: (id: string) =>
    apiRequest<AdminWorkshop>(`/api/admin/workshops/${id}/publish`, { method: 'POST' }),
  unpublishWorkshop: (id: string) =>
    apiRequest<AdminWorkshop>(`/api/admin/workshops/${id}/unpublish`, { method: 'POST' }),
  deleteWorkshop: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/workshops/${id}`, { method: 'DELETE' }),
  jobOpenings: () => apiRequest<AdminJobOpening[]>('/api/admin/job-openings'),
  createJobOpening: (body: JobOpeningInput) =>
    apiRequest<AdminJobOpening>('/api/admin/job-openings', { method: 'POST', body }),
  updateJobOpening: (id: string, body: Partial<JobOpeningInput>) =>
    apiRequest<AdminJobOpening>(`/api/admin/job-openings/${id}`, { method: 'PUT', body }),
  publishJobOpening: (id: string) =>
    apiRequest<AdminJobOpening>(`/api/admin/job-openings/${id}/publish`, { method: 'POST' }),
  unpublishJobOpening: (id: string) =>
    apiRequest<AdminJobOpening>(`/api/admin/job-openings/${id}/unpublish`, { method: 'POST' }),
  deleteJobOpening: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/job-openings/${id}`, { method: 'DELETE' }),
  jobApplications: (id: string) =>
    apiRequest<JobApplication[]>(`/api/admin/job-openings/${id}/applications`),
  downloadJobApplicationCv: (jobId: string, applicationId: string) =>
    apiDownload(`/api/admin/job-openings/${jobId}/applications/${applicationId}/cv`),
  downloadJobOfferIdDocument: (jobId: string) =>
    apiDownload(`/api/admin/job-openings/${jobId}/id-document`),
  deleteJobApplication: (jobId: string, applicationId: string) =>
    apiRequest<{ message: string }>(
      `/api/admin/job-openings/${jobId}/applications/${applicationId}`,
      { method: 'DELETE' },
    ),
  uploadWorkshopCover: (id: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<AdminWorkshop>(`/api/admin/workshops/${id}/image`, {
      method: 'POST',
      formData: form,
    })
  },
  workshopRegistrations: (id: string) =>
    apiRequest<WorkshopRegistration[]>(`/api/admin/workshops/${id}/registrations`),
  articles: (section?: ArticleSection) =>
    apiRequest<AdminArticle[]>('/api/admin/articles', { query: section ? { section } : {} }),
  createArticle: (body: ArticleInput) =>
    apiRequest<AdminArticle>('/api/admin/articles', { method: 'POST', body }),
  updateArticle: (id: string, body: Partial<ArticleInput>) => apiRequest<AdminArticle>(`/api/admin/articles/${id}`, { method: 'PUT', body }),
  publishArticle: (id: string) =>
    apiRequest<AdminArticle>(`/api/admin/articles/${id}/publish`, { method: 'POST' }),
  unpublishArticle: (id: string) =>
    apiRequest<AdminArticle>(`/api/admin/articles/${id}/unpublish`, { method: 'POST' }),
  deleteArticle: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/articles/${id}`, { method: 'DELETE' }),
  uploadArticleCover: (id: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiRequest<AdminArticle>(`/api/admin/articles/${id}/image`, {
      method: 'POST',
      formData: form,
    })
  },
  deleteArticleCover: (id: string) =>
    apiRequest<AdminArticle>(`/api/admin/articles/${id}/image`, { method: 'DELETE' }),
}

export interface FeedbackTicketPayload {
  title: string
  description?: string | null
  priority?: FeedbackPriority
  page_path?: string | null
  client_context?: string | null
}

/** What an owner reporting a problem may send. No priority: an administrator
 *  decides that, and the API drops it rather than trusting the client. */
export interface FeedbackSubmissionPayload {
  title: string
  description?: string | null
  page_path?: string | null
  client_context?: string | null
}

/** The receipt a reporter gets back — enough to attach a screenshot to what
 *  was filed, and nothing about the board's own state. */
export interface FeedbackSubmission {
  id: string
  title: string
  created_at: string
}

export interface FeedbackTicketUpdatePayload {
  title?: string
  description?: string | null
  priority?: FeedbackPriority
  assignee_id?: string | null
}

/**
 * Mostly admin-only. The exception is the reporting pair — `submit` and
 * `submitAttachment` — which any signed-in account may call: an owner reports
 * a problem, an administrator triages it. Reporting returns a receipt and no
 * view of the board.
 */
export const feedbackApi = {
  list: () => apiRequest<FeedbackTicketSummary[]>('/api/admin/feedback/tickets'),
  assignees: () => apiRequest<FeedbackUser[]>('/api/admin/feedback/assignees'),
  get: (id: string) => apiRequest<FeedbackTicketDetail>(`/api/admin/feedback/tickets/${id}`),
  // Reporting and triaging are different jobs on different routes. An
  // administrator raising a ticket uses `create` and may set a priority; an
  // owner reporting a problem uses `submit`, which returns a receipt and no
  // view of the board. See docs and backend/app/api/v1/feedback.py.
  submit: (payload: FeedbackSubmissionPayload) =>
    apiRequest<FeedbackSubmission>('/api/feedback', { method: 'POST', body: payload }),
  submitAttachment: (id: string, file: File, kind: FeedbackAttachmentKind) => {
    const form = new FormData()
    form.append('file', file)
    form.append('kind', kind)
    return apiRequest<FeedbackSubmission>(`/api/feedback/${id}/attachments`, {
      method: 'POST',
      body: form,
    })
  },
  create: (payload: FeedbackTicketPayload) =>
    apiRequest<FeedbackTicketDetail>('/api/admin/feedback/tickets', {
      method: 'POST',
      body: payload,
    }),
  update: (id: string, payload: FeedbackTicketUpdatePayload) =>
    apiRequest<FeedbackTicketDetail>(`/api/admin/feedback/tickets/${id}`, {
      method: 'PUT',
      body: payload,
    }),
  remove: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/feedback/tickets/${id}`, { method: 'DELETE' }),
  move: (id: string, status: FeedbackTicketSummary['status'], index: number) =>
    apiRequest<FeedbackTicketSummary[]>(`/api/admin/feedback/tickets/${id}/move`, {
      method: 'POST',
      body: { status, index },
    }),
  addComment: (id: string, body: string) =>
    apiRequest<FeedbackTicketDetail>(`/api/admin/feedback/tickets/${id}/comments`, {
      method: 'POST',
      body: { body },
    }),
  uploadAttachment: (id: string, file: File, kind: FeedbackAttachmentKind) => {
    const form = new FormData()
    form.append('file', file)
    form.append('kind', kind)
    return apiRequest<FeedbackTicketDetail>(`/api/admin/feedback/tickets/${id}/attachments`, {
      method: 'POST',
      formData: form,
    })
  },
  deleteAttachment: (id: string, attachmentId: string) =>
    apiRequest<FeedbackTicketDetail>(
      `/api/admin/feedback/tickets/${id}/attachments/${attachmentId}`,
      { method: 'DELETE' },
    ),
  attachmentUrl: (id: string, attachmentId: string) =>
    `/api/admin/feedback/tickets/${id}/attachments/${attachmentId}/download`,
}

/**
 * Applying for a listing without an account.
 *
 * Unauthenticated by design: this is how someone gets onto the site at all.
 * The response carries a message and nothing else — no id, no status — so a
 * number that already has an account is answered exactly like a new one, and
 * the form cannot be used to ask who is registered.
 */
export interface RegistrationResult {
  message: string
}

/**
 * An application, as the register routes take it: the JSON in one field and
 * the applicant's ID scan beside it.
 *
 * Multipart rather than JSON because the scans travel with the application —
 * there is no account to upload them to yet, and the reviewer decides whether
 * this is a real person from the South. The application stays JSON in one
 * field rather than being flattened into form fields, so there is still one
 * definition of what an application is.
 */
function applicationForm(application: unknown, documents: ApplicantDocuments): FormData {
  const form = new FormData()
  form.append('application', JSON.stringify(application))
  if (documents.front) form.append('document', documents.front)
  if (documents.back) form.append('document_back', documents.back)
  return form
}

export const registrationApi = {
  business: (
    applicant: Applicant,
    business: BusinessPayload,
    captcha_token: string | null,
  ) =>
    apiRequest<RegistrationResult>('/api/register/business', {
      method: 'POST',
      formData: applicationForm(
        {
          login_phone: applicant.phone,
          identity: applicant.identity,
          business,
          captcha_token,
        },
        applicant.documents,
      ),
    }),
  talent: (applicant: Applicant, talent: TalentPayload, captcha_token: string | null) =>
    apiRequest<RegistrationResult>('/api/register/talent', {
      method: 'POST',
      formData: applicationForm(
        {
          login_phone: applicant.phone,
          identity: applicant.identity,
          talent,
          captcha_token,
        },
        applicant.documents,
      ),
    }),
}
