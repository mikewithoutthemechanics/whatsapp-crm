import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Sidebar from '../components/Sidebar';
import { PWAInstallScript } from '../components/PWAInstallScript';

export const metadata: Metadata = { title: 'WhatsApp CRM SA — Admin' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <meta name="theme-color" content="#25D366" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="WA CRM" />
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body>
        <Sidebar>{children}</Sidebar>
        <PWAInstallScript />
      </body>
    </html>
  );
}
