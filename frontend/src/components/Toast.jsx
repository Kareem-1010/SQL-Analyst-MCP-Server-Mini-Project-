import { useState, useEffect, createContext, useContext, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, AlertCircle, Info, X, AlertTriangle } from 'lucide-react'

// ── Toast Context ─────────────────────────────────────────────────────────────
const ToastContext = createContext(null)
export const useToast = () => useContext(ToastContext)

const ICONS = {
  success: <CheckCircle size={16} className="text-green-400" />,
  error:   <AlertCircle size={16} className="text-red-400" />,
  info:    <Info size={16} className="text-blue-400" />,
  warning: <AlertTriangle size={16} className="text-yellow-400" />,
}

const BORDERS = {
  success: 'border-green-500/30',
  error:   'border-red-500/30',
  info:    'border-blue-500/30',
  warning: 'border-yellow-500/30',
}

function Toast({ id, type = 'info', message, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(id), 4500)
    return () => clearTimeout(t)
  }, [id, onDismiss])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      className={`flex items-start gap-3 glass rounded-xl px-4 py-3 shadow-xl border ${BORDERS[type]} min-w-72 max-w-sm`}
    >
      <span className="mt-0.5 shrink-0">{ICONS[type]}</span>
      <p className="text-sm text-primary flex-1 leading-relaxed">{message}</p>
      <button
        onClick={() => onDismiss(id)}
        className="text-muted-custom hover:text-primary transition-colors shrink-0 mt-0.5"
      >
        <X size={14} />
      </button>
    </motion.div>
  )
}

// ── Provider ─────────────────────────────────────────────────────────────────
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id))
  }, [])

  const toast = useCallback(({ type = 'info', message }) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t.slice(-4), { id, type, message }])
  }, [])

  // Convenience helpers
  toast.success = (msg) => toast({ type: 'success', message: msg })
  toast.error   = (msg) => toast({ type: 'error',   message: msg })
  toast.info    = (msg) => toast({ type: 'info',    message: msg })
  toast.warning = (msg) => toast({ type: 'warning', message: msg })

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {/* Portal-like fixed overlay */}
      <div className="fixed bottom-6 right-6 z-[999] flex flex-col gap-3 items-end">
        <AnimatePresence mode="popLayout">
          {toasts.map((t) => (
            <Toast key={t.id} {...t} onDismiss={dismiss} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
