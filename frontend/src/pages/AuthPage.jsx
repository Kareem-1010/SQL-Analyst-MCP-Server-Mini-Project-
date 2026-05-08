import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Database, Eye, EyeOff, ArrowRight, Sparkles, User, Lock, AlertCircle, CheckCircle } from 'lucide-react'
import { loginUser, registerUser } from '../services/api'

export default function AuthPage() {
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!username.trim() || !password) {
      setError('Username and password are required.')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      let res
      if (mode === 'login') {
        res = await loginUser(username.trim(), password)
      } else {
        res = await registerUser(username.trim(), password, displayName.trim())
        setSuccess(`Account created! Your private database "${res.data.db_name}" is ready.`)
        await new Promise(r => setTimeout(r, 1200))
      }

      const { access_token, username: uname, db_name } = res.data
      localStorage.setItem('sql_analyst_token', access_token)
      localStorage.setItem('sql_analyst_user', JSON.stringify({ username: uname, db_name }))
      navigate('/dashboard')
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map(d => d.msg).join(', ')
          : 'Something went wrong. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="animated-gradient min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background glows */}
      <div className="absolute top-1/4 left-1/4 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="glass rounded-3xl p-8 w-full max-w-md border border-glass glow-blue"
      >
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 gradient-bg rounded-xl flex items-center justify-center">
            <Database size={20} className="text-white" />
          </div>
          <div>
            <h1 className="font-bold text-primary">SQL Analyst</h1>
            <p className="text-xs text-secondary">MCP Server</p>
          </div>
        </div>

        {/* Toggle */}
        <div className="flex glass rounded-xl p-1 mb-6">
          {['login', 'signup'].map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(''); setSuccess('') }}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
                mode === m ? 'gradient-bg text-white' : 'text-secondary hover:text-primary'
              }`}
            >
              {m === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.form
            key={mode}
            initial={{ opacity: 0, x: mode === 'login' ? -20 : 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onSubmit={handleSubmit}
            className="space-y-4"
          >
            {/* Display name (signup only) */}
            {mode === 'signup' && (
              <div>
                <label className="text-sm text-secondary mb-1 block">Display Name (optional)</label>
                <div className="relative">
                  <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-custom" />
                  <input
                    type="text"
                    value={displayName}
                    onChange={e => setDisplayName(e.target.value)}
                    placeholder="Your display name"
                    className="w-full glass rounded-xl px-4 py-3 pl-9 text-primary placeholder:text-muted-custom focus:outline-none focus:border-blue-500/50 transition-colors"
                  />
                </div>
              </div>
            )}

            {/* Username */}
            <div>
              <label className="text-sm text-secondary mb-1 block">Username</label>
              <div className="relative">
                <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-custom" />
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="your_username"
                  autoComplete="username"
                  className="w-full glass rounded-xl px-4 py-3 pl-9 text-primary placeholder:text-muted-custom focus:outline-none focus:border-blue-500/50 transition-colors"
                />
              </div>
              {mode === 'signup' && (
                <p className="text-xs text-muted-custom mt-1">
                  Your private database <code className="text-blue-400">db_{'{username}'}</code> will be created automatically.
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="text-sm text-secondary mb-1 block">Password</label>
              <div className="relative">
                <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-custom" />
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  className="w-full glass rounded-xl px-4 py-3 pl-9 pr-12 text-primary placeholder:text-muted-custom focus:outline-none focus:border-blue-500/50 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary hover:text-primary transition-colors"
                >
                  {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-2 glass rounded-xl p-3 border border-red-500/20"
              >
                <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
                <p className="text-red-400 text-sm">{error}</p>
              </motion.div>
            )}

            {/* Success */}
            {success && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-2 glass rounded-xl p-3 border border-green-500/20"
              >
                <CheckCircle size={14} className="text-green-400 shrink-0 mt-0.5" />
                <p className="text-green-400 text-sm">{success}</p>
              </motion.div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full gradient-bg text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 hover:opacity-90 transition-all hover:scale-[1.02] disabled:opacity-60 disabled:scale-100"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {mode === 'login' ? 'Signing in…' : 'Creating account & database…'}
                </span>
              ) : (
                <>
                  <Sparkles size={18} />
                  {mode === 'login' ? 'Sign In' : 'Create Account'}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </motion.form>
        </AnimatePresence>

        <p className="text-center text-xs text-muted-custom mt-6">
          {mode === 'signup'
            ? 'Each account gets its own isolated PostgreSQL database.'
            : 'Your data is isolated — only you can see your tables.'}
        </p>
      </motion.div>
    </div>
  )
}
