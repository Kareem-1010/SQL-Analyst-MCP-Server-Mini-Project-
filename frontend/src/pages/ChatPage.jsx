import { useState, useRef, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, ArrowLeft, Database, Sparkles, Copy, Download,
  ChevronDown, ChevronUp, BarChart2, Play, CheckCircle,
  AlertCircle, Code2, MessageSquare
} from 'lucide-react'
import { runQuery, getTables, callMCPTool } from '../services/api'
import ConfirmModal from '../components/ConfirmModal'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'

// Detect SQL that modifies data — requires double confirmation
const DESTRUCTIVE_PATTERN = /\b(DELETE|UPDATE|INSERT|DROP|TRUNCATE|ALTER)\b/i
const isDestructive = (sql) => DESTRUCTIVE_PATTERN.test(sql)

const COLORS = ['#4f8ef7', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']

function useTypingEffect(text, speed = 12) {
  const [displayed, setDisplayed] = useState('')
  useEffect(() => {
    if (!text) { setDisplayed(''); return }
    setDisplayed('')
    let i = 0
    const t = setInterval(() => {
      setDisplayed(text.slice(0, i + 1))
      i++
      if (i >= text.length) clearInterval(t)
    }, speed)
    return () => clearInterval(t)
  }, [text])
  return displayed
}

const detectChartType = (cols) => {
  if (!cols || cols.length < 2) return 'bar'
  const hasDate = cols.some(c => /date|time|month|year|day/.test(c))
  const hasName = cols.some(c => /name|category|type|label/.test(c))
  if (hasDate) return 'line'
  if (hasName && cols.length === 2) return 'pie'
  return 'bar'
}

function SmartChart({ rows, columns }) {
  const [chartType, setChartType] = useState(() => detectChartType(columns))
  if (!rows || rows.length === 0) return null
  const numericCols = columns.filter(c => typeof rows[0][c] === 'number')
  const labelCol = columns.find(c => typeof rows[0][c] === 'string') || columns[0]
  if (numericCols.length === 0) return null
  const data = rows.slice(0, 20).map(r => ({
    name: String(r[labelCol]).slice(0, 15),
    ...numericCols.reduce((acc, c) => ({ ...acc, [c]: r[c] }), {})
  }))
  return (
    <div className="mt-4">
      <div className="flex gap-2 mb-3">
        {['bar', 'line', 'pie'].map(t => (
          <button key={t} onClick={() => setChartType(t)}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all capitalize ${chartType === t ? 'gradient-bg text-white' : 'glass text-secondary glass-hover'}`}>
            {t}
          </button>
        ))}
      </div>
      <div className="glass rounded-xl p-4" style={{ height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'bar' ? (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#0d1427', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }} />
              {numericCols.map((c, i) => <Bar key={c} dataKey={c} fill={COLORS[i % COLORS.length]} radius={[3, 3, 0, 0]} />)}
            </BarChart>
          ) : chartType === 'line' ? (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#0d1427', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }} />
              {numericCols.map((c, i) => <Line key={c} type="monotone" dataKey={c} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />)}
            </LineChart>
          ) : (
            <PieChart>
              <Pie data={data} dataKey={numericCols[0]} nameKey="name" cx="50%" cy="50%" outerRadius={90}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#0d1427', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }} />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function ResultTable({ rows, columns }) {
  const [page, setPage] = useState(0)
  const perPage = 10
  const total = rows.length
  const slice = rows.slice(page * perPage, (page + 1) * perPage)
  const exportCSV = () => {
    const headers = columns.join(',')
    const body = rows.map(r => columns.map(c => JSON.stringify(r[c] ?? '')).join(',')).join('\n')
    const blob = new Blob([headers + '\n' + body], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'results.csv'; a.click()
  }
  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-muted-custom">{total} rows</span>
        <button onClick={exportCSV} className="flex items-center gap-1 text-xs glass px-2 py-1 rounded-lg text-secondary glass-hover">
          <Download size={12} /> Export CSV
        </button>
      </div>
      <div className="glass rounded-xl overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-glass">
              {columns.map(c => <th key={c} className="text-left py-2 px-3 font-mono text-muted-custom whitespace-nowrap">{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {slice.map((row, i) => (
              <tr key={i} className="border-b border-glass/50 hover:bg-white/5 transition-colors">
                {columns.map(c => (
                  <td key={c} className="py-2 px-3 text-secondary whitespace-nowrap max-w-40 overflow-hidden text-ellipsis">
                    {row[c] === null || row[c] === undefined ? <span className="text-muted-custom">null</span> : String(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total > perPage && (
        <div className="flex items-center justify-between mt-2 text-xs text-secondary">
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="glass px-3 py-1 rounded-lg glass-hover disabled:opacity-40">Prev</button>
          <span>Page {page + 1} / {Math.ceil(total / perPage)}</span>
          <button disabled={(page + 1) * perPage >= total} onClick={() => setPage(p => p + 1)} className="glass px-3 py-1 rounded-lg glass-hover disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  )
}

// ── Inline SQL execution result after clicking ▶ Execute ──────────────────────
function InlineExecResult({ result }) {
  if (!result) return null
  if (!result.success) {
    return (
      <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
        className="mt-3 glass rounded-xl p-3 border border-red-500/20 flex items-start gap-2">
        <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
        <p className="text-red-400 text-xs">{result.error}</p>
      </motion.div>
    )
  }
  const data = result.data || {}
  const isDML = data.type === 'dml'
  return (
    <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
      className="mt-3 glass rounded-xl p-3 border border-green-500/20">
      <div className="flex items-center gap-2 mb-2">
        <CheckCircle size={14} className="text-green-400" />
        <span className="text-green-400 text-xs font-medium">
          {isDML
            ? `✓ Executed — ${data.rows_affected ?? data.row_count} row(s) affected`
            : `✓ ${data.row_count} row(s) returned in ${data.execution_time_ms?.toFixed(0)}ms`}
        </span>
      </div>
      {!isDML && data.rows?.length > 0 && (
        <>
          <ResultTable rows={data.rows} columns={data.columns} />
          <SmartChart rows={data.rows} columns={data.columns} />
        </>
      )}
    </motion.div>
  )
}

// ── SQL Block with Copy + ▶ Execute buttons ───────────────────────────────────
function SQLBlock({ sql }) {
  const [open, setOpen] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [execResult, setExecResult] = useState(null)
  const [showConfirm, setShowConfirm] = useState(false)

  const copySQL = () => navigator.clipboard.writeText(sql || '')

  const doExecute = async () => {
    setExecuting(true)
    setExecResult(null)
    try {
      const res = await callMCPTool('execute_sql_query', { sql })
      setExecResult(res.data)
    } catch (err) {
      setExecResult({ success: false, error: err.response?.data?.detail || 'Execution failed.' })
    } finally {
      setExecuting(false)
    }
  }

  const handleExecuteClick = () => {
    if (isDestructive(sql)) {
      setShowConfirm(true)
    } else {
      doExecute()
    }
  }

  return (
    <div className="glass rounded-2xl p-4">
      <ConfirmModal
        isOpen={showConfirm}
        sql={sql}
        onConfirm={() => { setShowConfirm(false); doExecute() }}
        onCancel={() => setShowConfirm(false)}
      />
      <div className="flex items-center justify-between mb-2">
        <button onClick={() => setOpen(o => !o)} className="flex items-center gap-2 text-sm font-medium text-blue-400">
          <Database size={14} /> Generated SQL {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        <div className="flex items-center gap-2">
          <button onClick={copySQL} className="flex items-center gap-1 text-xs glass px-2 py-1 rounded-lg text-secondary glass-hover">
            <Copy size={12} /> Copy
          </button>
          <button
            onClick={handleExecuteClick}
            disabled={executing}
            className={`flex items-center gap-1 text-xs px-3 py-1 rounded-lg font-medium hover:opacity-90 transition-all disabled:opacity-60 ${isDestructive(sql) ? 'bg-red-500/70 hover:bg-red-500 text-white border border-red-500/50' : 'gradient-bg text-white'}`}
          >
            {executing
              ? <><span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" /> Running…</>
              : <><Play size={11} fill="white" /> {isDestructive(sql) ? '⚠ Execute' : 'Execute'}</>
            }
          </button>
        </div>
      </div>
      {open && <pre className="code-block text-xs mt-2">{sql}</pre>}
      <InlineExecResult result={execResult} />
    </div>
  )
}

// ── Full AI response message ──────────────────────────────────────────────────
function AIMessage({ msg }) {
  const explanation = useTypingEffect(msg.explanation, 10)
  const [optOpen, setOptOpen] = useState(false)

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <div className="w-8 h-8 gradient-bg rounded-xl flex items-center justify-center shrink-0">
        <Sparkles size={14} className="text-white" />
      </div>
      <div className="flex-1 space-y-3">
        {msg.error ? (
          <div className="glass rounded-2xl p-4 border border-red-500/20">
            <p className="text-red-400 text-sm">{msg.error}</p>
          </div>
        ) : (
          <>
            {/* SQL Block with ▶ Execute */}
            {msg.sql && <SQLBlock sql={msg.sql} />}

            {/* Auto-executed results from the AI query flow */}
            {msg.query_type === 'dml' ? (
              <div className="glass rounded-2xl p-4 border border-green-500/20">
                <div className="flex items-center gap-2">
                  <CheckCircle size={16} className="text-green-400" />
                  <p className="text-green-400 text-sm font-medium">
                    {msg.rows_affected ?? msg.row_count} row(s) affected successfully
                  </p>
                </div>
              </div>
            ) : msg.rows?.length > 0 ? (
              <div className="glass rounded-2xl p-4">
                <p className="text-sm font-medium text-primary mb-1">
                  Results <span className="text-muted-custom font-normal">({msg.row_count} rows • {msg.execution_time_ms?.toFixed(0)}ms)</span>
                </p>
                <ResultTable rows={msg.rows} columns={msg.columns} />
                <SmartChart rows={msg.rows} columns={msg.columns} />
              </div>
            ) : msg.sql ? (
              <div className="glass rounded-2xl p-4">
                <p className="text-secondary text-sm">No rows returned.</p>
              </div>
            ) : null}

            {/* Plain English explanation */}
            {msg.explanation && (
              <div className="glass rounded-2xl p-4 border border-green-500/10">
                <p className="text-xs text-muted-custom mb-1 flex items-center gap-1"><Sparkles size={11} /> Plain English</p>
                <p className="text-sm text-primary leading-relaxed">
                  {explanation}
                  {explanation.length < msg.explanation.length && <span className="typing-cursor" />}
                </p>
              </div>
            )}

            {/* Optimisation tip */}
            {msg.optimization_suggestion && (
              <div className="glass rounded-2xl p-4 border border-yellow-500/10">
                <button onClick={() => setOptOpen(o => !o)} className="flex items-center gap-2 text-xs text-yellow-400 w-full">
                  <BarChart2 size={12} /> Optimisation Tip {optOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
                {optOpen && <p className="text-xs text-secondary mt-2 leading-relaxed">{msg.optimization_suggestion}</p>}
              </div>
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}

// ── Main Chat Page ────────────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [inputMode, setInputMode] = useState('nl')   // 'nl' | 'sql'
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [tableOpts, setTableOpts] = useState([])
  const [selectedTable, setSelectedTable] = useState('')
  const [confirmModal, setConfirmModal] = useState({ open: false, sql: '', pendingAction: null })
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { getTables().then(r => setTableOpts(r.data.tables || [])).catch(() => {}) }, [])

  const showConfirmFor = useCallback((sql, action) => {
    setConfirmModal({ open: true, sql, pendingAction: action })
  }, [])

  const handleModalConfirm = () => {
    const { pendingAction } = confirmModal
    setConfirmModal({ open: false, sql: '', pendingAction: null })
    if (pendingAction) pendingAction()
  }

  const handleModalCancel = () => {
    setConfirmModal({ open: false, sql: '', pendingAction: null })
  }

  // ── Natural Language mode: AI converts to SQL then executes ──
  const _doSendNL = async (question) => {
    setMessages(m => [...m, { role: 'user', content: question }])
    setLoading(true)
    try {
      const res = await runQuery(question, selectedTable || null)
      setMessages(m => [...m, { role: 'ai', ...res.data }])
    } catch (err) {
      setMessages(m => [...m, { role: 'ai', error: err.response?.data?.detail || 'Something went wrong.' }])
    } finally { setLoading(false) }
  }

  const sendNL = () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput('')
    // For NL mode we let the backend decide; we intercept destructive queries
    // by peeking at keywords in the question itself before sending
    const destKeywords = /\b(delete|drop|truncate|remove|clear all|wipe)\b/i
    if (destKeywords.test(question)) {
      showConfirmFor(
        `[AI will generate SQL for]: "${question}"\n\nCommon destructive operations include DELETE, DROP, TRUNCATE.`,
        () => _doSendNL(question)
      )
    } else {
      _doSendNL(question)
    }
  }

  // ── SQL mode: execute raw SQL directly via MCP tool ──────────
  const _doSendSQL = async (sql) => {
    setMessages(m => [...m, { role: 'user', content: sql, isSql: true }])
    setLoading(true)
    try {
      const res = await callMCPTool('execute_sql_query', { sql })
      const d = res.data
      if (!d.success) {
        setMessages(m => [...m, { role: 'ai', error: d.error }])
      } else {
        setMessages(m => [...m, {
          role: 'ai',
          sql,
          rows: d.data?.rows || [],
          row_count: d.data?.row_count ?? 0,
          rows_affected: d.data?.rows_affected,
          columns: d.data?.columns || [],
          execution_time_ms: d.data?.execution_time_ms,
          truncated: d.data?.truncated,
          query_type: d.data?.type || 'select',
          explanation: '',
          optimization_suggestion: '',
        }])
      }
    } catch (err) {
      setMessages(m => [...m, { role: 'ai', error: err.response?.data?.detail || 'Execution failed.' }])
    } finally { setLoading(false) }
  }

  const sendSQL = () => {
    if (!input.trim() || loading) return
    const sql = input.trim()
    setInput('')
    if (isDestructive(sql)) {
      showConfirmFor(sql, () => _doSendSQL(sql))
    } else {
      _doSendSQL(sql)
    }
  }

  const send = () => inputMode === 'sql' ? sendSQL() : sendNL()
  const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }

  const suggestions = inputMode === 'nl'
    ? ['Show me the top 10 records', 'Count rows by category', 'What is the average value?', 'Insert a new row into the table']
    : ['SELECT * FROM my_table LIMIT 10', "INSERT INTO my_table (col1) VALUES ('value')", 'SELECT COUNT(*) FROM my_table', 'SELECT * FROM my_table WHERE id = 1']

  return (
    <div className="min-h-screen bg-primary flex flex-col">
      {/* Double-confirm modal */}
      <ConfirmModal
        isOpen={confirmModal.open}
        sql={confirmModal.sql}
        onConfirm={handleModalConfirm}
        onCancel={handleModalCancel}
      />
      {/* Header */}
      <div className="glass border-b border-glass px-6 py-4 flex items-center gap-4 shrink-0">
        <Link to="/dashboard" className="glass glass-hover p-2 rounded-xl">
          <ArrowLeft size={18} className="text-secondary" />
        </Link>
        <div className="flex-1">
          <h1 className="font-bold text-primary">Chat Query</h1>
          <p className="text-xs text-secondary">Groq LLaMA 3 → MCP Tools → PostgreSQL</p>
        </div>
        {tableOpts.length > 0 && inputMode === 'nl' && (
          <select value={selectedTable} onChange={e => setSelectedTable(e.target.value)}
            className="glass text-sm text-secondary px-3 py-2 rounded-xl focus:outline-none">
            <option value="">All tables</option>
            {tableOpts.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-4xl mx-auto w-full">
        {messages.length === 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-12">
            <div className="w-16 h-16 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Sparkles size={28} className="text-white" />
            </div>
            <h2 className="text-xl font-bold text-primary mb-2">
              {inputMode === 'nl' ? 'Ask anything about your data' : 'Run SQL directly'}
            </h2>
            <p className="text-secondary text-sm max-w-sm mx-auto mb-8">
              {inputMode === 'nl'
                ? 'Type in plain English. AI generates SQL, executes it through MCP tools, and explains the results.'
                : 'Write any SQL query. It runs securely through the MCP safety gate before execution.'}
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              {suggestions.map(q => (
                <button key={q} onClick={() => setInput(q)}
                  className="glass px-4 py-2 rounded-xl text-sm text-secondary glass-hover text-left">
                  {q}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        <AnimatePresence>
          {messages.map((msg, i) =>
            msg.role === 'user' ? (
              <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
                <div className={`rounded-2xl rounded-tr-sm px-4 py-3 max-w-xl text-sm ${msg.isSql ? 'glass border border-blue-500/20' : 'gradient-bg text-white'}`}>
                  {msg.isSql
                    ? <pre className="font-mono text-xs text-blue-400 whitespace-pre-wrap">{msg.content}</pre>
                    : msg.content}
                </div>
              </motion.div>
            ) : (
              <AIMessage key={i} msg={msg} />
            )
          )}
        </AnimatePresence>

        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
            <div className="w-8 h-8 gradient-bg rounded-xl flex items-center justify-center shrink-0">
              <Sparkles size={14} className="text-white" />
            </div>
            <div className="glass rounded-2xl px-5 py-4 flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </motion.div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input bar */}
      <div className="glass border-t border-glass p-4 shrink-0">
        <div className="max-w-4xl mx-auto space-y-2">
          {/* Mode toggle */}
          <div className="flex gap-1 w-fit">
            <button
              onClick={() => setInputMode('nl')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${inputMode === 'nl' ? 'gradient-bg text-white' : 'glass text-secondary glass-hover'}`}
            >
              <MessageSquare size={12} /> Natural Language
            </button>
            <button
              onClick={() => setInputMode('sql')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${inputMode === 'sql' ? 'gradient-bg text-white' : 'glass text-secondary glass-hover'}`}
            >
              <Code2 size={12} /> Raw SQL
            </button>
          </div>

          {/* Input */}
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder={inputMode === 'nl'
                ? 'Ask a question… e.g. "Insert a row with name Alice and age 30"'
                : 'Type SQL… e.g. INSERT INTO users (name, age) VALUES (\'Alice\', 30)'}
              rows={inputMode === 'sql' ? 3 : 1}
              className={`flex-1 glass rounded-xl px-4 py-3 text-primary placeholder:text-muted-custom focus:outline-none resize-none text-sm ${inputMode === 'sql' ? 'font-mono text-blue-300' : ''}`}
              style={{ minHeight: inputMode === 'sql' ? 72 : 48, maxHeight: 160 }}
            />
            <button
              onClick={send}
              disabled={!input.trim() || loading}
              className="gradient-bg text-white px-4 rounded-xl flex items-center justify-center hover:opacity-90 transition-all disabled:opacity-40 hover:scale-105 shrink-0"
            >
              {inputMode === 'sql' ? <Play size={18} fill="white" /> : <Send size={18} />}
            </button>
          </div>

          {inputMode === 'sql' && (
            <p className="text-xs text-muted-custom flex items-center gap-1">
              <AlertCircle size={11} />
              Queries run through the MCP safety gate — DROP, TRUNCATE, DELETE without WHERE are blocked.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
