import React, { useState, useEffect } from 'react'
import { useChatStore } from './store/useChatStore'
import { Sidebar } from './components/Sidebar'
import { Chat } from './components/Chat'
import { Settings } from './components/Settings'
import { Cpu, Lock, Mail } from 'lucide-react'

const App: React.FC = () => {
  const { isAuthenticated, login, register, fetchSessions } = useChatStore()
  const [isRegistering, setIsRegistering] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  useEffect(() => {
    if (isAuthenticated) {
      fetchSessions()
    }
  }, [isAuthenticated])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      if (isRegistering) {
        await register(email, password)
      } else {
        await login(email, password)
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please try again.')
    }
  }

  // Render Authentication Page if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-dark-bg relative overflow-hidden">
        {/* Colorful background glows */}
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-brand-900/10 blur-[150px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full bg-indigo-900/10 blur-[150px]" />

        <div className="w-[420px] p-8 rounded-2xl glass-panel shadow-2xl border border-dark-border z-10 animate-in fade-in zoom-in-95 duration-300">
          <div className="text-center space-y-3 mb-8">
            <div className="inline-flex bg-brand-600 p-3 rounded-2xl text-white shadow-lg shadow-brand-500/20">
              <Cpu className="w-8 h-8" />
            </div>
            <h1 className="font-outfit font-black text-2xl tracking-tight text-white">VLM Cognitive Workspace</h1>
            <p className="text-xs text-dark-textMuted uppercase tracking-wider font-bold">
              High-Performance AI Pipeline Gateway
            </p>
          </div>

          {error && (
            <div className="p-4 mb-5 rounded-xl bg-rose-950/20 border border-rose-500/30 text-rose-300 text-xs text-center font-medium animate-shake">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-brand-400 uppercase tracking-widest block">Email Address</label>
              <div className="flex items-center space-x-2 bg-dark-card border border-dark-border rounded-xl p-3 focus-within:border-brand-500/60 transition-colors">
                <Mail className="w-4 h-4 text-gray-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="bg-transparent border-none focus:outline-none text-sm text-white placeholder-gray-600 flex-1"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-bold text-brand-400 uppercase tracking-widest block">Password</label>
              <div className="flex items-center space-x-2 bg-dark-card border border-dark-border rounded-xl p-3 focus-within:border-brand-500/60 transition-colors">
                <Lock className="w-4 h-4 text-gray-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="bg-transparent border-none focus:outline-none text-sm text-white placeholder-gray-600 flex-1"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-3.5 mt-2 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold text-sm transition-all transform active:scale-95 shadow-lg shadow-brand-500/25"
            >
              {isRegistering ? 'Create Account' : 'Authenticate Session'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => setIsRegistering(!isRegistering)}
              className="text-xs text-dark-textMuted hover:text-white transition-colors"
            >
              {isRegistering
                ? 'Already registered? Sign In instead'
                : "Don't have an account? Sign Up now"}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Render Main Application Workspace
  return (
    <div className="min-h-screen w-full flex bg-dark-bg text-gray-100 overflow-hidden font-sans">
      <Sidebar onOpenSettings={() => setIsSettingsOpen(true)} />
      <Chat />
      
      {/* Overlay Pipeline Settings Modal */}
      <Settings isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  )
}

export default App
