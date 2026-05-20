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
  active: '#25D366',
  paused: '#F59E0B',
  draft: '#667781',
  completed: '#128C7E',
};

function StatusTag({ status }: { status: string }) {
  return (
    <span
      className="text-[11px] px-2 py-0.5 rounded-full uppercase font-semibold"
      style={{ background: `${STATUS_COLOR[status] || '#667781'}18`, color: STATUS_COLOR[status] || '#667781' }}
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

  const [broadcastMsg, setBroadcastMsg] = useState('');
  const [broadcastTag, setBroadcastTag] = useState('');
  const [broadcastSending, setBroadcastSending] = useState(false);
  const [broadcastCampaignId, setBroadcastCampaignId] = useState('');
  const [broadcastStatus, setBroadcastStatus] = useState('');

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
      setBroadcastStatus('Sent successfully!');
      setTimeout(() => { setBroadcastStatus(''); setBroadcastMsg(''); setBroadcastCampaignId(''); }, 3000);
    } catch (err: unknown) {
      setBroadcastStatus(`Error: ${err instanceof Error ? err.message : 'Unknown'}`);
    } finally {
      setBroadcastSending(false);
    }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64" style={{ color: '#667781' }}>Loading…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#111B21' }}>Campaigns</h1>
          <p className="text-sm mt-0.5" style={{ color: '#667781' }}>Drip & broadcast campaigns</p>
        </div>
        {tab === 'campaigns' && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
            style={{ background: '#25D366' }}
            onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#128C7E')}
            onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#25D366')}
          >
            <Plus size={15} /> New Campaign
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg w-fit" style={{ background: '#F0F2F5' }}>
        {(['campaigns', 'broadcast'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-sm font-medium cursor-pointer border-none transition-all ${
              tab === t ? 'text-white' : 'hover:text-[#111B21]'
            }`}
            style={tab === t ? { background: '#25D366', color: '#FFFFFF' } : { background: 'transparent', color: '#667781' }}
          >
            {t === 'campaigns' ? '📨 Campaigns' : '📡 Broadcast'}
          </button>
        ))}
      </div>

      {/* Campaigns tab */}
      {tab === 'campaigns' && (
        <div className="space-y-2">
          {campaigns.length === 0 && (
            <div className="text-center py-10 rounded-xl border" style={{ borderColor: '#E0E0E0', color: '#667781' }}>No campaigns yet.</div>
          )}
          {campaigns.map((c) => (
            <div
              key={c.id}
              className="rounded-xl border p-4 flex flex-wrap items-center gap-3 sm:gap-4 animate-fade-in"
              style={{ background: '#FFFFFF', borderColor: '#E0E0E0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}
            >
              <Zap size={18} style={{ color: '#25D366' }} className="shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold" style={{ color: '#111B21' }}>{c.name}</p>
                <p className="text-xs mt-0.5" style={{ color: '#667781' }}>
                  {c.campaign_type} · trigger: {c.trigger_event}
                </p>
              </div>
              <StatusTag status={c.status} />
              <div className="text-xs text-center" style={{ color: '#667781' }}>
                <p className="font-semibold" style={{ color: '#111B21' }}>{c.active_subscribers}</p>
                <p>subscribers</p>
              </div>
              <div className="text-xs text-center" style={{ color: '#667781' }}>
                <p>{c.sent_count}</p>
                <p>sent</p>
              </div>
              <div className="text-xs text-center" style={{ color: '#667781' }}>
                <p className="font-semibold" style={{ color: '#25D366' }}>{c.delivered_count}</p>
                <p>delivered</p>
              </div>
              <div className="text-xs text-center" style={{ color: '#667781' }}>
                <p>{c.replied_count}</p>
                <p>replied</p>
              </div>
              <div className="flex gap-1.5 shrink-0">
                <button
                  onClick={() => handleActivate(c.id)}
                  className="p-2 rounded-lg cursor-pointer border-none transition-all"
                  style={{ color: '#25D366', background: '#25D36615' }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#25D36625')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#25D36615')}
                  title="Activate"
                >
                  <Play size={14} />
                </button>
                <button
                  onClick={() => handlePause(c.id)}
                  className="p-2 rounded-lg cursor-pointer border-none transition-all"
                  style={{ color: '#F59E0B', background: '#F59E0B15' }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#F59E0B25')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#F59E0B15')}
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
          style={{ background: '#FFFFFF', borderColor: '#E0E0E0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}
        >
          <div className="flex items-center gap-2">
            <Send size={16} style={{ color: '#25D366' }} />
            <h2 className="text-lg font-semibold" style={{ color: '#111B21' }}>Send Broadcast</h2>
          </div>
          <p className="text-sm" style={{ color: '#667781' }}>Send a message to all contacts or a specific segment.</p>

          {broadcastStatus && (
            <p className={`text-sm ${broadcastStatus.includes('Error') ? 'text-red-600' : broadcastStatus.includes('successfully') ? 'text-green-600' : 'text-amber-600'}`}>
              {broadcastStatus}
            </p>
          )}

          <div>
            <label className="block text-xs uppercase mb-1" style={{ color: '#667781' }}>Campaign</label>
            <select
              value={broadcastCampaignId}
              onChange={(e) => setBroadcastCampaignId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm outline-none cursor-pointer"
              style={{ color: '#111B21', background: '#F0F2F5', border: '1px solid #E0E0E0' }}
            >
              <option value="">Select a campaign…</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs uppercase mb-1" style={{ color: '#667781' }}>Tag Filter (optional)</label>
            <input
              type="text"
              value={broadcastTag}
              onChange={(e) => setBroadcastTag(e.target.value)}
              placeholder="Filter recipients by tag…"
              className="w-full px-3 py-2 rounded-lg text-sm outline-none"
              style={{ color: '#111B21', background: '#F0F2F5', border: '1px solid #E0E0E0' }}
              onFocus={(e) => (e.target.style.borderColor = '#25D366')}
              onBlur={(e) => (e.target.style.borderColor = '#E0E0E0')}
            />
          </div>

          <div>
            <label className="block text-xs uppercase mb-1" style={{ color: '#667781' }}>Message</label>
            <textarea
              value={broadcastMsg}
              onChange={(e) => setBroadcastMsg(e.target.value)}
              placeholder="Write your broadcast message…"
              rows={5}
              className="w-full px-3 py-2 rounded-lg text-sm resize-none outline-none"
              style={{ color: '#111B21', background: '#F0F2F5', border: '1px solid #E0E0E0' }}
              onFocus={(e) => (e.target.style.borderColor = '#25D366')}
              onBlur={(e) => (e.target.style.borderColor = '#E0E0E0')}
            />
          </div>

          <button
            onClick={handleBroadcast}
            disabled={broadcastSending || !broadcastCampaignId || !broadcastMsg.trim()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all disabled:opacity-40"
            style={{ background: '#25D366' }}
            onMouseEnter={(e) => !broadcastSending && !(!broadcastCampaignId || !broadcastMsg.trim()) && ((e.currentTarget as HTMLButtonElement).style.background = '#128C7E')}
            onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#25D366')}
          >
            {broadcastSending ? <><Loader2 size={15} className="animate-spin" /> Sending…</> : <><Send size={15} /> Send Broadcast</>}
          </button>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-md rounded-xl border p-6 space-y-4 animate-fade-in" style={{ background: '#FFFFFF', borderColor: '#E0E0E0', boxShadow: '0 8px 32px rgba(0,0,0,0.12)' }}>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold" style={{ color: '#111B21' }}>New Campaign</h2>
              <button onClick={() => setShowCreate(false)} className="cursor-pointer bg-transparent border-none text-xl" style={{ color: '#667781' }}>&times;</button>
            </div>
            <div>
              <label className="block text-xs uppercase mb-1" style={{ color: '#667781' }}>Campaign Name</label>
              <input
                type="text"
                value={newCampaign.name}
                onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
                placeholder="e.g. Summer Promotion"
                className="w-full px-3 py-2 rounded-lg text-sm outline-none"
                style={{ color: '#111B21', background: '#F0F2F5', border: '1px solid #E0E0E0' }}
                onFocus={(e) => (e.target.style.borderColor = '#25D366')}
                onBlur={(e) => (e.target.style.borderColor = '#E0E0E0')}
              />
            </div>
            <div>
              <label className="block text-xs uppercase mb-1" style={{ color: '#667781' }}>Type</label>
              <select
                value={newCampaign.campaign_type}
                onChange={(e) => setNewCampaign({ ...newCampaign, campaign_type: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm outline-none cursor-pointer"
                style={{ color: '#111B21', background: '#F0F2F5', border: '1px solid #E0E0E0' }}
              >
                <option value="drip">Drip</option>
                <option value="broadcast">Broadcast</option>
                <option value="re_engagement">Re-engagement</option>
              </select>
            </div>
            <div>
              <label className="block text-xs uppercase mb-1" style={{ color: '#667781' }}>Trigger Event (optional)</label>
              <input
                type="text"
                value={newCampaign.trigger_event}
                onChange={(e) => setNewCampaign({ ...newCampaign, trigger_event: e.target.value })}
                placeholder="e.g. new_lead, order_confirmed"
                className="w-full px-3 py-2 rounded-lg text-sm outline-none"
                style={{ color: '#111B21', background: '#F0F2F5', border: '1px solid #E0E0E0' }}
                onFocus={(e) => (e.target.style.borderColor = '#25D366')}
                onBlur={(e) => (e.target.style.borderColor = '#E0E0E0')}
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setShowCreate(false)}
                className="flex-1 py-2.5 rounded-lg text-sm cursor-pointer font-medium transition-all"
                style={{ color: '#667781', border: '1px solid #E0E0E0', background: '#FFFFFF' }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#F0F2F5')}
                onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#FFFFFF')}
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                className="flex-1 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
                style={{ background: '#25D366' }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#128C7E')}
                onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#25D366')}
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
