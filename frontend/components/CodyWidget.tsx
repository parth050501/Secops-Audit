'use client';
import { useState, useRef, useEffect } from 'react';
import { askCody } from '@/lib/api';
import { MessageCircle, X, Send, Sparkles } from 'lucide-react';

type Msg = { role: 'user' | 'assistant'; content: string; error?: boolean };

export default function CodyWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([
    { role: 'assistant', content: "Hi, I'm Cody. I can help you understand your compliance posture — your open findings, which controls they affect, and what to prioritize. I base every answer on your own data, and I won't declare you compliant (that's your auditor's call). What would you like to know?" },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, open]);

  const suggestions = [
    "What should I fix first?",
    "Which controls have open findings?",
    "Summarize my compliance posture",
  ];

  const send = async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput('');
    const history = messages.filter(m => !m.error).map(m => ({ role: m.role, content: m.content }));
    setMessages(m => [...m, { role: 'user', content: msg }]);
    setLoading(true);
    try {
      const r = await askCody(msg, history);
      if (r.data.answer) {
        setMessages(m => [...m, { role: 'assistant', content: r.data.answer }]);
      } else if (r.data.configured === false) {
        setMessages(m => [...m, { role: 'assistant', content: "I'm not fully set up yet — the assistant service hasn't been connected. Please check back soon.", error: true }]);
      } else {
        setMessages(m => [...m, { role: 'assistant', content: "I couldn't produce an answer just now. Please try again.", error: true }]);
      }
    } catch (e) {
      setMessages(m => [...m, { role: 'assistant', content: "I'm temporarily unavailable. Please try again in a moment.", error: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Launcher */}
      {!open && (
        <button onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-teal-600 hover:bg-teal-700 text-white shadow-lg flex items-center justify-center transition-all"
          aria-label="Open Cody assistant">
          <MessageCircle className="w-6 h-6" />
        </button>
      )}

      {/* Panel */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] h-[560px] max-h-[calc(100vh-3rem)] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-teal-600 to-teal-700 text-white px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <p className="font-semibold text-sm leading-tight">Cody</p>
                <p className="text-[11px] opacity-80 leading-tight">Compliance assistant</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="opacity-80 hover:opacity-100"><X className="w-5 h-5" /></button>
          </div>

          {/* Disclaimer */}
          <div className="bg-amber-50 border-b border-amber-100 px-4 py-2 text-[11px] text-amber-800">
            Cody explains your findings and posture. It doesn't determine compliance — that's your auditor's call.
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  m.role === 'user' ? 'bg-teal-600 text-white rounded-br-sm'
                  : m.error ? 'bg-red-50 text-red-700 border border-red-100 rounded-bl-sm'
                  : 'bg-slate-100 text-slate-800 rounded-bl-sm'}`}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 text-slate-400 px-3 py-2 rounded-2xl rounded-bl-sm text-sm italic">Cody is thinking…</div>
              </div>
            )}
            {messages.length <= 1 && !loading && (
              <div className="flex flex-wrap gap-2 pt-2">
                {suggestions.map(s => (
                  <button key={s} onClick={() => send(s)}
                    className="text-xs px-3 py-1.5 bg-white border border-slate-200 rounded-full text-teal-700 hover:bg-teal-50 hover:border-teal-300">
                    {s}
                  </button>
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div className="border-t border-slate-100 p-3 flex gap-2">
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') send(); }}
              placeholder="Ask about your compliance posture…"
              className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm outline-none focus:border-teal-400" />
            <button onClick={() => send()} disabled={loading || !input.trim()}
              className="px-3 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white rounded-lg">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
