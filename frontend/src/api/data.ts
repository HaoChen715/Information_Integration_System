import client from './client'

export interface SelectOption {
  id: number
  value: string
  color: string
}

export interface BaserowField {
  id: number
  name: string
  type: string
  primary?: boolean
  select_options?: SelectOption[]
}

export interface Dataset {
  key: string
  name: string
  table_id: string
  source: string
}

export interface RowsPage {
  count: number
  next: string | null
  previous: string | null
  results: Record<string, unknown>[]
}

export async function fetchDatasets(): Promise<Dataset[]> {
  const { data } = await client.get<Dataset[]>('/data/datasets')
  return data
}

export async function fetchFields(tableId: string): Promise<BaserowField[]> {
  const { data } = await client.get<BaserowField[]>(`/data/tables/${tableId}/fields`)
  return data
}

export async function fetchRows(
  tableId: string,
  params: { page?: number; size?: number; search?: string } = {},
): Promise<RowsPage> {
  const { data } = await client.get<RowsPage>(`/data/tables/${tableId}/rows`, { params })
  return data
}

export async function createRow(
  tableId: string,
  payload: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const { data } = await client.post(`/data/tables/${tableId}/rows`, payload)
  return data
}

export async function updateRow(
  tableId: string,
  rowId: number,
  payload: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const { data } = await client.patch(`/data/tables/${tableId}/rows/${rowId}`, payload)
  return data
}

export async function deleteRow(tableId: string, rowId: number): Promise<void> {
  await client.delete(`/data/tables/${tableId}/rows/${rowId}`)
}
