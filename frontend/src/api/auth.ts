import client from './client'

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface CurrentUser {
  id: number
  username: string
  email: string | null
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  is_admin: boolean
  manage_scope: string | null
  auth_source: string
  department: string | null
  roles: string[]
  permissions: Record<string, string>
  avatar_url: string | null
  created_at: string
  last_login_at: string | null
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/login', { username, password })
  return data
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const { data } = await client.get<CurrentUser>('/auth/me')
  return data
}

export interface AuthMethods {
  local: boolean
  ldap: boolean
  oidc: boolean
  oidc_login_url: string | null
}

export async function fetchAuthMethods(): Promise<AuthMethods> {
  const { data } = await client.get<AuthMethods>('/auth/methods')
  return data
}

export async function uploadAvatar(file: File): Promise<CurrentUser> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post<CurrentUser>('/users/me/avatar', form)
  return data
}

export async function removeAvatar(): Promise<CurrentUser> {
  const { data } = await client.delete<CurrentUser>('/users/me/avatar')
  return data
}
