import client from './client'

export interface BaserowTable {
  id?: number
  name: string
  table_id: string
  enabled: boolean
}

export interface BaserowSource {
  id: number
  name: string
  url: string
  token_set: boolean
  token_hint: string
  department_field: string
  enabled: boolean
  tables: BaserowTable[]
}

export interface SourcePayload {
  name: string
  url: string
  token?: string
  department_field: string
  enabled: boolean
  tables: { name: string; table_id: string; enabled: boolean }[]
}

export interface TestResult {
  ok: boolean
  count: number
  fields: string[]
}

export async function fetchSources(): Promise<BaserowSource[]> {
  const { data } = await client.get<BaserowSource[]>('/admin/baserow/sources')
  return data
}

export async function createSource(payload: SourcePayload): Promise<BaserowSource> {
  const { data } = await client.post<BaserowSource>('/admin/baserow/sources', payload)
  return data
}

export async function updateSource(id: number, payload: SourcePayload): Promise<BaserowSource> {
  const { data } = await client.put<BaserowSource>(`/admin/baserow/sources/${id}`, payload)
  return data
}

export async function deleteSource(id: number): Promise<void> {
  await client.delete(`/admin/baserow/sources/${id}`)
}

export async function testConnection(payload: {
  url: string
  token: string
  table_id: string
}): Promise<TestResult> {
  const { data } = await client.post<TestResult>('/admin/baserow/test', payload)
  return data
}

export interface BaserowFieldInfo {
  name: string
  type: string
}

export interface BaserowOptions {
  default_url: string
  departments: string[]
}

export async function fetchOptions(): Promise<BaserowOptions> {
  const { data } = await client.get<BaserowOptions>('/admin/baserow/options')
  return data
}

export async function fetchTableFields(payload: {
  url: string
  token: string
  table_id: string
}): Promise<BaserowFieldInfo[]> {
  const { data } = await client.post<BaserowFieldInfo[]>('/admin/baserow/fields', payload)
  return data
}
