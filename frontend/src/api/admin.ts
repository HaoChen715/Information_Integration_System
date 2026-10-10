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
  is_department_manager: boolean
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
  role_names: string[]
  permissions: Record<string, string>
  direct_permissions: Grant[]
  avatar_url: string | null
}

export interface RolePayload {
  code: string
  name: string
  description?: string | null
  is_admin: boolean
  is_department_manager: boolean
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

export interface UserCreatePayload {
  username: string
  password: string
  full_name?: string | null
  email?: string | null
  department?: string | null
  roles: string[]
  is_active: boolean
}

export async function createUser(payload: UserCreatePayload): Promise<AdminUser> {
  const { data } = await client.post<AdminUser>('/admin/users', payload)
  return data
}

export async function deleteUser(id: number): Promise<void> {
  await client.delete(`/admin/users/${id}`)
}

export interface DepartmentMember {
  id: number
  username: string
  full_name: string | null
  department: string | null
  avatar_url: string | null
  roles: string[]
  role_names: string[]
  is_active: boolean
  last_seen_at: string | null
}

export async function fetchDepartmentMembers(): Promise<DepartmentMember[]> {
  const { data } = await client.get<DepartmentMember[]>('/departments/me/members')
  return data
}

export interface OnlineUser {
  id: number
  username: string
  full_name: string | null
  department: string | null
  email: string | null
  auth_source: string
  roles: string[]
  last_login_at: string | null
  last_seen_at: string | null
  avatar_url: string | null
}

export async function fetchOnlineUsers(): Promise<OnlineUser[]> {
  const { data } = await client.get<OnlineUser[]>('/admin/online-users')
  return data
}

export interface Department {
  id: number
  name: string
  description: string | null
}

export async function fetchDepartments(): Promise<Department[]> {
  const { data } = await client.get<Department[]>('/admin/departments')
  return data
}

export async function createDepartment(payload: {
  name: string
  description?: string | null
}): Promise<Department> {
  const { data } = await client.post<Department>('/admin/departments', payload)
  return data
}

export async function updateDepartment(
  id: number,
  payload: { name?: string; description?: string | null },
): Promise<Department> {
  const { data } = await client.put<Department>(`/admin/departments/${id}`, payload)
  return data
}

export async function deleteDepartment(id: number): Promise<void> {
  await client.delete(`/admin/departments/${id}`)
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
