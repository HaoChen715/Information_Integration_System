export interface ParsedField {
  key: string
  label: string
  type: string
  required: boolean
  optionsText: string
}

export interface ParsedTable {
  code: string
  name: string
  fields: ParsedField[]
}

function stripComments(sql: string): string {
  return sql.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/--[^\n]*/g, ' ')
}

function unquoteIdent(raw: string): string {
  const s = raw.trim()
  if (s.length >= 2) {
    const first = s[0]
    const last = s[s.length - 1]
    if ((first === '"' && last === '"') || (first === '`' && last === '`')) {
      return s.slice(1, -1).split(first + first).join(first)
    }
    if (first === '[' && last === ']') return s.slice(1, -1)
  }
  return s
}

function splitTopLevel(text: string): string[] {
  const parts: string[] = []
  let depth = 0
  let quote = ''
  let cur = ''
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (quote) {
      cur += ch
      if (ch === quote) {
        if (text[i + 1] === quote) {
          cur += text[i + 1]
          i++
        } else {
          quote = ''
        }
      }
      continue
    }
    if (ch === "'" || ch === '"' || ch === '`') {
      quote = ch
      cur += ch
      continue
    }
    if (ch === '(') depth++
    else if (ch === ')') depth--
    if (ch === ',' && depth === 0) {
      parts.push(cur)
      cur = ''
      continue
    }
    cur += ch
  }
  if (cur.trim()) parts.push(cur)
  return parts
}

function findClosingParen(text: string, open: number): number {
  let depth = 0
  let quote = ''
  for (let i = open; i < text.length; i++) {
    const ch = text[i]
    if (quote) {
      if (ch === quote) {
        if (text[i + 1] === quote) i++
        else quote = ''
      }
      continue
    }
    if (ch === "'" || ch === '"' || ch === '`') {
      quote = ch
      continue
    }
    if (ch === '(') depth++
    else if (ch === ')') {
      depth--
      if (depth === 0) return i
    }
  }
  return -1
}

function asciiIdent(raw: string): string {
  return raw
    .normalize('NFKD')
    .replace(/[^\x00-\x7F]/g, ' ')
    .replace(/[^A-Za-z0-9_]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
}

function sanitizeCode(raw: string): string {
  let code = asciiIdent(raw).toLowerCase()
  if (!code) return 'table_1'
  if (!/^[a-z]/.test(code)) code = `t_${code}`
  if (code.length < 2) code = 'table_1'
  return code.slice(0, 64)
}

function sanitizeFieldKey(raw: string, index: number): string {
  let key = asciiIdent(raw)
  if (!/^[A-Za-z]/.test(key)) key = `field_${index + 1}`
  return key.slice(0, 64) || `field_${index + 1}`
}

function mapType(rest: string): string {
  const t = rest.trim().toLowerCase()
  if (/^(bool|boolean)\b/.test(t)) return 'boolean'
  if (/^(smallint|integer|int|int2|int4|bigint|int8|serial|bigserial|smallserial)\b/.test(t)) return 'number'
  if (/^(numeric|decimal|real|double\s+precision|float|money)\b/.test(t)) return 'number'
  if (/^date\b/.test(t)) return 'date'
  if (/^(timestamp|timestamptz|time)\b/.test(t)) return 'date'
  if (/^(text|jsonb?|xml|bytea)\b/.test(t)) return 'long_text'
  return 'text'
}

function parseOptions(text: string): string[] {
  return splitTopLevel(text)
    .map((v) => v.trim().replace(/^'/, '').replace(/'$/, '').split("''").join("'"))
    .filter(Boolean)
}

const CONSTRAINT = /^(constraint|primary\s+key|unique|foreign\s+key|check|key|index|exclude)\b/i

export function parseCreateTableDdl(sql: string): ParsedTable {
  const clean = stripComments(sql)
  const match =
    /CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?((?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*)(?:\s*\.\s*(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*))?)\s*\(/i.exec(
      clean,
    )
  if (!match) throw new Error('未找到 CREATE TABLE (...) 语句')

  const tableRaw = match[1].split('.').pop() || match[1]
  let name = unquoteIdent(tableRaw)
  const open = clean.indexOf('(', match.index + match[0].length - 1)
  const close = findClosingParen(clean, open)
  if (open < 0 || close < 0) throw new Error('DDL 括号不匹配')

  const body = clean.slice(open + 1, close)
  const fields: ParsedField[] = []
  const rawNames = new Map<string, string>()
  const fieldByRaw = new Map<string, ParsedField>()
  const usedKeys = new Set<string>()

  for (const item of splitTopLevel(body)) {
    const trimmed = item.trim()
    if (!trimmed || CONSTRAINT.test(trimmed)) continue
    const col = /^("(?:[^"]|"")*"|`[^`]*`|\[[^\]]*\]|[A-Za-z_][\w$]*)\s+([\s\S]+)$/.exec(trimmed)
    if (!col) continue
    const rawName = unquoteIdent(col[1])
    const rest = col[2]
    const required = /\b(primary\s+key|not\s+null)\b/i.test(rest)
    let type = mapType(rest)

    let optionsText = ''
    const check = /\bCHECK\s*\(\s*[^)]*?\bIN\s*\(([^)]*)\)/i.exec(rest)
    if (check) {
      const opts = parseOptions(check[1])
      if (opts.length) {
        type = 'single_select'
        optionsText = opts.join('\n')
      }
    }

    const comment = /\bCOMMENT\s+'((?:[^']|'')*)'/i.exec(rest)
    const label = comment ? comment[1].split("''").join("'") : rawName

    let key = sanitizeFieldKey(rawName, fields.length)
    if (key.toLowerCase() === 'id' && required && type === 'number') continue
    let unique = key
    let n = 2
    while (usedKeys.has(unique)) unique = `${key}_${n++}`
    usedKeys.add(unique)
    rawNames.set(unique, rawName)
    const field: ParsedField = { key: unique, label, type, required, optionsText }
    fieldByRaw.set(rawName, field)
    fields.push(field)
  }

  if (!fields.length) throw new Error('DDL 中没有解析到字段')

  for (const field of fields) {
    if (field.optionsText) continue
    const rawName = rawNames.get(field.key) || field.key
    const col = escapeRegExp(rawName)
    const re = new RegExp(`CHECK\\s*\\(\\s*\\(*\\s*["\`\\[]?${col}["\`\\]]?\\s+IN\\s*\\(([^)]*)\\)`, 'i')
    const found = re.exec(body)
    if (found) {
      const opts = parseOptions(found[1])
      if (opts.length) {
        field.type = 'single_select'
        field.optionsText = opts.join('\n')
      }
    }
  }

  const tableComment =
    /COMMENT\s+ON\s+TABLE\s+((?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*)(?:\s*\.\s*(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*))?)\s+IS\s+'((?:[^']|'')*)'/i.exec(
      clean,
    )
  if (tableComment) {
    const parts = tableComment[1].split('.').map((s) => unquoteIdent(s))
    if (sanitizeCode(parts[parts.length - 1]) === sanitizeCode(name)) {
      name = tableComment[2].split("''").join("'")
    }
  }
  const inlineTableComment = /\)\s*COMMENT\s*=\s*'((?:[^']|'')*)'/i.exec(clean.slice(close))
  if (inlineTableComment) name = inlineTableComment[1].split("''").join("'")

  const columnComment =
    /COMMENT\s+ON\s+COLUMN\s+((?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*)(?:\s*\.\s*(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*)){1,2})\s+IS\s+'((?:[^']|'')*)'/gi
  let cm: RegExpExecArray | null
  while ((cm = columnComment.exec(clean))) {
    const parts = cm[1].split('.').map((s) => unquoteIdent(s))
    const field = fieldByRaw.get(parts[parts.length - 1])
    if (field) field.label = cm[2].split("''").join("'")
  }

  return { code: sanitizeCode(name), name, fields }
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
