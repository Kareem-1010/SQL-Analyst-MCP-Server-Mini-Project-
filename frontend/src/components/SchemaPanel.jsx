import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Database, ChevronDown, ChevronRight, Columns, Loader2, Search } from 'lucide-react'
import { getTables, describeTable } from '../services/api'

export default function SchemaPanel({ onInsertColumn }) {
  const [tables, setTables] = useState([])
  const [expanded, setExpanded] = useState({})
  const [schemas, setSchemas] = useState({})
  const [loading, setLoading] = useState(true)
  const [loadingTable, setLoadingTable] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    getTables()
      .then((r) => setTables(r.data.tables || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const toggleTable = async (table) => {
    const isOpen = expanded[table]
    setExpanded((e) => ({ ...e, [table]: !isOpen }))
    if (!isOpen && !schemas[table]) {
      setLoadingTable(table)
      try {
        const r = await describeTable(table)
        setSchemas((s) => ({ ...s, [table]: r.data.columns || [] }))
      } catch (_) {}
      finally { setLoadingTable(null) }
    }
  }

  const filteredTables = tables.filter((t) =>
    t.toLowerCase().includes(search.toLowerCase())
  )

  const TYPE_COLOR = {
    integer: 'text-blue-400', bigint: 'text-blue-400', smallint: 'text-blue-400',
    numeric: 'text-cyan-400', real: 'text-cyan-400', 'double precision': 'text-cyan-400',
    text: 'text-green-400', varchar: 'text-green-400', character: 'text-green-400',
    boolean: 'text-yellow-400', date: 'text-purple-400', timestamp: 'text-purple-400',
  }
  const getTypeColor = (type) => {
    const key = Object.keys(TYPE_COLOR).find((k) => type?.toLowerCase().includes(k))
    return key ? TYPE_COLOR[key] : 'text-secondary'
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-3 border-b border-glass">
        <p className="text-xs font-semibold text-muted-custom uppercase tracking-wider mb-2 flex items-center gap-2">
          <Database size={12} /> Schema Explorer
        </p>
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-custom" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tables…"
            className="w-full glass rounded-lg pl-7 pr-3 py-1.5 text-xs text-primary placeholder:text-muted-custom focus:outline-none"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={16} className="animate-spin text-muted-custom" />
          </div>
        ) : filteredTables.length === 0 ? (
          <div className="px-3 py-6 text-center">
            <p className="text-xs text-muted-custom">
              {tables.length === 0 ? (
                <>No tables yet.<br /><Link to="/upload" className="text-blue-400 hover:underline">Upload a file</Link></>
              ) : 'No matching tables'}
            </p>
          </div>
        ) : (
          filteredTables.map((table) => (
            <div key={table}>
              <button
                onClick={() => toggleTable(table)}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/5 transition-colors text-left"
              >
                {expanded[table]
                  ? <ChevronDown size={12} className="text-muted-custom shrink-0" />
                  : <ChevronRight size={12} className="text-muted-custom shrink-0" />
                }
                <Database size={12} className="text-blue-400 shrink-0" />
                <span className="text-xs font-mono text-primary truncate">{table}</span>
                {loadingTable === table && (
                  <Loader2 size={10} className="animate-spin text-muted-custom ml-auto shrink-0" />
                )}
              </button>

              <AnimatePresence>
                {expanded[table] && schemas[table] && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    {schemas[table].map((col) => (
                      <button
                        key={col.column_name}
                        onClick={() => onInsertColumn?.(col.column_name, table)}
                        title={`Click to insert "${col.column_name}" into query`}
                        className="w-full flex items-center gap-2 pl-8 pr-3 py-1.5 hover:bg-blue-500/5 transition-colors text-left group"
                      >
                        <Columns size={10} className="text-muted-custom shrink-0" />
                        <span className="text-xs font-mono text-secondary group-hover:text-primary transition-colors truncate flex-1">
                          {col.column_name}
                        </span>
                        <span className={`text-xs font-mono ${getTypeColor(col.data_type)} shrink-0`}>
                          {col.data_type?.replace('character varying', 'varchar').replace('double precision', 'float').slice(0, 10)}
                        </span>
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
