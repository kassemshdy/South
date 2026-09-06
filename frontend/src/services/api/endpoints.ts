/**
 * Every backend call the app can make, typed end to end.
 *
 * Components import from here rather than calling `apiRequest` directly, so
 * paths and payload shapes are defined once.
 */

import { apiDownload, apiRequest } from '@/services/api/client'
import type {
  AdminBusiness,
  AdminTalent,
  AdminUser,
  AuthToken,
  BusinessDetail,
  BusinessItem,
  BusinessQuery,
  BusinessStatus,
  BusinessSummary,
  Category,
  Currency,
  ImageKind,
  LocationNode,
  OwnerBusiness,
  OwnerTalent,
  Paginated,
  PlatformStats,
  ProductDetail,
  ProductSummary,
  PublicStats,
  RequestOtpResponse,
  FeedbackAttachmentKind,
  FeedbackPriority,
  FeedbackTicketDetail,
  FeedbackTicketSummary,
  FeedbackUser,
  SocialPlatform,
  TalentDetail,
  TalentQuery,
  TalentSkill,
  TalentSummary,
  User,
  VerificationDocument,
} from '@/types/api'

export interface BusinessPayload {
  name: string
  short_description?: string | null
  description?: string | null
  category_id?: string | null
  custom_category_text?: string | null
  location_id?: string | null
  phone?: string | null
  whatsapp?: string | null
  email?: string | null
  website?: string | null
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
}

export interface TalentPayload {
  display_name: string
  headline?: string | null
  bio?: string | null
  years_experience?: number | null
  skill_id?: string | null
  custom_skill_text?: string | null
  location_id?: string | null
  phone?: string | null
  whatsapp?: string | null
  email?: string | null
  website?: string | null
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
  me: () => apiRequest<User>('/api/me'),
  updateProfile: (payload: { display_name?: string | null; personal_phone_number?: string | null }) =>
    apiRequest<User>('/api/me', { method: 'PATCH', body: payload }),

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
  search: (query: BusinessQuery) =>
    apiRequest<Paginated<ProductSummary>>('/api/items', { query: { ...query } }),
  bySlug: (slug: string) =>
    apiRequest<ProductDetail>(`/api/items/${encodeURIComponent(slug)}`),
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

  getVerificationDocument: (userId: string) =>
    apiRequest<VerificationDocument>(`/api/admin/users/${userId}/verification-document`),
  downloadVerificationDocument: (userId: string) =>
    apiDownload(`/api/admin/users/${userId}/verification-document/download`),

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
}

export interface FeedbackTicketPayload {
  title: string
  description?: string | null
  priority?: FeedbackPriority
  page_path?: string | null
  client_context?: string | null
}

export interface FeedbackTicketUpdatePayload {
  title?: string
  description?: string | null
  priority?: FeedbackPriority
  assignee_id?: string | null
}

/**
 * Every route here is admin-only — there is no owner- or public-facing
 * counterpart to any of this, unlike ownerApi/adminApi's business split.
 */
export const feedbackApi = {
  list: () => apiRequest<FeedbackTicketSummary[]>('/api/admin/feedback/tickets'),
  assignees: () => apiRequest<FeedbackUser[]>('/api/admin/feedback/assignees'),
  get: (id: string) => apiRequest<FeedbackTicketDetail>(`/api/admin/feedback/tickets/${id}`),
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
