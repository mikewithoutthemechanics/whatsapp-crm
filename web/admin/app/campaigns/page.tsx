'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  getCampaigns,
  createCampaign,
  activateCampaign,
  pauseCampaign,
  broadcastCampaign,
} from '../../lib/api';
import type { Campaign } from '../../lib/api';
import { Loader2, Plus, Play, Pause, Send, X, Zap } from 'lucide-react';

const STATUS_COLOR: Record<string, string> = {
  active: '#10B981',
  paused: '#F59E0B',
  draft: '#6B7280',
  completed: '#6366F1',
};

function StatusTag({ status }: { status: string }) {
  return (
    <span
      className="text-[11px] px-2 py-0.5 rounded-full uppercase font-semibold"
      style={{ background: `${STATUS_COLOR[status] || '#6B7280'}20`, color: STATUS_COLOR[status] || '#6B7280' }}
    >
      {status}
    </span>
  );
}

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'campaigns' | 'broadcast'>('campaigns');
  const [showCreate, setShowCreate] = useState(false);

  // Broadcast form
  const [broadcastMsg, setBroadcastMsg] = useState('');
  const [broadcastTag, setBroadcastTag] = useState('');
  const [broadcastSending, setBroadcastSending] = useState(false);
  const [broadcastCampaignId, setBroadcastCampaignId] = useState('');
  const [broadcastStatus, setBroadcastStatus] = useState('');

  // Create form
  const [newCampaign, setNewCampaign] = useState({ name: '', campaign_type: 'drip', trigger_event: '' });

  useEffect(() => {
    if (!localStorage.getItem('wacrm_token')) return router.push('/');
    loadCampaigns();
  }, [router]);

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const res = await getCampaigns();
      setCampaigns(res);
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

  const handleCreate = async () => {
    if (!newCampaign.name) return;
    try {
      await createCampaign(newCampaign);
      setShowCreate(false);
      setNewCampaign({ name: '', campaign_type: 'drip', trigger_event: '' });
      loadCampaigns();
    } catch (err) { console.error(err); }
  };

  const handleActivate = async (id: string) => {
    try { await activateCampaign(id); loadCampaigns(); } catch (err) { console.error(err); }
  };
  const handlePause = async (id: string) => {
    try { await pauseCampaign(id); loadCampaigns(); } catch (err) { console.error(err); }
  };

  const handleBroadcast = async () => {
    if (!broadcastCampaignId || !broadcastMsg.trim()) return;
    setBroadcastSending(true);
    setBroadcastStatus('Sending…');
    try {
      const id = broadcastCampaignId;
      const payload: Record<string, unknown> = { message: broadcastMsg };
      if (broadcastTag) payload.tag = broadcastTag;
      await broadcastCampaign(id, payload);
      setBroadcastStatus('✅ Sent successfully!');
      setTimeout(() => { setBroadcastStatus(''); setBroadcastMsg(''); setBroadcastCampaignId(''); }, 3000);
    } catch (err: unknown) {
      setBroadcastStatus(`❌ Error: ${err instanceof Error ? err.message : 'Unknown'}`);
    } finally {
      setBroadcastSending(false);
    }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64 text-white/30">Loading…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-white">Campaigns</h1>
          <p className="text-sm text-white/35 mt-0.5">Drip & broadcast campaigns</p>
        </div>
        {tab === 'campaigns' && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
            style={{ background: '#6366F1' }}
            onMouseEnter={(e) => ((e.target as HTMLButtonElement).style.background = '#4F46E5')}
            onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.background = '#6366F1')}
          >
            <Plus size={15} /> New Campaign
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg w-fit" style={{ background: 'rgba(255,255,255,0.04)' }}>
        {(['campaigns', 'broadcast'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-all ${
              tab === t ? 'text-white' : 'text-white/40 hover:text-white/70'
            }`}
            style={tab === t ? { background: '#6366F1' } : { background: 'transparent' }}
          >
            {t === 'campaigns' ? '📨 Campaigns' : '📡 Broadcast'}
          </button>
        ))}
      </div>

      {/* Campaigns tab */}
      {tab === 'campaigns' && (
        <div className="space-y-2">
          {campaigns.length === 0 && (
            <div className="text-center text-white/25 py-10 rounded-xl border" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>No campaigns yet.</div>
          )}
          {campaigns.map((c) => (
            <div
              key={c.id}
              className="rounded-xl border p-4 flex flex-wrap items-center gap-3 sm:gap-4 animate-fade-in"
              style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}
            >
              <Zap size={18} className="text-indigo-400 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white">{c.name}</p>
                <p className="text-xs text-white/35 mt-0.5">
                  {c.campaign_type} · trigger: {c.trigger_event}
                </p>
              </div>
              <StatusTag status={c.status} />
              <div className="text-xs text-white/40 text-center">
                <p className="font-semibold text-white">{c.active_subscribers}</p>
                <p>subscribers</p>
              </div>
              <div className="text-xs text-white/40 text-center">
                <p>{c.sent_count}</p>
                <p className="text-white/25">sent</p>
              </div>
              <div className="text-xs text-white/40 text-center">
                <p className="text-emerald-400 font-semibold">{c.delivered_count}</p>
                <p className="text-white/25">delivered</p>
              </div>
              <div className="text-xs text-white/40 text-center">
                <p>{c.replied_count}</p>
                <p className="text-white/25">replied</p>
              </div>
              <div className="flex gap-1.5 shrink-0">
                <button
                  onClick={() => handleActivate(c.id)}
                  className="p-2 rounded-lg text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 cursor-pointer border-none transition-all"
                  title="Activate"
                >
                  <Play size={14} />
                </button>
                <button
                  onClick={() => handlePause(c.id)}
                  className="p-2 rounded-lg text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 cursor-pointer border-none transition-all"
                  title="Pause"
                >
                  <Pause size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Broadcast tab */}
      {tab === 'broadcast' && (
        <div
          className="rounded-xl border p-5 space-y-4 animate-fade-in"
          style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-2">
            <Send size={16} className="text-indigo-400" />
            <h2 className="text-lg font-semibold text-white">Send Broadcast</h2>
          </div>
          <p className="text-sm text-white/35">Send a message to all contacts or a specific segment.</p>

          {broadcastStatus && (
            <p className={`text-sm ${broadcastStatus.includes('❌') ? 'text-red-400' : broadcastStatus.includes('✅') ? 'text-emerald-400' : 'text-amber-400'}`}>
              {broadcastStatus}
            </p>
          )}

          <div>
            <label className="block text-xs text-white/35 uppercase mb-1">Campaign</label>
            <select
              value={broadcastCampaignId}
              onChange={(e) => setBroadcastCampaignId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none cursor-pointer"
            >
              <option value="">Select a campaign…</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-white/35 uppercase mb-1">Tag Filter (optional)</label>
            <input
              type="text"
              value={broadcastTag}
              onChange={(e) => setBroadcastTag(e.target.value)}
              placeholder="Filter recipients by tag…"
              className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 outline-none placeholder:text-white/25"
            />
          </div>

          <div>
            <label className="block text-xs text-white/35 uppercase mb-1">Message</label>
            <textarea
              value={broadcastMsg}
              onChange={(e) => setBroadcastMsg(e.target.value)}
              placeholder="Write your broadcast message…"
              rows={5}
              className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 resize-none outline-none placeholder:text-white/25"
            />
          </div>

          <button
            onClick={handleBroadcast}
            disabled={broadcastSending || !broadcastCampaignId || !broadcastMsg.trim()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all disabled:opacity-40"
            style={{ background: '#6366F1' }}
            onMouseEnter={(e) => !broadcastSending && !(!broadcastCampaignId || !broadcastMsg.trim()) && ((e.target as HTMLButtonElement).style.background = '#4F46E5')}
            onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.background = '#6366F1')}
          >
            {broadcastSending ? <><Loader2 size={15} className="animate-spin" /> Sending…</> : <><Send size={15} /> Send Broadcast</>}
          </button>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-md rounded-xl border p-6 space-y-4 animate-fade-in" style={{ background: '#151519', borderColor: 'rgba(255,255,255,0.06)' }}>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">New Campaign</h2>
              <button onClick={() => setShowCreate(false)} className="text-white/40 hover:text-white cursor-pointer bg-transparent border-none text-xl">&times;</button>
            </div>
            <div>
              <label className="block text-xs text-white/35 uppercase mb-1">Campaign Name</label>
              <input
                type="text"
                value={newCampaign.name}
                onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
                placeholder="e.g. Summer Promotion"
                className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 outline-none placeholder:text-white/25"
              />
            </div>
            <div>
              <label className="block text-xs text-white/35 uppercase mb-1">Type</label>
              <select
                value={newCampaign.campaign_type}
                onChange={(e) => setNewCampaign({ ...newCampaign, campaign_type: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none cursor-pointer"
              >
                <option value="drip">Drip</option>
                <option value="broadcast">Broadcast</option>
                <option value="re_engagement">Re-engagement</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-white/35 uppercase mb-1">Trigger Event (optional)</label>
              <input
                type="text"
                value={newCampaign.trigger_event}
                onChange={(e) => setNewCampaign({ ...newCampaign, trigger_event: e.target.value })}
                placeholder="e.g. new_lead, order_confirmed"
                className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 outline-none placeholder:text-white/25"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={() => setShowCreate(false)} className="flex-1 py-2.5 rounded-lg text-sm text-white/55 cursor-pointer border border-white/[.08] bg-transparent font-medium hover:bg-white/[.04] transition-all">
                Cancel
              </button>
              <button
                onClick={handleCreate}
                className="flex-1 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
                style={{ background: '#6366F1' }}
              >
                Create Campaign
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
