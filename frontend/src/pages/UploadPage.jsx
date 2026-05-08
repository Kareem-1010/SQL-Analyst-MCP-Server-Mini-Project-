import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, ArrowLeft, Table2, ChevronRight } from 'lucide-react'
import { uploadFile } from '../services/api'

export default function UploadPage() {
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(0)

  const onDrop = useCallback(async (accepted) => {
    if (!accepted.length) return
    const file = accepted[0]
    setError('')
    setResult(null)
    setUploading(true)
    setProgress(0)

    // Fake progress animation
    const interval = setInterval(() => setProgress(p => Math.min(p + 15, 85)), 200)

    try {
      const res = await uploadFile(file)
      clearInterval(interval)
      setProgress(100)
      setTimeout(() => setUploading(false), 400)
      setResult(res.data)
    } catch (err) {
      clearInterval(interval)
      setUploading(false)
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'], 'application/vnd.ms-excel': ['.xls'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    maxFiles: 1,
    maxSize: 52428800,
  })

  return (
    <div className="min-h-screen bg-primary p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link to="/dashboard" className="glass glass-hover p-2 rounded-xl">
            <ArrowLeft size={18} className="text-secondary" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-primary">Upload Data</h1>
            <p className="text-secondary text-sm">Import CSV or Excel files into PostgreSQL</p>
          </div>
        </div>

        {/* Dropzone */}
        <motion.div
          {...getRootProps()}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          className={`glass rounded-3xl p-12 text-center cursor-pointer transition-all border-2 border-dashed ${
            isDragActive && !isDragReject ? 'border-blue-500/60 bg-blue-500/5' :
            isDragReject ? 'border-red-500/60 bg-red-500/5' :
            'border-glass hover:border-blue-500/30'
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-4">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${
              isDragActive ? 'gradient-bg' : 'glass'
            }`}>
              {isDragReject
                ? <AlertCircle size={28} className="text-red-400" />
                : <Upload size={28} className={isDragActive ? 'text-white' : 'text-blue-400'} />
              }
            </div>
            <div>
              <p className="text-lg font-semibold text-primary">
                {isDragActive ? (isDragReject ? 'File type not supported' : 'Drop it here!') : 'Drag & drop your file'}
              </p>
              <p className="text-secondary text-sm mt-1">
                or <span className="text-blue-400 underline cursor-pointer">browse files</span>
              </p>
              <p className="text-muted-custom text-xs mt-3">CSV, XLS, XLSX • Max 50MB</p>
            </div>
          </div>
        </motion.div>

        {/* Upload progress */}
        <AnimatePresence>
          {uploading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-6 glass rounded-2xl p-6"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                <p className="text-primary text-sm font-medium">Processing file…</p>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                  className="h-full gradient-bg rounded-full"
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              <p className="text-xs text-muted-custom mt-2">{progress}%</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error */}
        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 glass rounded-2xl p-4 border border-red-500/20">
            <p className="text-red-400 text-sm flex items-center gap-2"><AlertCircle size={16} />{error}</p>
          </motion.div>
        )}

        {/* Result */}
        <AnimatePresence>
          {result && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-6 space-y-4">
              <div className="glass rounded-2xl p-6 border border-green-500/20">
                <div className="flex items-center gap-3 mb-4">
                  <CheckCircle size={20} className="text-green-400" />
                  <p className="font-semibold text-primary">Upload successful!</p>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: 'Table Name', value: result.table_name, style: 'font-mono text-blue-400' },
                    { label: 'Rows', value: result.row_count?.toLocaleString() },
                    { label: 'Columns', value: result.column_count },
                  ].map(({ label, value, style }) => (
                    <div key={label} className="glass rounded-xl p-3">
                      <p className="text-xs text-muted-custom mb-1">{label}</p>
                      <p className={`font-bold text-primary ${style || ''}`}>{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Schema */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-semibold text-primary mb-4 flex items-center gap-2">
                  <Table2 size={16} className="text-blue-400" /> Schema
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-muted-custom text-xs border-b border-glass">
                        <th className="text-left py-2 pr-4">Column</th>
                        <th className="text-left py-2 pr-4">Type</th>
                        <th className="text-left py-2">Nullable</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.columns?.map((c, i) => (
                        <tr key={i} className="border-b border-glass/50">
                          <td className="py-2 pr-4 font-mono text-blue-400">{c.name}</td>
                          <td className="py-2 pr-4 text-secondary">{c.type}</td>
                          <td className="py-2 text-muted-custom">{c.nullable ? 'yes' : 'no'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Preview rows */}
              {result.preview?.length > 0 && (
                <div className="glass rounded-2xl p-6">
                  <h3 className="font-semibold text-primary mb-4">Preview (first 10 rows)</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-muted-custom text-xs border-b border-glass">
                          {Object.keys(result.preview[0]).map(k => (
                            <th key={k} className="text-left py-2 pr-4 font-mono">{k}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.preview.map((row, i) => (
                          <tr key={i} className="border-b border-glass/50">
                            {Object.values(row).map((v, j) => (
                              <td key={j} className="py-2 pr-4 text-secondary text-xs truncate max-w-32">
                                {v === null || v === undefined ? <span className="text-muted-custom">null</span> : String(v)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <Link
                to="/chat"
                className="flex items-center justify-center gap-2 glass gradient-bg text-white py-3 rounded-xl font-medium hover:opacity-90 transition-all"
              >
                Start Querying <ChevronRight size={18} />
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
