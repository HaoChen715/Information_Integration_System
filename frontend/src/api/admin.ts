import client from './client'

export interface PermissionItem {
  id: number
  code: string
  name: string
  resource: string
  action: string
}

export interface PermissionGroup {
  resource: string
  label: string
  permissions: PermissionItem[]
}

export interface Grant {
  code: string
  data_scope: string
}

export interface Role {
  id: number
  code: string
  name: string
  description: string | null
  is_system: boolean
  is_admin: boolean
  permissions: Grant[]
}

export interface AdminUser {
  id: number
  username: string
  email: string | null
  full_name: string | null
  department: string | null
  is_active: boolean
  is_superuser: boolean
  auth_source: string
  roles: string[]
  permissions: Record<string, string>
  direct_permissions: Grant[]
}

export interface RolePayload {
  code: string
  name: string
  description?: string | null
  is_admin: boolean
  permissions: Grant[]
}

export async function fetchPermissions(): Promise<PermissionGroup[]> {
  const { data } = await client.get<PermissionGroup[]>('/admin/permissions')
  return data
}

export async function fetchRoles(): Promise<Role[]> {
  const { data } = await client.get<Role[]>('/admin/roles')
  return data
}

export async function createRole(payload: RolePayload): Promise<Role> {
  const { data } = await client.post<Role>('/admin/roles', payload)
  return data
}

export async function updateRole(
  id: number,
  payload: Partial<RolePayload>,
): Promise<Role> {
  const { data } = await client.put<Role>(`/admin/roles/${id}`, payload)
  return data
}

export async function deleteRole(id: number): Promise<void> {
  await client.delete(`/admin/roles/${id}`)
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  const { data } = await client.get<AdminUser[]>('/admin/users')
  return data
}

export interface UserStats {
  total_users: number
  active_users: number
  online_users: number
  by_source: Record<string, number>
  online_window_minutes: number
}

export async function fetchStats(): Promise<UserStats> {
  const { data } = await client.get<UserStats>('/admin/stats')
  return data
}

export async function updateUser(
  id: number,
  payload: { full_name?: string | null; department?: string | null; is_active?: boolean },
): Promise<AdminUser> {
  const { data } = await client.put<AdminUser>(`/admin/users/${id}`, payload)
  return data
}

export async function assignRoles(id: number, roles: string[]): Promise<AdminUser> {
  const { data } = await client.put<AdminUser>(`/admin/users/${id}/roles`, { roles })
  return data
}

export async function setUserPermissions(id: number, permissions: Grant[]): Promise<AdminUser> {
  const { data } = await client.put<AdminUser>(`/admin/users/${id}/permissions`, { permissions })
  return data
}

export async function setSuperuser(id: number, value: boolean): Promise<AdminUser> {
  const { data } = await client.put<AdminUser>(`/admin/users/${id}/superuser`, null, {
    params: { value },
  })
  return data
}
