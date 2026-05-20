'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAIStats } from '../../lib/api';
import type { AIStats } from '../../lib/api';
import { Loader2, Zap, Clock, Gauge, TrendingUp, Cpu } from 'lucide-react';

const PROVIDER_COLOR: Record<string, string> = {
  auto: '#F59E0B',
  groq: '#25D366',
  openrouter: '#128C7E',
};

function Card({ children, delay = 0, className = '' }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <div
      className={`rounded-xl p-5 border animate-fade-in ${className}`.trim()}
      style={{
        background: '#FFFFFF',
        borderColor: '#B8C1C8',
        animationDelay: `${delay}ms`,
        boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
      }}
    >
      {children}
    </div>
  );
}

export default function AIStatsPage() {
  const router = useRouter();
  const [stats, setStats] = useState<AIStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!localStorage.getItem('wacrm_token')) return router.push('/');
    getAIStats()
      .then(setStats)
      .catch((err) => {
        if (err.message.includes('401') || err.message.includes('403')) {
          localStorage.removeItem('wacrm_token');
          router.push('/');
        } else {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading)
    return <div className="flex items-center justify-center h-64" style={{ color: '#3B4A54' }}>Loading…</div>;
  if (error) return <div className="text-red-600 text-sm">{error}</div>;
  if (!stats) return null;

  const provider = stats.current_provider || stats.provider || '—';
  const providerColor = PROVIDER_COLOR[provider] || '#3B4A54';
  const groqUsed = stats.groq_requests || 0;
  const groqDayLimit = stats.groq_free_tier_daily || 14400;
  const groqRemaining = Math.max(0, groqDayLimit - groqUsed);
  const groqPct = Math.min(100, Math.round((groqUsed / groqDayLimit) * 100));

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: '#0B141A' }}>AI Stats</h1>
        <p className="text-sm mt-0.5" style={{ color: '#3B4A54' }}>Groq and OpenRouter usage overview</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Provider */}
        <Card delay={0}>
          <div className="flex items-center gap-2 mb-3">
            <Cpu size={15} style={{ color: '#128C7E' }} />
            <p className="text-xs uppercase tracking-wider font-medium" style={{ color: '#3B4A54' }}>Current Provider</p>
          </div>
          <p className="text-xl font-bold" style={{ color: providerColor }}>{provider}</p>
          {stats.current_provider && (
            <p className="text-xs mt-1" style={{ color: '#3B4A54' }}>{stats.provider !== stats.current_provider ? `(was ${stats.provider})` : 'Active now'}</p>
          )}
        </Card>

        {/* After Hours */}
        <Card delay={30}>
          <div className="flex items-center gap-2 mb-3">
            <Clock size={15} style={{ color: '#F59E0B' }} />
            <p className="text-xs uppercase tracking-wider font-medium" style={{ color: '#3B4A54' }}>After-Hours Mode</p>
          </div>
          <p className="text-xl font-bold" style={{ color: stats.after_hours ? '#F59E0B' : '#25D366' }}>
            {stats.after_hours ? '🌙 Active' : '☀️ Inactive'}
          </p>
          <p className="text-xs mt-1" style={{ color: '#3B4A54' }}>{stats.after_hours ? 'AI handling out-of-hours messages' : 'Business hours — AI on standby'}</p>
        </Card>

        {/* Groq Requests */}
        <Card delay={60}>
          <div className="flex items-center gap-2 mb-3">
            <Zap size={15} style={{ color: '#25D366' }} />
            <p className="text-xs uppercase tracking-wider font-medium" style={{ color: '#3B4A54' }}>Groq Requests Today</p>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#0B141A' }}>{groqUsed.toLocaleString()}</p>
          <p className="text-xs mt-1" style={{ color: '#3B4A54' }}>of {groqDayLimit.toLocaleString()} /day free tier</p>
        </Card>

        {/* OpenRouter Requests */}
        <Card delay={90}>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={15} style={{ color: '#128C7E' }} />
            <p className="text-xs uppercase tracking-wider font-medium" style={{ color: '#3B4A54' }}>OpenRouter Requests</p>
          </div>
          <p className="text-2xl font-bold" style={{ color: '#0B141A' }}>{stats.openrouter_requests?.toLocaleString() ?? 0}</p>
          <p className="text-xs mt-1" style={{ color: '#3B4A54' }}>Today</p>
        </Card>

        {/* Free tier progress */}
        <Card delay={120} className="sm:col-span-2 lg:col-span-1">
          <div className="flex items-center gap-2 mb-3">
            <Gauge size={15} style={{ color: '#128C7E' }} />
            <p className="text-xs uppercase tracking-wider font-medium" style={{ color: '#3B4A54' }}>Groq Tier Usage</p>
          </div>
          <div className="flex items-baseline gap-2">
            <p className="text-2xl font-bold" style={{ color: groqPct > 80 ? '#EF4444' : groqPct > 50 ? '#F59E0B' : '#25D366' }}>{groqPct}%</p>
            <p className="text-xs" style={{ color: '#3B4A54' }}>{groqRemaining.toLocaleString()} remaining</p>
          </div>
          <div className="mt-2 w-full h-2 rounded-full overflow-hidden" style={{ background: '#EAEDEE' }}>
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${groqPct}%`,
                background: groqPct > 80 ? '#EF4444' : groqPct > 50 ? '#F59E0B' : '#25D366',
              }}
            />
          </div>
        </Card>
      </div>

      {/* Top Intents */}
      {stats.top_intents && stats.top_intents.length > 0 && (
        <Card delay={180} className="sm:col-span-2 lg:col-span-3">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: '#0B141A' }}>
            <Cpu size={14} style={{ color: '#128C7E' }} /> Top Detected Intents
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {stats.top_intents.map(({ intent, count }) => (
              <div
                key={intent}
                className="px-3 py-2 rounded-lg text-center text-xs"
                style={{ background: '#25D36610', border: '1px solid #25D36620' }}
              >
                <p style={{ color: '#3B4A54' }}>{intent}</p>
                <p className="font-bold mt-0.5" style={{ color: '#0B141A' }}>{count}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {(!stats.top_intents || stats.top_intents.length === 0) && (
        <p className="text-sm text-center py-4" style={{ color: '#3B4A54' }}>No intent data yet.</p>
      )}
    </div>
  );
}
