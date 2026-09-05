/**
 * Every backend call the app can make, typed end to end.
 *
 * Components import from here rather than calling `apiRequest` directly, so
 * paths and payload shapes are defined once.
 */

import { apiRequest } from '@/services/api/client'
import type {
  AdminBusiness,
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
  Paginated,
  PlatformStats,
  PublicStats,
  RequestOtpResponse,
  SocialPlatform,
  User,
} from '@/types/api'

export interface BusinessPayload {
  name: string
  short_description?: string | null
  description?: string | null
  category_id?: string | null
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
  updateProfile: (display_name: string | null) =>
    apiRequest<User>('/api/me', { method: 'PATCH', body: { display_name } }),
}

export const taxonomyApi = {
  categories: () => apiRequest<Category[]>('/api/categories'),
  locations: () => apiRequest<LocationNode[]>('/api/locations'),
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

  categories: () => apiRequest<Category[]>('/api/admin/categories'),
  createCategory: (body: Partial<Category> & { name_ar: string }) =>
    apiRequest<Category>('/api/admin/categories', { method: 'POST', body }),
  updateCategory: (id: string, body: Partial<Category>) =>
    apiRequest<Category>(`/api/admin/categories/${id}`, { method: 'PUT', body }),
  deleteCategory: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/categories/${id}`, { method: 'DELETE' }),

  locations: () => apiRequest<LocationNode[]>('/api/admin/locations'),
  createLocation: (body: Partial<LocationNode> & { name_ar: string }) =>
    apiRequest<LocationNode>('/api/admin/locations', { method: 'POST', body }),
  updateLocation: (id: string, body: Partial<LocationNode>) =>
    apiRequest<LocationNode>(`/api/admin/locations/${id}`, { method: 'PUT', body }),
  deleteLocation: (id: string) =>
    apiRequest<{ message: string }>(`/api/admin/locations/${id}`, { method: 'DELETE' }),
}
