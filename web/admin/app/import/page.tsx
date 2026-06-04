'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  getImportSources,
  getImportJobs,
  runChatImport,
  triggerContactImport,
  getPlatformSummary,
} from '../../lib/api';
import { Loader2, RefreshCw, Upload, Play, Download, CheckCircle2, XCircle, Clock, ChevronRight } from 'lucide-react';

type ImportSource = {
  id: string;
  name: string;
  source_type: string;
  provider: string;
  is_active: boolean;
  total_contacts_imported: number;
  total_messages_imported: number;
  last_import_at?: string | null;
};

type ImportJobRow = {
  id: string;
  job_type: string;
  status: string;
  created_at: string;
  contacts_created: number;
  messages_imported: number;
  contacts_found: number;
  errors: unknown[];
  warnings: unknown[];
  summary?: string | null;
};

function statusIcon(status: string) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 size={14} className="text-emerald-400" />;
    case 'failed':
      return <XCircle size={14} className="text-red-400" />;
    case 'running':
      return <Loader2 size={14} className="text-blue-400 animate-spin" />;
    default:
      return <Clock size={14} className="text-white/30" />;
  }
}

export default function ImportPage() {
  const router = useRouter();
  const [sources, setSources] = useState<ImportSource[]>([]);
  const [jobs, setJobs] = useState<ImportJobRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [importType, setImportType] = useState('full');
  const [error, setError] = useState('');

  const [brands, setBrands] = useState<{ id: string; name: string }[]>([]);
  const [selectedBrand, setSelectedBrand] = useState('');
  const [selectedSource, setSelectedSource] = useState('');
  const [brandLoading, setBrandLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem('wacrm_token')) {
      router.push('/');
      return;
    }
    loadBrands();
    loadData();
  }, [router]);

  async function loadBrands() {
    setBrandLoading(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/business/brands`,
        {
          headers: { Authorization: `Bearer ${localStorage.getItem('wacrm_token') || '' }` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        const list = (data.data || []).map((b: { id: string; name: string }) => ({ id: b.id, name: b.name }));
        setBrands(list);
        if (list.length && !selectedBrand) setSelectedBrand(list[0].id);
      }
    } catch { /* best-effort */ }
    setBrandLoading(false);
  }

  async function loadData() {
    setLoading(true);
    try {
      const [srcRes, jobRes] = await Promise.all([
        getImportSources(),
        getImportJobs(undefined, 1, 20),
      ]);
      setSources(srcRes.data || []);
      setJobs((jobRes.data || []).slice(0, 20));
    } catch (err: unknown) {
      if (err instanceof Error && (err.message.includes('401') || err.message.includes('403'))) {
        localStorage.removeItem('wacrm_token');
        router.push('/');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load');
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleRunImport() {
    setRunning(true);
    setError('');
    try {
      await runChatImport({
        business_id: selectedBrand || 'default',
        source_id: selectedSource || undefined,
        import_type: importType,
        chat_limit: 50,
        message_limit: 30,
        dry_run: dryRun,
      });
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setRunning(false);
    }
  }

  async function handleQuickContactImport() {
    setRunning(true);
    setError('');
    try {
      await triggerContactImport({ dry_run: dryRun });
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Contact import failed');
    } finally {
      setRunning(false);
    }
  }

  const totalImported = sources.reduce((a, s) => a + (s.total_contacts_imported || 0), 0);
  const totalMsgs = sources.reduce((a, s) => a + (s.total_messages_imported || 0), 0);
  const activeSources = sources.filter((s) => s.is_active).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Import from WhatsApp</h1>
        <p className="text-sm text-white/35 mt-0.5">
          Auto-import clients and chat history from your WhatsApp sessions into the CRM.
        </p>
      </div>

      {error && <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-400">{error}</div>}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl p-4 border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
          <p className="text-[11px] text-white/35 uppercase tracking-wider mb-1">Active Sources</p>
          <p className="text-2xl font-bold text-white">{activeSources}</p>
          <p className="text-xs text-white/30 mt-0.5">{sources.length} total configured</p>
        </div>
        <div className="rounded-xl p-4 border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
          <p className="text-[11px] text-white/35 uppercase tracking-wider mb-1">Contacts Imported</p>
          <p className="text-2xl font-bold text-emerald-400">{totalImported.toLocaleString()}</p>
          <p className="text-xs text-white/30 mt-0.5">{totalMsgs.toLocaleString()} messages</p>
        </div>
        <div className="rounded-xl p-4 border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
          <p className="text-[11px] text-white/35 uppercase tracking-wider mb-1">Recent Jobs</p>
          <p className="text-2xl font-bold text-white">{jobs.length}</p>
          <p className="text-xs text-white/30 mt-0.5">
            {jobs.filter((j) => j.status === 'completed').length} succeeded · {jobs.filter((j) => j.status === 'failed').length} failed
          </p>
        </div>
      </div>

      {/* Run Import */}
      <div className="rounded-xl border p-5 space-y-4" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2">
          <Upload size={16} className="text-indigo-400" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Run New Import</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-[11px] text-white/35 uppercase mb-1">Brand / Business</label>
            {brandLoading ? (
              <div className="px-3 py-2 rounded-lg text-xs text-white/30 bg-white/[.04] border border-white/[.08]">Loading…</div>
            ) : (
              <select
                value={selectedBrand}
                onChange={(e) => setSelectedBrand(e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none cursor-pointer"
              >
                {brands.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                <option value="default">(default)</option>
              </select>
            )}
          </div>
          <div>
            <label className="block text-[11px] text-white/35 uppercase mb-1">Import Type</label>
            <select
              value={importType}
              onChange={(e) => setImportType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none cursor-pointer"
            >
              <option value="full">Full (contacts + messages)</option>
              <option value="contacts_only">Contacts Only</option>
              <option value="delta">Delta (new only)</option>
              <option value="chat_history">Chat History Backfill</option>
            </select>
          </div>
          <div>
            <label className="block text-[11px] text-white/35 uppercase mb-1">Source (optional)</label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] outline-none cursor-pointer"
            >
              <option value="">Any / default</option>
              {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button
              onClick={handleQuickContactImport}
              disabled={running}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
              style={{ background: '#6366F1' }}
              onMouseEnter={(e) => ((e.target as HTMLButtonElement).style.background = '#4F46E5')}
              onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.background = '#6366F1')}
            >
              <Upload size={14} />
              Contacts
            </button>
            <button
              onClick={handleRunImport}
              disabled={running}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-none transition-all"
              style={{ background: '#10B981' }}
              onMouseEnter={(e) => ((e.target as HTMLButtonElement).style.background = '#059669')}
              onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.background = '#10B981')}
            >
              {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              Run Import
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="w-4 h-4 rounded border-white/10 bg-white/[.04]"
            />
            <span className="text-xs text-white/50">Dry run (preview only, no data written)</span>
          </label>
        </div>
      </div>

      {/* Sources + Jobs */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Sources */}
        <div className="rounded-xl border overflow-hidden" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
          <div className="px-5 py-3.5 border-b border-white/[.06] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Download size={14} className="text-indigo-400" />
              <h2 className="text-xs font-semibold text-white uppercase tracking-wider">Import Sources</h2>
            </div>
            <button
              onClick={loadData}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] text-white/50 border border-white/[.06] bg-transparent cursor-pointer hover:text-white transition-colors"
            >
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
          {loading ? (
            <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-white/30" /></div>
          ) : sources.length === 0 ? (
            <div className="p-6 text-center text-sm text-white/25">No sources configured yet. Run an import to auto-create one.</div>
          ) : (
            <div className="divide-y divide-white/[.04]">
              {sources.map((s) => (
                <div key={s.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white font-medium">{s.name}</p>
                    <p className="text-[11px] text-white/35 mt-0.5">
                      {s.provider} · {s.source_type} · {s.is_active ? 'active' : 'paused'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-white/55">{s.total_contacts_imported} contacts · {s.total_messages_imported} msgs</p>
                    {s.last_import_at && (
                      <p className="text-[11px] text-white/25 mt-0.5">
                        Last: {new Date(s.last_import_at).toLocaleString('en-ZA')}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Jobs */}
        <div className="rounded-xl border overflow-hidden" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
          <div className="px-5 py-3.5 border-b border-white/[.06]">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider">Import Jobs</h2>
          </div>
          {loading ? (
            <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-white/30" /></div>
          ) : jobs.length === 0 ? (
            <div className="p-6 text-center text-sm text-white/25">No import jobs yet. Run an import to get started.</div>
          ) : (
            <div className="divide-y divide-white/[.04]">
              {jobs.map((j) => (
                <div key={j.id} className="px-5 py-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {statusIcon(j.status)}
                      <span className="text-sm text-white/80 font-mono">{j.job_type}</span>
                    </div>
                    <span className="text-[11px] text-white/35">{new Date(j.created_at).toLocaleString('en-ZA')}</span>
                  </div>
                  <div className="mt-1.5 ml-5 flex flex-wrap gap-3">
                    <span className="text-[11px] text-white/40">
                      +{j.contacts_created} c · +{j.messages_imported} msgs
                    </span>
                    {j.errors.length > 0 && (
                      <span className="text-[11px] text-red-400">{j.errors.length} errors</span>
                    )}
                    {j.summary && (
                      <span className="text-[11px] text-white/25 truncate max-w-[240px]">{j.summary}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
