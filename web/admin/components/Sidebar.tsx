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
    <div className="flex min-h-screen">
      <aside className="fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex flex-col z-50">
        <div className="p-5 border-b border-white/[.06]">
          <Link href="/dashboard" className="flex items-center gap-2 text-lg font-semibold text-white no-underline">
            <span className="text-xl">💬</span>
            <span>WhatsApp CRM</span>
          </Link>
          <p className="text-xs text-white/30 mt-1">Admin Dashboard</p>
        </div>

        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map(({ href, label, icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline"
            >
              <span className="text-base">{icon}</span>
              <span>{label}</span>
            </Link>
          ))}
        </nav>

        <div className="p-3 border-t border-white/[.06]">
          <button
            onClick={() => {
              localStorage.removeItem('wacrm_token');
              window.location.href = '/';
            }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"
          >
            <span className="text-base">🚪</span>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <main className="ml-[260px] flex-1">{children}</main>
    </div>
  );
}
