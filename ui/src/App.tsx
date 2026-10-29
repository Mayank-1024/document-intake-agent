import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import type { DocumentDetail, Field, Summary } from './types'

const DOC_TYPES = ['invoice', 'w2', 'loss_run']

function fmt(v: unknown): string {
  if (v === null || v === undefined) return '(empty)'
  return typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(v)
}

// Corrections are typed by field kind so money stays a number and dates stay ISO strings.
function parseValue(kind: string, raw: string): unknown {
  const t = raw.trim()
  if (t === '') return null
  if (kind === 'money' || kind === 'number') {
    const n = Number(t.replace(/[$,]/g, ''))
    if (Number.isNaN(n)) throw new Error('enter a number')
    return n
  }
  if (kind === 'int') {
    const n = parseInt(t, 10)
    if (Number.isNaN(n)) throw new Error('enter a whole number')
    return n
  }
  if (kind === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(t)) throw new Error('use YYYY-MM-DD')
  return t
}

function Confidence({ value }: { value: number }) {
  const cls = value >= 0.9 ? 'ok' : value >= 0.75 ? 'warn' : 'bad'
  return <span className={`pill ${cls}`}>{value.toFixed(2)}</span>
}

function Citation({ f }: { f: Field }) {
  const cls = f.citation === 'verified' ? 'ok' : f.citation === 'unverifiable' || f.citation === 'absent' ? 'muted' : 'bad'
  return (
    <div>
      <span className={`pill ${cls}`}>{f.citation}</span>
      {f.page ? <span className="muted"> p.{f.page}</span> : null}
      {f.source_text ? <div className="source">"{f.source_text}"</div> : null}
    </div>
  )
}

function FieldRow({ f, current, editable, onCorrect }: {
  f: Field
  current: unknown
  editable: boolean
  onCorrect: (field: Field, raw: string) => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [raw, setRaw] = useState('')
  const [err, setErr] = useState('')
  const corrected = JSON.stringify(current) !== JSON.stringify(f.value)
  return (
    <tr className={f.flags.length ? 'flagged' : ''}>
      <td className="mono">{f.path}</td>
      <td>
        {corrected ? (
          <>
            <s className="muted">{fmt(f.value)}</s> <strong>{fmt(current)}</strong>
          </>
        ) : (
          fmt(f.value)
        )}
      </td>
      <td><Confidence value={f.confidence} /></td>
      <td><Citation f={f} /></td>
      <td>{f.flags.map((x) => <div key={x} className="flag">{x}</div>)}</td>
      <td>
        {editable && !editing && (
          <button className="link" onClick={() => { setRaw(current == null ? '' : String(current)); setEditing(true) }}>
            correct
          </button>
        )}
        {editing && (
          <form
            onSubmit={async (e) => {
              e.preventDefault()
              try {
                await onCorrect(f, raw)
                setEditing(false)
                setErr('')
              } catch (ex) {
                setErr((ex as Error).message)
              }
            }}
          >
            <input autoFocus value={raw} onChange={(e) => setRaw(e.target.value)} />
            <button type="submit">save</button>
            <button type="button" className="link" onClick={() => setEditing(false)}>cancel</button>
            {err && <div className="error">{err}</div>}
          </form>
        )}
      </td>
    </tr>
  )
}

function Detail({ doc, reviewer, onChange }: {
  doc: DocumentDetail
  reviewer: string
  onChange: (d: DocumentDetail) => void
}) {
  const [flaggedOnly, setFlaggedOnly] = useState(doc.flagged_fields > 0)
  const [err, setErr] = useState('')
  const editable = doc.status === 'in_review'
  const fields = doc.result.fields.filter((f) => !flaggedOnly || f.flags.length)
  const failed = doc.result.rules.filter((r) => r.status === 'fail')
  const isImage = /\.(png|jpe?g)$/i.test(doc.filename)

  const correct = async (f: Field, raw: string) => {
    if (!reviewer.trim()) throw new Error('enter your name first')
    onChange(await api.correct(doc.id, f.path, parseValue(f.kind, raw), reviewer))
  }

  return (
    <div className="detail">
      <header>
        <h2>{doc.filename}</h2>
        <div className="muted">
          {doc.doc_type} | {doc.result.page_count} page(s) | {doc.model} | status <b>{doc.status}</b> |{' '}
          {doc.result.input_tokens + doc.result.output_tokens} tokens
          {doc.result.cost_usd != null ? ` | $${doc.result.cost_usd.toFixed(4)}` : ''}
        </div>
      </header>

      <section className="reasons">
        <h3>Why it is here</h3>
        {doc.result.reasons.length === 0 ? <p className="muted">No reasons: auto-accepted.</p> : (
          <ul>
            {Array.from(new Map(doc.result.reasons.map((r) => [r.code + (r.rule ?? ''), r])).values())
              .slice(0, 12)
              .map((r, i) => <li key={i}><span className="pill bad">{r.code}</span> {r.detail}</li>)}
          </ul>
        )}
        {failed.length > 0 && (
          <>
            <h3>Failed checks</h3>
            <ul>{failed.map((r) => <li key={r.rule}><span className="mono">{r.rule}</span>: {r.detail}</li>)}</ul>
          </>
        )}
      </section>

      <div className="split">
        <div className="preview">
          {isImage ? <img src={api.fileUrl(doc.id)} alt={doc.filename} /> : <iframe title="document" src={api.fileUrl(doc.id)} />}
        </div>
        <div className="fields">
          <label className="muted">
            <input type="checkbox" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} /> flagged fields only (
            {doc.flagged_fields} of {doc.result.fields.length})
          </label>
          <table>
            <thead>
              <tr><th>Field</th><th>Value</th><th>Conf.</th><th>Citation</th><th>Flags</th><th /></tr>
            </thead>
            <tbody>
              {fields.map((f) => (
                <FieldRow key={f.path} f={f} current={doc.current_values[f.path]} editable={editable} onCorrect={correct} />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <footer>
        {editable ? (
          <button
            className="primary"
            onClick={async () => {
              if (!reviewer.trim()) return setErr('enter your name first')
              try { onChange(await api.approve(doc.id, reviewer)); setErr('') } catch (ex) { setErr((ex as Error).message) }
            }}
          >
            Approve {doc.actions.some((a) => a.action === 'correct') ? 'with corrections' : 'as extracted'}
          </button>
        ) : <span className="muted">Closed ({doc.status}).</span>}
        {err && <span className="error"> {err}</span>}
        {doc.actions.length > 0 && (
          <ul className="history">
            {doc.actions.map((a, i) => (
              <li key={i} className="muted">
                {a.created_at} {a.reviewer}: {a.action}
                {a.field ? ` ${a.field} ${fmt(a.previous_value)} -> ${fmt(a.new_value)}` : ''}
              </li>
            ))}
          </ul>
        )}
      </footer>
    </div>
  )
}

export default function App() {
  const [showAll, setShowAll] = useState(false)
  const [list, setList] = useState<Summary[]>([])
  const [selected, setSelected] = useState<DocumentDetail | null>(null)
  const [reviewer, setReviewer] = useState('')
  const [docType, setDocType] = useState('invoice')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const refresh = useCallback(async () => {
    try {
      setList(await (showAll ? api.documents() : api.queue()))
      setErr('')
    } catch (ex) {
      setErr(`API unreachable: ${(ex as Error).message}`)
    }
  }, [showAll])

  useEffect(() => { refresh() }, [refresh])

  // #<document id> in the URL opens that document, so a review can be linked to.
  const open = useCallback(async (id: string) => {
    try {
      setSelected(await api.document(id))
      window.location.hash = id
    } catch (ex) {
      setErr((ex as Error).message)
    }
  }, [])
  useEffect(() => {
    const id = window.location.hash.slice(1)
    if (id) open(id)
  }, [open])

  const upload = async (file: File) => {
    setBusy(true)
    try {
      const doc = await api.upload(file, docType)
      setSelected(doc)
      window.location.hash = doc.id
      await refresh()
    } catch (ex) {
      setErr((ex as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app">
      <aside>
        <h1>Review queue</h1>
        <input placeholder="Reviewer name" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
        <div className="upload">
          <select value={docType} onChange={(e) => setDocType(e.target.value)}>
            {DOC_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" disabled={busy}
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          {busy && <div className="muted">Extracting...</div>}
        </div>
        <label className="muted">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> show all documents
        </label>
        {err && <div className="error">{err}</div>}
        <ul className="queue">
          {list.length === 0 && <li className="muted">Nothing waiting.</li>}
          {list.map((d) => (
            <li key={d.id} className={selected?.id === d.id ? 'active' : ''}
              onClick={() => open(d.id)}>
              <div><b>{d.filename}</b> <span className="muted">{d.doc_type}</span></div>
              <div className="muted">{d.status} | {d.flagged_fields} flagged</div>
              <div>{d.reason_codes.map((c) => <span key={c} className="pill bad">{c}</span>)}</div>
            </li>
          ))}
        </ul>
      </aside>
      <main>
        {selected ? (
          <Detail key={selected.id} doc={selected} reviewer={reviewer}
            onChange={(d) => { setSelected(d); refresh() }} />
        ) : <p className="muted">Select a document, or upload one.</p>}
      </main>
    </div>
  )
}
