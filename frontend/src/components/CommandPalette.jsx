import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Search, X, Database, MessageSquare, Upload, History, BarChart2, Settings, Zap } from 'lucide-react'

const COMMANDS = [
  { id: 'dashboard', label: 'Go to Dashboard',    icon: <BarChart2 size={16} />,    path: '/dashboard', category: 'Navigate' },
  { id: 'upload',    label: 'Upload Data',         icon: <Upload size={16} />,       path: '/upload',    category: 'Navigate' },
  { id: 'chat',      label: 'Open Chat Query',     icon: <MessageSquare size={16} />,path: '/chat',      category: 'Navigate' },
  { id: 'visualize', label: 'Visualize Data',      icon: <Database size={16} />,     path: '/visualize', category: 'Navigate' },
  { id: 'history',   label: 'Query History',       icon: <History size={16} />,      path: '/history',   category: 'Navigate' },
  { id: 'nl-mode',   label: 'Switch to NL Mode',  icon: <Zap size={16} />,          action: 'nl',       category: 'Action' },
  { id: 'sql-mode',  label: 'Switch to SQL Mode',  icon: <Settings size={16} />,     action: 'sql',      category: 'Action' },
]

export default function CommandPalette({ isOpen, onClose, onAction }) {
  const [query, setQuery] = useState('')
  const [selectedIdx, setSelectedIdx] = useState(0)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  const filtered = COMMANDS.filter(
    (c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.category.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIdx(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  useEffect(() => {
    setSelectedIdx(0)
  }, [query])

  const execute = useCallback((cmd) => {
    onClose()
    if (cmd.path) navigate(cmd.path)
    if (cmd.action && onAction) onAction(cmd.action)
  }, [navigate, onClose, onAction])

  const onKey = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, filtered.length - 1)) }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, 0)) }
    if (e.key === 'Enter' && filtered[selectedIdx]) execute(filtered[selectedIdx])
    if (e.key === 'Escape') onClose()
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[900]"
          />
          {/* Palette */}
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            className="fixed top-1/4 left-1/2 -translate-x-1/2 w-full max-w-lg z-[901] px-4"
          >
            <div className="glass rounded-2xl overflow-hidden shadow-2xl border border-blue-500/20">
              {/* Search input */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-glass">
                <Search size={18} className="text-muted-custom shrink-0" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={onKey}
                  placeholder="Search commands…"
                  className="flex-1 bg-transparent text-primary placeholder:text-muted-custom focus:outline-none text-sm"
                />
                <button onClick={onClose} className="text-muted-custom hover:text-primary transition-colors">
                  <X size={16} />
                </button>
              </div>

              {/* Results */}
              <div className="py-2 max-h-80 overflow-y-auto">
                {filtered.length === 0 ? (
                  <p className="px-4 py-6 text-center text-sm text-muted-custom">No commands found</p>
                ) : (
                  filtered.map((cmd, i) => (
                    <button
                      key={cmd.id}
                      onClick={() => execute(cmd)}
                      onMouseEnter={() => setSelectedIdx(i)}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                        i === selectedIdx ? 'bg-blue-500/10 text-primary' : 'text-secondary'
                      }`}
                    >
                      <span className={i === selectedIdx ? 'text-blue-400' : 'text-muted-custom'}>
                        {cmd.icon}
                      </span>
                      <span className="text-sm flex-1">{cmd.label}</span>
                      <span className="text-xs text-muted-custom">{cmd.category}</span>
                    </button>
                  ))
                )}
              </div>

              <div className="px-4 py-2 border-t border-glass flex items-center gap-4 text-xs text-muted-custom">
                <span>↑↓ Navigate</span>
                <span>↵ Select</span>
                <span>Esc Close</span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
