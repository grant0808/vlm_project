import React, { useState, useRef, useEffect } from 'react'
import { useChatStore } from '../store/useChatStore'
import { Send, Image, FileText, UploadCloud, Loader2, ArrowRight } from 'lucide-react'

export const Chat: React.FC = () => {
  const { messages, isStreaming, sendMessage, uploadFile, currentSessionId } = useChatStore()
  const [input, setInput] = useState('')
  const [selectedImage, setSelectedImage] = useState<string | null>(null) // Base64 encoding for VLM
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto scroll to bottom when new message arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() && !selectedImage) return

    const text = input
    const img = selectedImage
    
    setInput('')
    setSelectedImage(null)

    await sendMessage(text, img)
  }

  // Handle Document Upload (PDF, TXT for RAG)
  const handleDocumentChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadStatus('Uploading file for indexing...')
    try {
      await uploadFile(file)
      setUploadStatus('File uploaded! Vector indexing started in the background.')
      setTimeout(() => setUploadStatus(null), 5000)
    } catch (err) {
      setUploadStatus('Error uploading file.')
      setTimeout(() => setUploadStatus(null), 4000)
    }
  }

  // Handle Image Upload (For VLM Input)
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onloadend = () => {
      setSelectedImage(reader.result as string)
    }
    reader.readAsDataURL(file)
  }

  if (!currentSessionId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-dark-bg">
        <div className="max-w-md space-y-4">
          <UploadCloud className="w-16 h-16 text-brand-500 mx-auto animate-bounce" />
          <h2 className="text-2xl font-outfit font-extrabold text-white">No Active Session</h2>
          <p className="text-sm text-dark-textMuted">
            Create a new cognitive workspace from the sidebar to start interacting with Qwen2-VL, testing RAG/TAG/CAG pipelines.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 h-screen flex flex-col bg-dark-bg relative">
      {/* Background radial glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-brand-600/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-indigo-600/5 rounded-full blur-3xl pointer-events-none" />

      {/* Upload status banner */}
      {uploadStatus && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-20 py-2 px-6 rounded-full glass-panel border border-brand-500/30 text-xs text-brand-300 font-semibold flex items-center space-x-2 shadow-lg animate-in fade-in slide-in-from-top-4 duration-300">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>{uploadStatus}</span>
        </div>
      )}

      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 max-w-xl mx-auto">
            <div className="p-4 bg-brand-600/10 border border-brand-500/20 rounded-2xl">
              <span className="text-xs font-bold text-brand-400 uppercase tracking-widest">Cognitive Intelligence Platform</span>
            </div>
            <h3 className="text-3xl font-outfit font-black text-white">How can we assist your workflow today?</h3>
            <p className="text-sm text-dark-textMuted leading-relaxed">
              Upload a document (PDF, TXT) to index into Chroma DB for RAG, activate TAG to run analytical Pandas code, or utilize Redis memory caches for speed optimized CAG.
            </p>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-200`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl p-5 border text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-brand-600 border-brand-500 text-white shadow-lg shadow-brand-500/10 rounded-br-none'
                      : 'bg-dark-card border-dark-border text-gray-200 rounded-bl-none'
                  }`}
                >
                  <div className="font-bold text-[10px] uppercase tracking-wider mb-1.5 opacity-60">
                    {msg.role === 'user' ? 'You (Human)' : 'Qwen2-VL Agent'}
                  </div>
                  <div className="whitespace-pre-wrap font-sans font-normal">
                    {msg.content || (
                      <span className="flex items-center space-x-2 text-dark-textMuted">
                        <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
                        <span>Thinking...</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Tray & Attachment Previews */}
      <div className="p-6 max-w-4xl w-full mx-auto z-10">
        <form onSubmit={handleSend} className="space-y-3">
          {/* Image preview before upload */}
          {selectedImage && (
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-dark-card border border-dark-border w-fit animate-in zoom-in-95 duration-150">
              <img src={selectedImage} alt="Attachment Preview" className="h-14 w-14 object-cover rounded-lg" />
              <div>
                <div className="text-xs font-semibold text-white">Visual Attachment Loaded</div>
                <button
                  type="button"
                  onClick={() => setSelectedImage(null)}
                  className="text-[10px] text-rose-400 hover:underline mt-1 block"
                >
                  Remove Attachment
                </button>
              </div>
            </div>
          )}

          {/* Form Control */}
          <div className="flex items-center space-x-2 bg-dark-card border border-dark-border rounded-2xl p-2.5 focus-within:border-brand-500/60 transition-colors shadow-xl">
            {/* Document upload for RAG */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleDocumentChange}
              accept=".pdf,.txt,.md"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2.5 rounded-xl hover:bg-dark-border text-dark-textMuted hover:text-white transition-colors"
              title="Upload PDF/Text for RAG Indexing"
            >
              <FileText className="w-5 h-5" />
            </button>

            {/* Image upload for VLM */}
            <input
              type="file"
              ref={imageInputRef}
              onChange={handleImageChange}
              accept="image/*"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => imageInputRef.current?.click()}
              className="p-2.5 rounded-xl hover:bg-dark-border text-dark-textMuted hover:text-white transition-colors"
              title="Upload Image for Vision-Language Processing"
            >
              <Image className="w-5 h-5" />
            </button>

            {/* Main Text Input */}
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question, analyze table metrics, or upload documents..."
              className="flex-1 bg-transparent border-none focus:outline-none text-sm text-white placeholder-gray-600 px-2"
              disabled={isStreaming}
            />

            {/* Submit Button */}
            <button
              type="submit"
              disabled={(!input.trim() && !selectedImage) || isStreaming}
              className="p-3 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-dark-border disabled:text-gray-700 text-white transition-all transform active:scale-95"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
