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
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#EAEDEE' }}>
      <div className="w-full max-w-sm animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">💬</div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: '#075E54' }}>WhatsApp CRM SA</h1>
          <p className="text-sm mt-1" style={{ color: '#3B4A54' }}>Admin Dashboard</p>
        </div>

        {/* Card */}
        <div
          className="rounded-xl p-7 border"
          style={{ background: '#FFFFFF', borderColor: '#B8C1C8', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium mb-1.5 uppercase tracking-wider" style={{ color: '#3B4A54' }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg text-sm transition-colors outline-none"
                style={{ color: '#0B141A', background: '#EAEDEE', border: '1px solid #B8C1C8' }}
                onFocus={(e) => (e.target.style.borderColor = '#25D366')}
                onBlur={(e) => (e.target.style.borderColor = '#B8C1C8')}
                placeholder="admin@whatsapp-crm.com"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 uppercase tracking-wider" style={{ color: '#3B4A54' }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg text-sm transition-colors outline-none"
                style={{ color: '#0B141A', background: '#EAEDEE', border: '1px solid #B8C1C8' }}
                onFocus={(e) => (e.target.style.borderColor = '#25D366')}
                onBlur={(e) => (e.target.style.borderColor = '#B8C1C8')}
                placeholder="••••••••"
                required
              />
            </div>

            {error && (
              <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg text-sm font-semibold text-white transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed border-none"
              style={{ background: '#25D366' }}
              onMouseEnter={(e) => !loading && ((e.target as HTMLButtonElement).style.background = '#128C7E')}
              onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.background = '#25D366')}
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

          <div className="mt-5 pt-4" style={{ borderTop: '1px solid #B8C1C8' }}>
            <p className="text-[11px]" style={{ color: '#3B4A54' }}>
              Default: <span style={{ color: '#0B141A' }}>admin@whatsapp-crm.com</span> /{' '}
              <span style={{ color: '#0B141A' }}>changeme123</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
