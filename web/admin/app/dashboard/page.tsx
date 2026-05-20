'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getDashboardSummary } from '../../lib/api';
import type { DashboardSummary } from '../../lib/api';

const cardClass =
  'rounded-xl p-5 border transition-all hover:border-white/12 animate-fade-in';

function StatCard({
  label,
  value,
  sub,
  accent,
  delay = 0,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
  delay?: number;
}) {
  return (
    <div
      className={cardClass}
      style={{
        background: 'rgba(255,255,255,0.02)',
        borderColor: 'rgba(255,255,255,0.06)',
        animationDelay: `${delay}ms`,
      }}
    >
      <p className="text-xs text-white/35 uppercase tracking-wider mb-2">{label}</p>
      <p className="text-2xl font-bold text-white">{typeof value === 'number' ? value.toLocaleString() : value}</p>
      {sub && <p className="text-xs mt-1" style={{ color: accent || '#10B981' }}>{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!localStorage.getItem('wacrm_token')) {
      router.push('/');
      return;
    }
    getDashboardSummary()
      .then(setData)
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
    return <div className="flex items-center justify-center h-64 text-white/30">Loading…</div>;
  if (error) return <div className="text-red-400 text-sm">{error}</div>;
  if (!data) return null;

  const a = data.ai_requests_today;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-sm text-white/35 mt-0.5">Overview of your WhatsApp CRM instance</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <StatCard label="Total Conversations" value={data.total_conversations} delay={0} />
        <StatCard label="Active Conversations" value={data.active_conversations} delay={30} />
        <StatCard label="AI Handled Today" value={data.ai_handled} delay={60} />
        <StatCard label="Messages Today" value={data.messages_today} delay={90} />
        <StatCard label="New Leads Today" value={data.new_leads_today} delay={120} />
        <StatCard label="Converted Leads" value={data.converted_leads} delay={150} />
        <StatCard
          label="AI Requests Today"
          value={a.groq + a.openrouter}
          sub={`Groq: ${a.groq}  ·  OpenRouter: ${a.openrouter}`}
          accent="#6366F1"
          delay={180}
        />
        <StatCard label="Active Campaigns" value={data.campaigns_active} delay={210} />
        <StatCard label="Campaign Subscribers" value={data.campaign_subscribers} delay={240} />
      </div>
    </div>
  );
}
