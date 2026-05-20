'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, login } from '../lib/api';
import { Loader2 } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@whatsapp-crm.com');
  const [password, setPassword] = useState('changeme123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await login({ email, password });
      localStorage.setItem('wacrm_token', result.token);
      router.push('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#0B0B0F' }}>
      <div className="w-full max-w-sm animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">💬</div>
          <h1 className="text-2xl font-bold text-white tracking-tight">WhatsApp CRM SA</h1>
          <p className="text-sm text-white/40 mt-1">Admin Dashboard</p>
        </div>

        {/* Card */}
        <div
          className="rounded-xl p-7 border"
          style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5 uppercase tracking-wider">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 transition-colors outline-none"
                placeholder="admin@whatsapp-crm.com"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg text-sm text-white bg-white/[.04] border border-white/[.08] focus:border-indigo-500 transition-colors outline-none"
                placeholder="••••••••"
                required
              />
            </div>

            {error && (
              <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg text-sm font-semibold text-white transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ background: '#6366F1' }}
              onMouseEnter={(e) => !loading && ((e.target as HTMLButtonElement).style.background = '#4F46E5')}
              onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.background = '#6366F1')}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="animate-spin" size={15} /> Signing in…
                </span>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <div className="mt-5 pt-4 border-t border-white/[.06]">
            <p className="text-[11px] text-white/30">
              Default: <span className="text-white/50">admin@whatsapp-crm.com</span> /{' '}
              <span className="text-white/50">changeme123</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
