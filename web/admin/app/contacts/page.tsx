'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getContacts, createCampaign as apiCreate } from '../../lib/api';
import type { Contact } from '../../lib/api';
import { Loader2, Search, Plus, X } from 'lucide-react';

const STATUS_OPTIONS = ['new', 'contacted', 'qualified', 'converted', 'inactive'];
const SOUTH_AFRICA_LOADSHED_STAGES = ['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4'];

// Detect loadshedding stage from ZA number
function getLoadshedStage(phone: string): string | null {
  const cleaned = phone.replace(/\D/g, '');
  // South African numbers: +27XXXXXXXXX or 0XXXXXXXXX
  if (!cleaned.startsWith('27') && !cleaned.startsWith('0')) return null;
  const numMatch = cleaned.match(/0?27\d{9}$/);
  if (!numMatch) return null;
  // Mock: loadshedding based on area — just a demo label
  const suffix = cleaned.slice(-4);
  const hash = [...suffix].reduce((s, c) => s + c.charCodeAt(0), 0);
  return SOUTH_AFRICA_LOADSHED_STAGES[hash % SOUTH_AFRICA_LOADSHED_STAGES.length];
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'new': return '#F59E0B';
    case 'contacted': return '#6366F1';
    case 'qualified': return '#10B981';
    case 'converted': return '#10B981';
    case 'inactive': return '#6B7280';
    default: return '#6366F1';
  }
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#10B981';
  if (score >= 50) return '#F59E0B';
  if (score >= 25) return '#6366F1';
  return '#6B7280';
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className="text-[11px] px-2 py-0.5 rounded-full uppercase font-semibold whitespace-nowrap"
      style={{ background: `${getStatusColor(status)}20`, color: getStatusColor(status) }}
    >
      {status.replace('_', ' ')}
    </span>
  );
}

export default function ContactsPage() {
  const router = useRouter();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [leadFilter, setLeadFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [selected, setSelected] = useState<Contact | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem('wacrm_token')) return router.push('/');
    fetchContacts();
  }, [router, search, leadFilter, tagFilter]);

  const fetchContacts = async () => {
    setLoading(true);
    try {
      const res = await getContacts({ page: 1, limit: 50, search, lead_status: leadFilter, tag: tagFilter });
      setContacts(res.data);
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

  // Create Contact modal state
  const [newContact, setNewContact] = useState({
    first_name: '', last_name: '', whatsapp_number: '', lead_status: 'new', province: '', city: '', lead_source: '',
  });

  const handleCreate = async () => {
    try {
      // POST /api/contacts — this endpoint is assumed available; if not, backend adds it
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/contacts`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(localStorage.getItem('wacrm_token') ? { Authorization: `Bearer ${localStorage.getItem('wacrm_token')}` } : {}) },
          body: JSON.stringify({ ...newContact, display_name: `${newContact.first_name} ${newContact.last_name}` }),
        },
      );
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
      setShowCreate(false);
      setNewContact({ first_name: '', last_name: '', whatsapp_number: '', lead_status: 'new', province: '', city: '', lead_source: '' });
      fetchContacts();
    } catch (err) { console.error(err); }
  };

  if (loading)
    return <div className="flex items-center justify-center h-64 text-white/30">Loading…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-white">Contacts</h1>
          <p className="text-sm text-white/35 mt-0.5">{contacts.length} contacts</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
          style={{ background: '#6366F1' }}
          onMouseEnter={(e) => ((e.target as HTMLButtonElement).style.background = '#4F46E5')}
          onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.background = '#6366F1')}
        >
          <Plus size={15} /> Add Contact
        </button>
      </div>

      {/* Filters */}
      <div
        className="rounded-xl p-4 border flex flex-wrap gap-3 items-center"
        style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            type="text"
            placeholder="Search name or number…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 outline-none placeholder:text-white/25"
          />
        </div>
        <select
          value={leadFilter}
          onChange={(e) => setLeadFilter(e.target.value)}
          className="px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none cursor-pointer"
        >
          <option value="">All Statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Tag filter…"
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          className="px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 outline-none placeholder:text-white/25"
        />
      </div>

      <div className="flex gap-0 rounded-xl border overflow-hidden" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
        {/* Table */}
        <div className={`flex-1 overflow-auto transition-all ${selected ? 'md:max-w-[75%]' : ''}`}>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-white/[.06]">
                {['Name', 'WhatsApp', 'Status', 'Score', 'Tags', 'Province', 'Source', 'Created'].map((h) => (
                  <th key={h} className="text-left text-[11px] text-white/30 uppercase tracking-wider px-4 py-3 font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contacts.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center text-white/25 py-10">No contacts found.</td>
                </tr>
              )}
              {contacts.map((c) => {
                const lds = getLoadshedStage(c.whatsapp_number);
                return (
                  <tr
                    key={c.id}
                    onClick={() => setSelected(selected?.id === c.id ? null : c)}
                    className={`border-b border-white/[.04] cursor-pointer transition-all ${
                      selected?.id === c.id ? 'bg-white/[.06]' : 'hover:bg-white/[.02]'
                    }`}
                  >
                    <td className="px-4 py-3 text-white font-medium">{c.display_name}</td>
                    <td className="px-4 py-3 text-white/55 flex items-center gap-1.5">
                      {c.whatsapp_number}
                      {lds && (
                        <span title={`Load shedding: ${lds}`} className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 font-semibold">
                          ⚡ {lds}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={c.lead_status} /></td>
                    <td className="px-4 py-3">
                      <span className="font-medium" style={{ color: getScoreColor(c.lead_score) }}>
                        {c.lead_score}
                      </span>
                      <span className="text-white/25 text-xs"> /100</span>
                    </td>
                    <td className="px-4 py-3 text-white/50">
                      {c.tags?.length ? (
                        <div className="flex gap-1 flex-wrap">
                          {c.tags.slice(0, 3).map((t) => (
                            <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-white/[.06] text-white/55">{t}</span>
                          ))}
                        </div>
                      ) : <span className="text-white/25">—</span>}
                    </td>
                    <td className="px-4 py-3 text-white/50">{c.province || '—'}</td>
                    <td className="px-4 py-3 text-white/50">{c.lead_source || '—'}</td>
                    <td className="px-4 py-3 text-white/35 text-xs">{c.created_at?.slice(0, 10) || '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Detail panel */}
        {selected && (
          <div
            className="w-full md:w-[320px] border-l p-5 space-y-4 shrink-0"
            style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.2)' }}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Contact Detail</h3>
              <button onClick={() => setSelected(null)} className="text-white/35 hover:text-white cursor-pointer bg-transparent border-none text-lg leading-none">&times;</button>
            </div>
            <div>
              <p className="text-xs text-white/30 uppercase">Name</p>
              <p className="text-sm text-white mt-0.5">{selected.display_name}</p>
            </div>
            <div>
              <p className="text-xs text-white/30 uppercase">WhatsApp Number</p>
              <p className="text-sm text-white mt-0.5">{selected.whatsapp_number}</p>
            </div>
            <div>
              <p className="text-xs text-white/30 uppercase">Lead Status</p>
              <p className="mt-1"><StatusBadge status={selected.lead_status} /></p>
            </div>
            <div>
              <p className="text-xs text-white/30 uppercase">Lead Score</p>
              <p className="text-lg font-bold mt-0.5" style={{ color: getScoreColor(selected.lead_score) }}>{selected.lead_score}<span className="text-xs text-white/25"> /100</span></p>
            </div>
            {selected.tags?.length && (
              <div>
                <p className="text-xs text-white/30 uppercase mb-1.5">Tags</p>
                <div className="flex gap-1 flex-wrap">
                  {selected.tags.map((t) => (
                    <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/20">{t}</span>
                  ))}
                </div>
              </div>
            )}
            <div>
              <p className="text-xs text-white/30 uppercase">Province</p>
              <p className="text-sm text-white mt-0.5">{selected.province || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-white/30 uppercase">City</p>
              <p className="text-sm text-white mt-0.5">{selected.city || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-white/30 uppercase">Source</p>
              <p className="text-sm text-white mt-0.5">{selected.lead_source || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-white/30 uppercase">Created</p>
              <p className="text-sm text-white mt-0.5">{selected.created_at?.slice(0, 10) || '—'}</p>
            </div>
          </div>
        )}
      </div>

      {/* Create Contact Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div
            className="w-full max-w-lg rounded-xl border p-6 space-y-4 animate-fade-in"
            style={{ background: '#151519', borderColor: 'rgba(255,255,255,0.06)' }}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Add Contact</h2>
              <button onClick={() => setShowCreate(false)} className="text-white/40 hover:text-white cursor-pointer bg-transparent border-none text-xl">&times;</button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                ['First Name', 'first_name'],
                ['Last Name', 'last_name'],
                ['WhatsApp Number', 'whatsapp_number'],
                ['Province', 'province'],
                ['City', 'city'],
                ['Source', 'lead_source'],
              ].map(([label, key]) => (
                <div key={key} className="col-span-2 sm:col-span-1">
                  <label className="block text-[11px] text-white/35 uppercase mb-1">{label}</label>
                  <input
                    type="text"
                    value={(newContact as Record<string, string>)[key]}
                    onChange={(e) =>
                      setNewContact({ ...newContact, [key]: e.target.value })
                    }
                    className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 outline-none placeholder:text-white/25"
                  />
                </div>
              ))}
            </div>
            <div>
              <label className="block text-[11px] text-white/35 uppercase mb-1">Lead Status</label>
              <select
                value={newContact.lead_status}
                onChange={(e) => setNewContact({ ...newContact, lead_status: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none cursor-pointer"
              >
                {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setShowCreate(false)}
                className="flex-1 py-2.5 rounded-lg text-sm text-white/55 cursor-pointer border border-white/[.08] bg-transparent font-medium hover:bg-white/[.04] transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                className="flex-1 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
                style={{ background: '#6366F1' }}
              >
                Create Contact
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
