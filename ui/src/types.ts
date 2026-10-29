export type Field = {
  path: string
  kind: string
  value: unknown
  confidence: number
  page: number | null
  source_text: string | null
  row: number | null
  citation: string
  flags: string[]
}

export type Reason = { code: string; detail: string; field: string | null; rule: string | null }
export type Rule = { rule: string; status: 'pass' | 'fail' | 'skipped'; detail: string; fields: string[] }

export type Summary = {
  id: string
  filename: string
  doc_type: string
  route: string
  status: string
  model: string
  created_at: string
  reason_codes: string[]
  flagged_fields: number
}

export type Action = {
  action: 'approve' | 'correct'
  field: string | null
  previous_value: unknown
  new_value: unknown
  reviewer: string
  note: string | null
  created_at: string
}

export type DocumentDetail = Summary & {
  result: {
    fields: Field[]
    rules: Rule[]
    reasons: Reason[]
    page_count: number
    has_text_layer: boolean
    attempts: number
    input_tokens: number
    output_tokens: number
    cost_usd: number | null
    latency_ms: number
  }
  actions: Action[]
  current_values: Record<string, unknown>
}
