/**
 * Every backend call the app can make, typed end to end.
 *
 * Components import from here rather than calling `apiRequest` directly, so
 * paths and payload shapes are defined once.
 */

import { apiDownload, apiRequest } from '@/services/api/client'
import type {
  ContactChannel,
  AdminArticle,
  AdminBusiness,
  AdminTalent,
  AdminTestimonial,
  AdminUser,
  AdminUserDetail,
  Article,
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
  IssuedPassword,
  LanguageProficiency,
  LocationNode,
  MaritalStatus,
  OwnerBusiness,
  OwnerRelation,
  OwnerTalent,
  Order,
  OrderStatus,
  OwnerTestimonial,
  OwnerViews,
  Paginated,
  PlatformStats,
  ProductDetail,
  ProductQuery,
  ProductSummary,
  PublicStats,
  RequestOtpResponse,
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
  category_id?: string | null
  custom_category_text?: string | null
  location_id?: string | null
  phone?: string | null
  whatsapp?: string | null
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
}

export interface TalentPayload {
  display_name: string
  bio?: string | null
  years_experience?: number | null
  skill_id?: string | null
  custom_skill_text?: string | null
  skill_specialty?: string | null
  preferred_contact?: ContactChannel | null
  location_id?: string | null
  phone?: string | null
  whatsapp?: string | null
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
  languages?: { name: string; proficiency: LanguageProficiency }[]
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
}

export const authApi = {
  requestOtp: (phone_number: string) =>
    apiRequest<RequestOtpResponse>('/api/auth/request-otp', {
      method: 'POST',
      body: { phone_number },
    }),
  verifyOtp: (phone_number: string, code: string) =>
    apiRequest<AuthToken>('/api/auth/verify-otp', {
      method: 'POST',
      body: { phone_number, code },
    }),
  adminLogin: (email: string, password: string) =>
    apiRequest<AuthToken>('/api/auth/admin/login', {
      method: 'POST',
      body: { email, password },
    }),
  /**
   * Phone and password — the way in that needs no SMS or WhatsApp gateway,
   * and therefore the only one that currently works. Administrators use
   * `adminLogin`; this route refuses them.
   */
  login: (phone_number: string, password: string) =>
    apiRequest<AuthToken>('/api/auth/login', {
      method: 'POST',
      body: { phone_number, password },
    }),
  /** Replaces one's own password, which ends every other session. */
  changePassword: (current_password: string, new_password: string) =>
    apiRequest<User>('/api/me/password', {
      method: 'POST',
      body: { current_password, new_password },
    }),
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
}

/**
 * Submitting is anonymous and rate limited; reading a testimonial publicly
 * happens through the business profile, which carries approved ones only.
 */
export const testimonialApi = {
  submit: (slug: string, payload: TestimonialPayload) =>
    apiRequest<{ message: string }>(
      `/api/businesses/${encodeURIComponent(slug)}/testimonials`,
      { method: 'POST', body: payload },
    ),
  listMine: (businessId: string) =>
    apiRequest<OwnerTestimonial[]>(`/api/businesses/${businessId}/testimonials`),
  approve: (businessId: string, id: string) =>
    apiRequest<OwnerTestimonial>(
      `/api/businesses/${businessId}/testimonials/${id}/approve`,
      { method: 'POST' },
    ),
  hide: (businessId: string, id: string) =>
    apiRequest<OwnerTestimonial>(
      `/api/businesses/${businessId}/testimonials/${id}/hide`,
      { method: 'POST' },
    ),
}

export interface OrderPayload {
  customer_name: string
  customer_phone: string
  note?: string | undefined
  lines: { item_id: string; quantity: number }[]
}

/**
 * Placing an order needs no account; reading one is the owner's alone.
 * Nothing here can fetch an order publicly, which is the point.
 */
export const orderApi = {
  place: (slug: string, payload: OrderPayload) =>
    apiRequest<{ message: string }>(`/api/businesses/${encodeURIComponent(slug)}/orders`, {
      method: 'POST',
      body: payload,
    }),
  listMine: (businessId: string) =>
    apiRequest<Order[]>(`/api/businesses/${businessId}/orders`),
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

export const adminApi = {
  stats: () => apiRequest<PlatformStats>('/api/admin/stats'),
  businesses: (params: { status?: BusinessStatus; q?: string; page?: number; page_size?: number }) =>
    apiRequest<Paginated<AdminBusiness>>('/api/admin/businesses', { query: { ...params } }),
  pending: (page = 1) =>
    apiRequest<Paginated<AdminBusiness>>('/api/admin/businesses/pending', { query: { page } }),
  get: (id: string) => apiRequest<AdminBusiness>(`/api/admin/businesses/${id}`),
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

  users: (page = 1) =>
    apiRequest<Paginated<AdminUser>>('/api/admin/users', { query: { page } }),
  user: (id: string) => apiRequest<AdminUserDetail>(`/api/admin/users/${id}`),
  /**
   * Generates a password for an account and returns it **once**. There is no
   * route that reads it back, so a second call replaces it rather than
   * repeating it — and invalidates any session opened with the first.
   */
  issueCredentials: (userId: string) =>
    apiRequest<IssuedPassword>(`/api/admin/users/${userId}/credentials`, { method: 'POST' }),

  getVerificationDocument: (userId: string) =>
    apiRequest<VerificationDocument>(`/api/admin/users/${userId}/verification-document`),
  downloadVerificationDocument: (userId: string) =>
    apiDownload(`/api/admin/users/${userId}/verification-document/download`),
  downloadCvDocument: (userId: string) =>
    apiDownload(`/api/admin/users/${userId}/cv-document/download`),

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
  clearTestimonial: (id: string) =>
    apiRequest<AdminTestimonial>(`/api/admin/testimonials/${id}/clear`, { method: 'POST' }),
  rejectTestimonial: (id: string) =>
    apiRequest<AdminTestimonial>(`/api/admin/testimonials/${id}/reject`, { method: 'POST' }),

  articles: (section?: ArticleSection) =>
    apiRequest<AdminArticle[]>('/api/admin/articles', { query: section ? { section } : {} }),
  createArticle: (body: { section: ArticleSection; title: string; body: string; slug?: string }) =>
    apiRequest<AdminArticle>('/api/admin/articles', { method: 'POST', body }),
  updateArticle: (
    id: string,
    body: Partial<{ section: ArticleSection; title: string; body: string; slug: string }>,
  ) => apiRequest<AdminArticle>(`/api/admin/articles/${id}`, { method: 'PUT', body }),
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

export const registrationApi = {
  business: (login_phone: string, business: BusinessPayload, captcha_token: string | null) =>
    apiRequest<RegistrationResult>('/api/register/business', {
      method: 'POST',
      body: { login_phone, business, captcha_token },
    }),
  talent: (login_phone: string, talent: TalentPayload, captcha_token: string | null) =>
    apiRequest<RegistrationResult>('/api/register/talent', {
      method: 'POST',
      body: { login_phone, talent, captcha_token },
    }),
}
