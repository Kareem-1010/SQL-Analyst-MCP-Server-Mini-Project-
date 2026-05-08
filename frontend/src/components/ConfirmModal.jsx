import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, X, ShieldAlert, Check } from 'lucide-react'

/**
 * ConfirmModal — double-confirmation dialog for destructive SQL operations.
 *
 * Props:
 *   isOpen    {boolean}  — whether the modal is visible
 *   sql       {string}   — the SQL string to preview
 *   onConfirm {function} — called when user double-confirms
 *   onCancel  {function} — called when user cancels
 */
export default function ConfirmModal({ isOpen, sql, onConfirm, onCancel }) {
  const [step, setStep] = useState(1)       // 1 = first warning, 2 = final confirm
  const [countdown, setCountdown] = useState(3)
  const [canProceed, setCanProceed] = useState(false)

  // Reset when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep(1)
      setCountdown(3)
      setCanProceed(false)
    }
  }, [isOpen])

  // Countdown timer for step 2
  useEffect(() => {
    if (step !== 2) return
    setCountdown(3)
    setCanProceed(false)
    const interval = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) {
          clearInterval(interval)
          setCanProceed(true)
          return 0
        }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [step])

  const handleFirstConfirm = () => setStep(2)
  const handleFinalConfirm = () => {
    if (canProceed) onConfirm()
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)' }}
        onClick={(e) => { if (e.target === e.currentTarget) onCancel() }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 20 }}
          transition={{ type: 'spring', stiffness: 300, damping: 24 }}
          className="glass rounded-3xl p-6 w-full max-w-lg border border-red-500/30 shadow-2xl"
        >
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                step === 1 ? 'bg-yellow-500/20' : 'bg-red-500/20'
              }`}>
                {step === 1
                  ? <AlertTriangle size={20} className="text-yellow-400" />
                  : <ShieldAlert size={20} className="text-red-400" />
                }
              </div>
              <div>
                <h3 className={`font-bold text-base ${step === 1 ? 'text-yellow-300' : 'text-red-300'}`}>
                  {step === 1 ? 'Destructive Query Warning' : 'Are you absolutely sure?'}
                </h3>
                <p className="text-xs text-secondary">
                  {step === 1 ? 'Step 1 of 2 — Please review' : 'Step 2 of 2 — Final confirmation'}
                </p>
              </div>
            </div>
            <button
              onClick={onCancel}
              className="text-secondary hover:text-primary transition-colors p-1 rounded-lg glass glass-hover"
            >
              <X size={16} />
            </button>
          </div>

          {/* SQL Preview */}
          <div className="glass rounded-xl p-3 mb-4 border border-red-500/10">
            <p className="text-xs text-muted-custom mb-1 font-mono">SQL to be executed:</p>
            <pre className="text-xs text-red-300 font-mono whitespace-pre-wrap break-all leading-relaxed max-h-32 overflow-y-auto">
              {sql}
            </pre>
          </div>

          {/* Step 1 Warning Banner */}
          {step === 1 && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-2 glass rounded-xl p-3 border border-yellow-500/20 mb-4"
            >
              <AlertTriangle size={14} className="text-yellow-400 shrink-0 mt-0.5" />
              <p className="text-sm text-yellow-300 leading-relaxed">
                This query will <strong>modify or delete data</strong> in your database.
                This action <strong>cannot be undone</strong>. Make sure you have reviewed the SQL above carefully.
              </p>
            </motion.div>
          )}

          {/* Step 2 Final Warning */}
          {step === 2 && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-2 glass rounded-xl p-3 border border-red-500/20 mb-4"
            >
              <ShieldAlert size={14} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-sm text-red-300 leading-relaxed">
                <strong>This is your final warning.</strong> Executing this query may permanently alter
                or destroy data. There is no undo. The button will activate in {countdown > 0 ? `${countdown}s` : 'a moment'}.
              </p>
            </motion.div>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-2">
            <button
              onClick={onCancel}
              className="flex-1 glass rounded-xl py-2.5 text-sm font-medium text-secondary glass-hover transition-all"
            >
              Cancel
            </button>

            {step === 1 ? (
              <button
                onClick={handleFirstConfirm}
                className="flex-1 bg-yellow-500/20 border border-yellow-500/40 hover:bg-yellow-500/30 text-yellow-300 rounded-xl py-2.5 text-sm font-semibold transition-all flex items-center justify-center gap-2"
              >
                <AlertTriangle size={14} />
                I understand — Continue
              </button>
            ) : (
              <button
                onClick={handleFinalConfirm}
                disabled={!canProceed}
                className={`flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
                  canProceed
                    ? 'bg-red-500/80 hover:bg-red-500 text-white border border-red-500'
                    : 'glass text-muted-custom cursor-not-allowed border border-red-500/20'
                }`}
              >
                {canProceed ? (
                  <><Check size={14} /> Execute Query</>
                ) : (
                  <><span className="w-4 h-4 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
                  Please wait ({countdown}s)…</>
                )}
              </button>
            )}
          </div>

          {/* Step indicators */}
          <div className="flex justify-center gap-1.5 mt-4">
            {[1, 2].map(s => (
              <div
                key={s}
                className={`w-2 h-2 rounded-full transition-all ${
                  s === step
                    ? (step === 1 ? 'bg-yellow-400 w-4' : 'bg-red-400 w-4')
                    : s < step ? 'bg-yellow-400/40' : 'bg-white/10'
                }`}
              />
            ))}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
