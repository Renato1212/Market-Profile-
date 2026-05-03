import { useEffect, useState, useRef } from 'react'
import { Send, Bot, RefreshCw } from 'lucide-react'
import { fetchTodayBriefing, sendChatMessage } from '../../lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export function AtlasBriefing() {
  const [briefing, setBriefing] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    fetchTodayBriefing()
      .then((r) => setBriefing(r.data.content))
      .catch(() => setBriefing(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="atlas-card h-32 animate-pulse" />

  return (
    <div className="atlas-card">
      <div className="flex items-center gap-2 mb-3">
        <Bot size={16} className="text-blue" />
        <span className="text-[11px] uppercase tracking-wider text-text-secondary">Today's Pre-Market Briefing</span>
        <button
          onClick={() => { setLoading(true); fetchTodayBriefing().then((r) => { setBriefing(r.data.content); setLoading(false) }) }}
          className="ml-auto text-text-secondary hover:text-text-primary"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      {briefing ? (
        <div>
          <div className={`text-sm text-text-primary leading-relaxed whitespace-pre-wrap font-mono text-xs overflow-hidden transition-all ${expanded ? '' : 'max-h-40'}`}>
            {briefing}
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-2 text-xs text-blue hover:underline"
          >
            {expanded ? 'Show less' : 'Show full briefing'}
          </button>
        </div>
      ) : (
        <p className="text-sm text-text-secondary">
          Briefing unavailable. Configure ANTHROPIC_API_KEY to enable AI analysis.
        </p>
      )}
    </div>
  )
}

export function AtlasChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const send = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await sendChatMessage(input, messages.slice(-6))
      setMessages([...newMessages, { role: 'assistant', content: res.data.response }])
    } catch {
      setMessages([...newMessages, { role: 'assistant', content: 'Sorry, AI service is unavailable. Please check configuration.' }])
    } finally {
      setLoading(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    }
  }

  return (
    <div className="atlas-card flex flex-col h-96">
      <div className="flex items-center gap-2 mb-3 pb-3 border-b border-border">
        <Bot size={16} className="text-blue" />
        <span className="text-[11px] uppercase tracking-wider text-text-secondary">Ask ATLAS</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.length === 0 && (
          <div className="text-center py-4">
            <p className="text-text-secondary text-sm">Ask about gap statistics, GEX regime, A Period patterns, or anything in the data.</p>
            <div className="mt-3 space-y-1.5">
              {[
                'Why is the market in short gamma right now?',
                'What did similar gap setups do historically?',
                'What are odds of trend day today?',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="block w-full text-left text-xs text-blue hover:text-text-primary px-3 py-1.5 rounded-lg border border-border hover:border-blue transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-blue/20 text-text-primary rounded-tr-sm'
                : 'bg-surface border border-border text-text-primary rounded-tl-sm'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 py-2">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-text-secondary animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="mt-3 pt-3 border-t border-border flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask ATLAS..."
          className="flex-1 bg-bg border border-border rounded-xl px-3 py-2 text-sm text-text-primary placeholder-text-secondary outline-none focus:border-blue transition-colors"
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="p-2 rounded-xl bg-blue text-bg disabled:opacity-40 transition-opacity"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
