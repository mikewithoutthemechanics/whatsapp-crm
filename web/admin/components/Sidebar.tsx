'use client';

import '../app/globals.css';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

const HIDDEN_ROUTES = ['/login'];

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: '🏠' },
  { href: '/business', label: 'Business', icon: '🏢' },
  { href: '/conversations', label: 'Chats', icon: '💬' },
  { href: '/contacts', label: 'Contacts', icon: '👥' },
  { href: '/campaigns', label: 'Campaigns', icon: '📨' },
  { href: '/ai', label: 'AI Stats', icon: '🤖' },
  { href: '/import', label: 'Imports', icon: '📥' },
];

export default function Sidebar({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const showSidebar = !HIDDEN_ROUTES.includes(pathname);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!showSidebar) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex fixed left-0 top-0 h-full w-[260px] bg-black/40 backdrop-blur-xl border-r border-white/[.06] flex-col z-50">
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

      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-14 bg-black/60 backdrop-blur-xl border-b border-white/[.06] flex items-center justify-between px-4 z-50">
        <Link href="/dashboard" className="flex items-center gap-2 text-white font-semibold no-underline">
          <span className="text-xl">💬</span>
          <span>WhatsApp CRM</span>
        </Link>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="text-white text-2xl bg-transparent border-none cursor-pointer p-1"
          aria-label="Menu"
        >
          {mobileMenuOpen ? '✕' : '☰'}
        </button>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 bg-black/90 backdrop-blur-xl z-40 pt-16 px-4 pb-4">
          <nav className="space-y-2">
            {navItems.map(({ href, label, icon }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-4 py-3 rounded-lg text-base text-white/70 hover:text-white hover:bg-white/[.06] transition-all no-underline"
              >
                <span className="text-xl">{icon}</span>
                <span>{label}</span>
              </Link>
            ))}
          </nav>
          <div className="mt-4 pt-4 border-t border-white/[.06]">
            <button
              onClick={() => {
                localStorage.removeItem('wacrm_token');
                window.location.href = '/';
              }}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-base text-white/50 hover:text-white hover:bg-white/[.06] transition-all cursor-pointer bg-transparent border-none"
            >
              <span className="text-xl">🚪</span>
              <span>Logout</span>
            </button>
          </div>
        </div>
      )}

      {/* Mobile Bottom Nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-black/80 backdrop-blur-xl border-t border-white/[.06] flex items-center justify-around z-50" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        {navItems.map(({ href, icon, label }) => {
          const active = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center gap-0.5 py-1 px-3 no-underline ${active ? 'text-white' : 'text-white/40'}`}
            >
              <span className="text-xl">{icon}</span>
              <span className="text-[10px]">{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Main Content */}
      <main className="md:ml-[260px] flex-1 pt-16 md:pt-0 pb-20 md:pb-0">
        <div className="p-4 md:p-6">{children}</div>
      </main>
    </div>
  );
}
