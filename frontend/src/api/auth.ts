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
  auth_source: string
  roles: string[]
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
