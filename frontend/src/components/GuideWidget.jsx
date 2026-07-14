import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Compass, X, PaperPlaneRight } from '@phosphor-icons/react';
import { apiGet, apiPost } from '../lib/api';

// The Village Guide — a greeter/navigator, not a chatbot. Renders only when
// the server has the guide configured (GET /api/guide/status), so nothing
// appears in prod until the ANTHROPIC_API_KEY is set.
export default function GuideWidget({ user }) {
  const [enabled, setEnabled] = useState(false);
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [thread, setThread] = useState([]); // {who: 'me'|'guide', text, route?}
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const endRef = useRef(null);

  useEffect(() => {
    apiGet('/api/guide/status').then(d => setEnabled(!!d.enabled)).catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thread, open]);

  if (!enabled) return null;

  const firstName = (user?.name || '').split(' ')[0];
  const greeting = user?.intent === 'family'
    ? `Welcome to the village${firstName ? ', ' + firstName : ''}. I can show you how to follow your young person's growth — ask me anything about the app.`
    : `Welcome${firstName ? ', ' + firstName : ''} — I'm your guide to the village. Ask me how to do anything here.`;

  const ask = async () => {
    const q = question.trim();
    if (!q || busy) return;
    setThread(t => [...t, { who: 'me', text: q }]);
    setQuestion('');
    setBusy(true);
    try {
      const res = await apiPost('/api/guide/ask', { question: q, page: location.pathname });
      setThread(t => [...t, { who: 'guide', text: res.answer, route: res.route }]);
    } catch (e) {
      setThread(t => [...t, { who: 'guide', text: e.message || 'I couldn\'t answer just now — please try again.' }]);
    }
    setBusy(false);
  };

  return (
    <>
      {/* Floating launcher */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-40 w-12 h-12 rounded-full bg-[#D4AF37] text-[#050814] shadow-lg shadow-black/40 flex items-center justify-center hover:bg-[#F3E5AB] transition-colors"
          title="Ask the Village Guide"
          data-testid="guide-launcher"
        >
          <Compass size={24} weight="duotone" />
        </button>
      )}

      {/* Panel */}
      {open && (
        <div className="fixed bottom-5 right-5 z-40 w-[min(92vw,360px)] rounded-lg border border-[#D4AF37]/30 bg-[#0F172A] shadow-2xl shadow-black/60 flex flex-col overflow-hidden" data-testid="guide-panel">
          <div className="flex items-center justify-between px-4 py-3 bg-[#050814] border-b border-[#1E293B]">
            <span className="flex items-center gap-2 text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              <Compass size={16} weight="duotone" className="text-[#D4AF37]" /> Village Guide
            </span>
            <button onClick={() => setOpen(false)} className="text-[#94A3B8] hover:text-[#F8FAFC]" data-testid="guide-close">
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 max-h-[50vh] overflow-y-auto p-3 space-y-2">
            <div className="text-xs text-[#94A3B8] bg-[#050814] border border-[#1E293B] rounded-md p-2.5">{greeting}</div>
            {thread.map((m, i) => (
              <div key={i} className={m.who === 'me' ? 'text-right' : ''}>
                <div className={`inline-block text-left text-xs rounded-md p-2.5 max-w-[90%] ${
                  m.who === 'me'
                    ? 'bg-[#D4AF37]/15 text-[#F3E5AB] border border-[#D4AF37]/25'
                    : 'bg-[#050814] text-[#E2E8F0] border border-[#1E293B]'
                }`}>
                  <span className="whitespace-pre-wrap">{m.text}</span>
                  {m.route && (
                    <button
                      onClick={() => { navigate(m.route); setOpen(false); }}
                      className="block mt-2 text-[11px] text-[#D4AF37] hover:underline"
                      data-testid="guide-take-me"
                    >
                      Take me there →
                    </button>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="text-[10px] text-[#475569] italic">The guide is thinking…</div>}
            <div ref={endRef} />
          </div>

          <div className="flex gap-2 p-3 border-t border-[#1E293B]">
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && ask()}
              placeholder="How do I…?"
              maxLength={500}
              className="flex-1 px-3 py-2 rounded bg-[#050814] border border-[#1E293B] text-xs text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50"
              data-testid="guide-input"
            />
            <button onClick={ask} disabled={busy || !question.trim()}
              className="px-3 rounded bg-[#D4AF37]/15 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/25 disabled:opacity-40"
              data-testid="guide-send">
              <PaperPlaneRight size={14} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
