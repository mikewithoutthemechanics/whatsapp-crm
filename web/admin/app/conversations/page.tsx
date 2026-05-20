'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  getActiveConversations,
  sendMessage,
  quickReply,
} from '../../lib/api';
import type { Conversation } from '../../lib/api';
import { Send, Loader2 } from 'lucide-react';

const QUICK_REPLIES = [
  { key: 'greeting', label: '👋 Greeting' },
  { key: 'thanks', label: '🙏 Thanks' },
  { key: 'pricing', label: '💰 Pricing' },
  { key: 'hours', label: '🕐 Hours' },
  { key: 'location', label: '📍 Location' },
  { key: 'follow_up', label: '🔁 Follow-up' },
  { key: 'goodbye', label: '👋 Goodbye' },
];

export default function ConversationsPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<{ from: 'contact' | 'me'; text: string }[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [quickLoading, setQuickLoading] = useState<string | null>(null);
  const [error, setError] = useState('');
  const msgsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!localStorage.getItem('wacrm_token')) return router.push('/');
    loadConversations();
  }, [router]);

  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversations = async () => {
    setLoading(true);
    try {
      const res = await getActiveConversations(25);
      setConversations(res.data);
      if (res.data.length > 0) setSelected(res.data[0]);
    } catch (err: unknown) {
      if (err instanceof Error && (err.message.includes('401') || err.message.includes('403'))) {
        localStorage.removeItem('wacrm_token');
        router.push('/');
      } else {
        console.error(err);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !selected) return;
    setMessages((m) => [...m, { from: 'me', text: input.trim() }]);
    const text = input.trim();
    setInput('');
    try {
      await sendMessage({ to: selected.contact.phone, content: text });
    } catch (err) {
      console.error(err);
    }
  };

  const handleQuickReply = async (replyKey: string) => {
    if (!selected) return;
    setQuickLoading(replyKey);
    try {
      await quickReply({ reply_key: replyKey, to: selected.contact.phone });
      const label = QUICK_REPLIES.find((q) => q.key === replyKey)?.label || replyKey;
      setMessages((m) => [...m, { from: 'me', text: `[Quick Reply] ${label}` }]);
    } catch (err) {
      console.error(err);
    } finally {
      setQuickLoading(null);
    }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64" style={{ color: '#3B4A54' }}>Loading…</div>;

  return (
    <div className="space-y-4 h-[calc(100vh-4rem)] flex flex-col">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: '#0B141A' }}>Conversations</h1>
        <p className="text-sm mt-0.5" style={{ color: '#3B4A54' }}>Live WhatsApp conversations</p>
      </div>

      <div
        className="flex flex-1 gap-0 rounded-xl border overflow-hidden"
        style={{ background: '#FFFFFF', borderColor: '#B8C1C8', boxShadow: '0 1px 4px rgba(0,0,0,0.1)' }}
      >
        {/* Left pane — conversation list */}
        <div
          className="w-full md:w-[30%] min-w-0 border-r flex flex-col"
          style={{ borderColor: '#B8C1C8' }}
        >
          <div className="p-4 border-b" style={{ borderColor: '#B8C1C8' }}>
            <p className="text-xs uppercase tracking-wider font-medium" style={{ color: '#3B4A54' }}>
              Active Conversations ({conversations.length})
            </p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {conversations.length === 0 && (
              <p className="p-4 text-sm" style={{ color: '#3B4A54' }}>No conversations yet.</p>
            )}
            {conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => {
                  setSelected(c);
                  setMessages([]);
                }}
                className="w-full text-left px-4 py-3 transition-all cursor-pointer border-none"
                style={{
                  borderBottom: '1px solid #EAEDEE',
                  background: selected?.id === c.id ? '#EAEDEE' : '#FFFFFF',
                }}
                onMouseEnter={(e) => { if (selected?.id !== c.id) (e.currentTarget as HTMLButtonElement).style.background = '#EEF0F2'; }}
                onMouseLeave={(e) => { if (selected?.id !== c.id) (e.currentTarget as HTMLButtonElement).style.background = '#FFFFFF'; }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-base shrink-0">💬</span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: '#0B141A' }}>{c.contact.name}</p>
                    <p className="text-xs mt-0.5 truncate" style={{ color: '#3B4A54' }}>{c.contact.phone}</p>
                  </div>
                  <span
                    className="ml-auto shrink-0 text-[10px] px-2 py-0.5 rounded-full uppercase font-semibold"
                    style={{
                      background: c.status === 'active' ? '#DCF8C620' : c.status === 'waiting' ? '#FFF3CD' : '#EAEDEE',
                      color: c.status === 'active' ? '#25D366' : c.status === 'waiting' ? '#B8860B' : '#3B4A54',
                    }}
                  >
                    {c.status}
                  </span>
                </div>
                {c.last_message && (
                  <p className="text-xs mt-1 truncate pl-6" style={{ color: '#3B4A54' }}>
                    {c.last_message.text}
                  </p>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Right pane — chat view */}
        <div className="flex-1 flex flex-col min-w-0" style={{ background: '#ECE5DD' }}>
          {selected ? (
            <>
              {/* Header */}
              <div className="px-5 py-3 border-b flex items-center gap-3" style={{ borderColor: '#B8C1C8', background: '#075E54' }}>
                <span className="text-xl">💬</span>
                <div>
                  <p className="text-sm font-semibold text-white">{selected.contact.name}</p>
                  <p className="text-xs" style={{ color: 'rgba(255,255,255,0.65)' }}>{selected.contact.phone}</p>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-5 space-y-3">
                <div className="text-center text-xs py-6" style={{ color: '#3B4A54' }}>
                  WhatsApp CRM SA — {selected.contact.name}
                </div>
                {messages.map((m, i) => (
                  <div
                    key={i}
                    className={`flex ${m.from === 'me' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className="max-w-[75%] px-3.5 py-2 rounded-2xl text-sm"
                      style={{
                        background: m.from === 'me' ? '#DCF8C6' : '#FFFFFF',
                        color: '#0B141A',
                        borderBottomRightRadius: m.from === 'me' ? '4px' : '16px',
                        borderBottomLeftRadius: m.from === 'me' ? '16px' : '4px',
                        boxShadow: '0 1px 1px rgba(0,0,0,0.06)',
                      }}
                    >
                      {m.text}
                    </div>
                  </div>
                ))}
                <div ref={msgsEndRef} />
              </div>

              {/* Quick replies */}
              <div className="px-4 pb-2 flex flex-wrap gap-1.5 pt-2" style={{ borderTop: '1px solid #B8C1C8', background: '#EAEDEE' }}>
                {QUICK_REPLIES.map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => handleQuickReply(key)}
                    disabled={quickLoading !== null}
                    className="text-[11px] px-2.5 py-1 rounded-full transition-all cursor-pointer disabled:opacity-30"
                    style={{ background: '#FFFFFF', color: '#075E54', border: '1px solid #B8C1C8' }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = '#DCF8C6'; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = '#FFFFFF'; }}
                  >
                    {quickLoading === key ? <Loader2 size={10} className="inline animate-spin" /> : label}
                  </button>
                ))}
              </div>

              {/* Input */}
              <div className="p-4 flex gap-2" style={{ background: '#EAEDEE', borderTop: '1px solid #B8C1C8' }}>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Type a message…"
                  className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
                  style={{ color: '#0B141A', background: '#FFFFFF', border: '1px solid #B8C1C8' }}
                  onFocus={(e) => (e.target.style.borderColor = '#25D366')}
                  onBlur={(e) => (e.target.style.borderColor = '#B8C1C8')}
                />
                <button
                  onClick={handleSend}
                  className="p-2.5 rounded-xl text-white cursor-pointer border-none transition-all"
                  style={{ background: '#25D366' }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#128C7E')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#25D366')}
                >
                  <Send size={18} />
                </button>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm" style={{ color: '#3B4A54' }}>
              Select a conversation to start chatting
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
