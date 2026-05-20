'use client';

import '../app/globals.css';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const HIDDEN_ROUTES = ['/login'];

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: '🏠' },
  { href: '/conversations', label: 'Conversations', icon: '💬' },
  { href: '/contacts', label: 'Contacts', icon: '👥' },
  { href: '/campaigns', label: 'Campaigns', icon: '📨' },
  { href: '/ai', label: 'AI Stats', icon: '🤖' },
];

export default function Sidebar({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const showSidebar = !HIDDEN_ROUTES.includes(pathname);

  if (!showSidebar) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen" style={{ background: '#EAEDEE' }}>
      <aside className="fixed left-0 top-0 h-full w-[260px] flex flex-col z-50" style={{ background: '#075E54' }}>
        <div className="p-5 border-b" style={{ borderColor: 'rgba(255,255,255,0.12)' }}>
          <Link href="/dashboard" className="flex items-center gap-2 text-lg font-semibold text-white no-underline">
            <span className="text-xl">💬</span>
            <span>WhatsApp CRM</span>
          </Link>
          <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.55)' }}>Admin Dashboard</p>
        </div>

        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map(({ href, label, icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all no-underline"
                style={{
                  color: active ? '#FFFFFF' : 'rgba(255,255,255,0.7)',
                  background: active ? 'rgba(255,255,255,0.15)' : 'transparent',
                }}
                onMouseEnter={(e) => {
                  if (!active) {
                    (e.currentTarget as HTMLAnchorElement).style.background = 'rgba(255,255,255,0.08)';
                    (e.currentTarget as HTMLAnchorElement).style.color = '#FFFFFF';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    (e.currentTarget as HTMLAnchorElement).style.background = 'transparent';
                    (e.currentTarget as HTMLAnchorElement).style.color = 'rgba(255,255,255,0.7)';
                  }
                }}
              >
                <span className="text-base">{icon}</span>
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-3" style={{ borderTop: '1px solid rgba(255,255,255,0.12)' }}>
          <button
            onClick={() => {
              localStorage.removeItem('wacrm_token');
              window.location.href = '/';
            }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm cursor-pointer bg-transparent border-none transition-all"
            style={{ color: 'rgba(255,255,255,0.55)' }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = '#FFFFFF'; (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.08)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,0.55)'; (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
          >
            <span className="text-base">🚪</span>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <main className="ml-[260px] flex-1 p-6">{children}</main>
    </div>
  );
}
