import React from 'react'
import { useChatStore } from '../store/useChatStore'
import { MessageSquare, Plus, LogOut, Cpu, Settings as SettingsIcon } from 'lucide-react'

interface SidebarProps {
  onOpenSettings: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({ onOpenSettings }) => {
  const { sessions, currentSessionId, createSession, setCurrentSessionId, logout } = useChatStore()

  return (
    <aside className="w-80 h-screen glass-panel flex flex-col border-r border-dark-border z-10">
      {/* Header Logo */}
      <div className="p-6 border-b border-dark-border flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-brand-600 p-2 rounded-xl text-white shadow-lg shadow-brand-500/30 animate-pulse">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-outfit font-extrabold text-xl tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-white via-gray-200 to-gray-400">
              VLM Cognitive
            </h1>
            <p className="text-[10px] text-brand-400 uppercase tracking-widest font-bold font-sans">
              RAG • TAG • CAG Platform
            </p>
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-4">
        <button
          onClick={() => createSession()}
          className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-medium text-sm transition-all duration-300 transform hover:-translate-y-0.5 hover:shadow-lg hover:shadow-brand-500/25"
        >
          <Plus className="w-4 h-4" />
          <span>New Cognitive Session</span>
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        {sessions.map(session => (
          <button
            key={session.id}
            onClick={() => setCurrentSessionId(session.id)}
            className={`w-full flex items-center space-x-3 px-4 py-3.5 rounded-xl text-left text-sm transition-all duration-200 group ${
              currentSessionId === session.id
                ? 'bg-brand-600/10 border border-brand-500/30 text-white font-medium'
                : 'text-dark-textMuted hover:bg-dark-card hover:text-white border border-transparent'
            }`}
          >
            <MessageSquare className={`w-4 h-4 shrink-0 transition-colors ${
              currentSessionId === session.id ? 'text-brand-400' : 'text-gray-500 group-hover:text-gray-300'
            }`} />
            <span className="truncate flex-1">{session.title}</span>
          </button>
        ))}
      </div>

      {/* Footer / User controls */}
      <div className="p-4 border-t border-dark-border space-y-2">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium text-dark-textMuted hover:bg-dark-card hover:text-white transition-all"
        >
          <SettingsIcon className="w-4 h-4 text-gray-500" />
          <span>Pipeline Settings</span>
        </button>

        <button
          onClick={logout}
          className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium text-rose-400 hover:bg-rose-950/20 hover:text-rose-300 transition-all"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
