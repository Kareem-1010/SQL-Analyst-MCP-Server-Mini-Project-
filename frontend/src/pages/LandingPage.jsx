import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Database, Zap, Shield, BarChart2, Brain, Upload,
  ArrowRight, Sparkles, Code2, Layers, Lock, Activity,
  ChevronRight, Star, GitBranch, Globe
} from 'lucide-react'

const features = [
  { icon: <Upload size={22} />,    title: 'CSV / Excel Ingestion',     desc: 'Drag & drop files. Auto-detect schema and load into per-user PostgreSQL instantly. Supports up to 50MB files.' },
  { icon: <Brain size={22} />,     title: 'Multi-Turn NL→SQL',         desc: 'Ask follow-up questions in plain English. Groq LLaMA 3 remembers conversation context across queries.' },
  { icon: <Shield size={22} />,    title: '14 MCP Security Tools',      desc: 'Every query validated through the MCP tool-chain. Destructive SQL requires double confirmation with countdown.' },
  { icon: <BarChart2 size={22} />, title: 'Interactive Visualizations', desc: 'Results auto-render as bar, line, pie, or scatter charts. Export to PNG. Switch views instantly.' },
  { icon: <Zap size={22} />,       title: 'Real-Time SSE Streaming',    desc: 'AI explanations stream token-by-token at 500+ tokens/sec using Groq inference. Zero perceived latency.' },
  { icon: <Database size={22} />,  title: 'Multi-Tenant Isolation',     desc: 'Every user gets their own PostgreSQL database. Zero data leakage. JWT-scoped DB routing.' },
  { icon: <Activity size={22} />,  title: 'Analytics Dashboard',        desc: 'Query volume trends, success rates, avg response time, and top queried tables — all in one view.' },
  { icon: <Lock size={22} />,      title: 'Rate Limiting',              desc: 'Token-bucket algorithm enforces 10 queries/minute per user for fair resource distribution.' },
  { icon: <Code2 size={22} />,     title: 'AI Insights Engine',         desc: 'After every query, get 3 AI-generated observations about patterns and anomalies in your data.' },
]

const techStack = [
  { label: 'FastAPI',      color: '#009688' },
  { label: 'Groq LLaMA 3', color: '#7c3aed' },
  { label: 'PostgreSQL',   color: '#336791' },
  { label: 'React 19',     color: '#61dafb' },
  { label: 'MCP Protocol', color: '#f59e0b' },
  { label: 'JWT Auth',     color: '#10b981' },
  { label: 'SSE Streaming',color: '#06b6d4' },
  { label: 'Recharts',     color: '#8b5cf6' },
]

const fadeUp = { hidden: { opacity: 0, y: 30 }, show: { opacity: 1, y: 0 } }
const stagger = { show: { transition: { staggerChildren: 0.08 } } }

const TerminalLine = ({ prompt, command, result, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, x: -10 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay, duration: 0.4 }}
    className="font-mono text-sm"
  >
    {prompt && <span className="text-blue-400">{prompt} </span>}
    {command && <span className="text-green-300">{command}</span>}
    {result && <div className="text-secondary mt-0.5 pl-2">{result}</div>}
  </motion.div>
)

export default function LandingPage() {
  return (
    <div className="animated-gradient min-h-screen overflow-hidden">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 glass border-b border-glass sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center">
            <Database size={16} className="text-white" />
          </div>
          <span className="font-bold text-lg text-primary">QueryMind AI</span>
          <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded-full border border-purple-500/30">Research v3.0</span>
        </div>
        <div className="hidden md:flex items-center gap-6 text-sm text-secondary">
          <a href="#features" className="hover:text-primary transition-colors">Features</a>
          <a href="#architecture" className="hover:text-primary transition-colors">Architecture</a>
          <a href="#stack" className="hover:text-primary transition-colors">Tech Stack</a>
        </div>
        <div className="flex gap-3">
          <Link to="/auth" className="text-secondary text-sm px-4 py-2 glass rounded-lg glass-hover">
            Sign In
          </Link>
          <Link to="/auth" className="text-sm px-4 py-2 gradient-bg rounded-lg text-white font-medium hover:opacity-90 transition-opacity flex items-center gap-1">
            Get Started <ChevronRight size={14} />
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex flex-col items-center text-center px-6 pt-24 pb-20 relative">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-3xl" />
          <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-purple-500/5 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 left-1/2 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl" />
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full mb-8 border border-blue-500/20"
        >
          <Sparkles size={14} className="text-blue-400" />
          <span className="text-sm text-secondary">Conference Edition • Groq LLaMA 3.3 70B • 500+ tokens/sec</span>
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.6 }}
          className="text-5xl md:text-7xl font-bold mb-6 max-w-4xl leading-tight"
        >
          Talk to your data.{' '}
          <span className="gradient-text">Instantly.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-xl text-secondary max-w-2xl mb-10 leading-relaxed"
        >
          QueryMind AI translates natural language to production-safe SQL, executes it through 14 MCP security tools,
          streams AI explanations in real-time, and renders interactive visualizations — all in seconds.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="flex flex-wrap gap-4 justify-center mb-16"
        >
          <Link
            to="/auth"
            className="flex items-center gap-2 px-8 py-3.5 gradient-bg rounded-xl text-white font-semibold text-lg hover:opacity-90 transition-all hover:scale-105 pulse-glow"
          >
            Start Analysing <ArrowRight size={20} />
          </Link>
          <a
            href="#architecture"
            className="flex items-center gap-2 px-8 py-3.5 glass rounded-xl text-primary font-semibold text-lg glass-hover"
          >
            View Architecture
          </a>
        </motion.div>

        {/* Live Demo Terminal */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="w-full max-w-3xl glass rounded-2xl overflow-hidden border border-blue-500/20 text-left shadow-2xl"
        >
          {/* Terminal header */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-glass bg-black/30">
            <div className="w-3 h-3 rounded-full bg-red-500/70" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
            <div className="w-3 h-3 rounded-full bg-green-500/70" />
            <span className="ml-3 text-xs text-muted-custom font-mono">QueryMind AI — Live Session</span>
            <div className="ml-auto flex items-center gap-1">
              <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
              <span className="text-xs text-green-400">Connected</span>
            </div>
          </div>
          <div className="p-6 space-y-4">
            <TerminalLine prompt="user@querymind:~$" command="query: What are the top 5 products by revenue last month?" delay={0.1} />
            <TerminalLine result="🔍 Generating SQL via Groq LLaMA 3.3 70B…" delay={0.5} />
            <TerminalLine
              result={<span className="text-blue-400">SELECT product_name, SUM(revenue) AS total_revenue<br/>FROM sales WHERE DATE_TRUNC('month', sale_date) = DATE_TRUNC('month', NOW() - INTERVAL '1 month')<br/>GROUP BY product_name ORDER BY total_revenue DESC LIMIT 5;</span>}
              delay={0.9}
            />
            <TerminalLine result="✅ Safety check passed • 14 MCP tools validated" delay={1.3} />
            <TerminalLine result="⚡ Executed in 48ms • 5 rows returned" delay={1.6} />
            <TerminalLine result={<span className="text-green-300">🤖 AI: This query identifies your highest-grossing products for last month. Widget Pro leads with $142,300 in revenue...</span>} delay={1.9} />
            <TerminalLine result="📊 Auto-rendering bar chart • 3 insights generated" delay={2.3} />
          </div>
        </motion.div>
      </section>

      {/* Architecture */}
      <section id="architecture" className="px-6 py-20 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl font-bold text-primary mb-4">System Architecture</h2>
          <p className="text-secondary max-w-xl mx-auto">
            A layered, security-first design built for research and production workloads.
          </p>
        </motion.div>

        {/* Architecture diagram */}
        <div className="glass rounded-3xl p-8 border border-blue-500/10">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
            {[
              { label: 'React 19\nFrontend', icon: <Globe size={20} />, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30' },
              { label: '→', arrow: true },
              { label: 'FastAPI\nBackend', icon: <Layers size={20} />, color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/30' },
              { label: '→', arrow: true },
              { label: 'MCP Tool\nOrchestrator', icon: <GitBranch size={20} />, color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/30' },
            ].map((item, i) => item.arrow ? (
              <div key={i} className="hidden md:flex justify-center text-muted-custom text-2xl">→</div>
            ) : (
              <div key={i} className={`glass rounded-2xl p-5 border ${item.bg} text-center`}>
                <div className={`${item.color} flex justify-center mb-2`}>{item.icon}</div>
                <p className="text-sm font-medium text-primary whitespace-pre-line">{item.label}</p>
              </div>
            ))}
          </div>
          <div className="flex justify-center mt-4">
            <div className="text-muted-custom text-sm">↓</div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
            {[
              { label: 'Groq LLaMA 3\nAI Engine', icon: <Brain size={20} />, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30' },
              { label: 'PostgreSQL\nUser DBs', icon: <Database size={20} />, color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30' },
              { label: 'JWT Auth\n+ Rate Limiter', icon: <Lock size={20} />, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
            ].map((item, i) => (
              <div key={i} className={`glass rounded-2xl p-5 border ${item.bg} text-center`}>
                <div className={`${item.color} flex justify-center mb-2`}>{item.icon}</div>
                <p className="text-sm font-medium text-primary whitespace-pre-line">{item.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 py-12 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl font-bold text-primary mb-4">Research-Grade Features</h2>
          <p className="text-secondary max-w-xl mx-auto">
            Every feature engineered for reliability, security, and developer experience.
          </p>
        </motion.div>
        <motion.div
          variants={stagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((f, i) => (
            <motion.div key={i} variants={fadeUp} className="glass rounded-2xl p-6 glass-hover">
              <div className="w-10 h-10 gradient-bg rounded-xl flex items-center justify-center text-white mb-4">
                {f.icon}
              </div>
              <h3 className="font-semibold text-primary mb-2">{f.title}</h3>
              <p className="text-secondary text-sm leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Tech Stack */}
      <section id="stack" className="px-6 py-16 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-10"
        >
          <h2 className="text-2xl font-bold text-primary mb-3">Built With</h2>
          <p className="text-secondary">Best-in-class technologies for AI-powered data analytics</p>
        </motion.div>
        <div className="flex flex-wrap gap-3 justify-center">
          {techStack.map((t) => (
            <motion.div
              key={t.label}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="glass px-5 py-2.5 rounded-full border border-glass glass-hover"
            >
              <span className="text-sm font-medium" style={{ color: t.color }}>{t.label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Stats bar */}
      <section className="px-6 py-10">
        <div className="max-w-4xl mx-auto glass rounded-3xl p-8 border border-purple-500/20">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { value: '14',    label: 'MCP Tools' },
              { value: '500+',  label: 'tokens/sec' },
              { value: '100%',  label: 'Data Isolated' },
              { value: '<50ms', label: 'Query Latency' },
            ].map((s) => (
              <div key={s.label}>
                <p className="text-3xl font-bold gradient-text">{s.value}</p>
                <p className="text-sm text-secondary mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 pb-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass rounded-3xl p-12 max-w-2xl mx-auto border border-purple-500/20"
        >
          <div className="w-14 h-14 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-6">
            <Sparkles size={26} className="text-white" />
          </div>
          <h2 className="text-3xl font-bold mb-4">Ready to query smarter?</h2>
          <p className="text-secondary mb-8 leading-relaxed">
            No SQL knowledge required. Upload your data, ask questions in plain English,
            and let AI do the heavy lifting.
          </p>
          <Link
            to="/auth"
            className="inline-flex items-center gap-2 px-8 py-3.5 gradient-bg rounded-xl text-white font-semibold hover:opacity-90 transition-all hover:scale-105"
          >
            Get Started Free <ArrowRight size={18} />
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-glass py-8 px-8">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 gradient-bg rounded-md flex items-center justify-center">
              <Database size={12} className="text-white" />
            </div>
            <span className="text-sm font-medium text-primary">QueryMind AI</span>
            <span className="text-xs text-muted-custom">v3.0 Research Edition</span>
          </div>
          <p className="text-muted-custom text-sm text-center">
            Built with FastAPI • Groq LLaMA 3 • PostgreSQL • React 19 • MCP Protocol
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-custom">
            <span>Multi-Tenant</span>
            <span>•</span>
            <span>JWT Secured</span>
            <span>•</span>
            <span>SSE Streaming</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
