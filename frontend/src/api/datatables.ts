import client from './client'

export interface FieldOption {
  value: string
  color?: string
}

export interface DataField {
  id: number
  key: string
  label: string
  type: string
  required: boolean
  options: FieldOption[]
}

export interface DataTable {
  id: number
  code: string
  name: string
  description: string | null
  title_field: string
  scope_by_department: boolean
  department_field: string
  fields: DataField[]
}

export interface FieldDef {
  key: string
  label: string
  type: string
  required: boolean
  options: FieldOption[]
}

export interface TablePayload {
  code: string
  name: string
  description?: string | null
  title_field?: string
  scope_by_department?: boolean
  department_field?: string
  fields: FieldDef[]
}

export interface DataRecord {
  id: number
  data: Record<string, unknown>
  owner_username: string
  department: string | null
  created_at: string
  updated_at: string
}

export async function listAdminTables(): Promise<DataTable[]> {
  const { data } = await client.get<DataTable[]>('/admin/datatables')
  return data
}

export async function createTable(payload: TablePayload): Promise<DataTable> {
  const { data } = await client.post<DataTable>('/admin/datatables', payload)
  return data
}

export async function updateTable(
  id: number,
  payload: Partial<TablePayload>,
): Promise<DataTable> {
  const { data } = await client.put<DataTable>(`/admin/datatables/${id}`, payload)
  return data
}

export async function deleteTable(id: number): Promise<void> {
  await client.delete(`/admin/datatables/${id}`)
}

export async function listTables(): Promise<DataTable[]> {
  const { data } = await client.get<DataTable[]>('/datatables')
  return data
}

export async function listRecords(code: string, search?: string): Promise<DataRecord[]> {
  const { data } = await client.get<DataRecord[]>(`/datatables/${code}/records`, {
    params: search ? { search } : undefined,
  })
  return data
}

export async function createRecord(
  code: string,
  values: Record<string, unknown>,
): Promise<DataRecord> {
  const { data } = await client.post<DataRecord>(`/datatables/${code}/records`, { data: values })
  return data
}

export async function updateRecord(
  code: string,
  id: number,
  values: Record<string, unknown>,
): Promise<DataRecord> {
  const { data } = await client.put<DataRecord>(`/datatables/${code}/records/${id}`, { data: values })
  return data
}

export async function deleteRecord(code: string, id: number): Promise<void> {
  await client.delete(`/datatables/${code}/records/${id}`)
}
