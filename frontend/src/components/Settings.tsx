import React from 'react'
import { useChatStore } from '../store/useChatStore'
import { X, Sliders, Database, Layers, Zap, Terminal } from 'lucide-react'

interface SettingsProps {
  isOpen: boolean
  onClose: () => void
}

export const Settings: React.FC<SettingsProps> = ({ isOpen, onClose }) => {
  const { activeSettings, updateSessionSettings } = useChatStore()

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md">
      <div className="w-[540px] glass-panel border border-dark-border rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-6 border-b border-dark-border flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Sliders className="w-5 h-5 text-brand-400" />
            <h2 className="font-outfit font-bold text-lg text-white">Cognitive Agent Settings</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-dark-card text-dark-textMuted hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Toggles */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-brand-400 uppercase tracking-widest">Pipeline Activations</h3>
            
            {/* RAG Toggle */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-dark-card/50 border border-dark-border/40">
              <div className="flex items-start space-x-3.5">
                <Database className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-white">RAG (Retrieval-Augmented)</h4>
                  <p className="text-xs text-dark-textMuted">Fetch chunked vector embeddings from Chroma DB.</p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={activeSettings.rag_enabled}
                  onChange={(e) => updateSessionSettings({ rag_enabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-dark-border rounded-full peer peer-focus:ring-2 peer-focus:ring-brand-500/20 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-gray-300 after:border-gray-300 after:border after:rounded-full after:height-5 after:width-5 after:transition-all peer-checked:bg-brand-600"></div>
              </label>
            </div>

            {/* TAG Toggle */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-dark-card/50 border border-dark-border/40">
              <div className="flex items-start space-x-3.5">
                <Layers className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-white">TAG (Table & Tool Augmented)</h4>
                  <p className="text-xs text-dark-textMuted">Enable SQL/Pandas sandbox execution and API connectors.</p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={activeSettings.tag_enabled}
                  onChange={(e) => updateSessionSettings({ tag_enabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-dark-border rounded-full peer peer-focus:ring-2 peer-focus:ring-brand-500/20 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-gray-300 after:border-gray-300 after:border after:rounded-full after:height-5 after:width-5 after:transition-all peer-checked:bg-brand-600"></div>
              </label>
            </div>

            {/* CAG Toggle */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-dark-card/50 border border-dark-border/40">
              <div className="flex items-start space-x-3.5">
                <Zap className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-white">CAG (Cache-Augmented)</h4>
                  <p className="text-xs text-dark-textMuted">Leverage Redis memory caching for instant low-cost responses.</p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={activeSettings.cag_enabled}
                  onChange={(e) => updateSessionSettings({ cag_enabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-dark-border rounded-full peer peer-focus:ring-2 peer-focus:ring-brand-500/20 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-gray-300 after:border-gray-300 after:border after:rounded-full after:height-5 after:width-5 after:transition-all peer-checked:bg-brand-600"></div>
              </label>
            </div>
          </div>

          {/* System Prompt */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-brand-400" />
              <label className="text-xs font-bold text-brand-400 uppercase tracking-widest">Cognitive System Prompt</label>
            </div>
            <textarea
              rows={4}
              value={activeSettings.system_prompt || ''}
              onChange={(e) => updateSessionSettings({ system_prompt: e.target.value })}
              placeholder="Provide context rules or system prompts..."
              className="w-full p-4 rounded-xl bg-dark-card border border-dark-border focus:border-brand-500 focus:outline-none text-sm text-white placeholder-gray-600 resize-none transition-colors"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-border bg-dark-card/30 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-all"
          >
            Apply Settings
          </button>
        </div>
      </div>
    </div>
  )
}
