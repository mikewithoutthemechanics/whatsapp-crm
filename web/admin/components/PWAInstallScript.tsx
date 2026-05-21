'use client';

import Script from 'next/script';

export function PWAInstallScript() {
  return (
    <Script id="pwa-sw-register" strategy="afterInteractive">
      {`
        (function() {
          if (!('serviceWorker' in navigator)) return;
          navigator.serviceWorker.register('/sw.js', { scope: '/' }).then(function(reg) {
            console.log('[PWA] SW registered:', reg.scope);
          }).catch(function(err) {
            console.warn('[PWA] SW registration failed:', err);
          });
        })();
      `}
    </Script>
  );
}
