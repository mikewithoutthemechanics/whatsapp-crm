import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import Sidebar from '../components/Sidebar';
import ServiceWorkerRegistration from '../components/ServiceWorkerRegistration';

export const metadata: Metadata = {
  title: 'WhatsApp CRM SA — Admin',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'WACRM',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: '#0B0B0F',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ServiceWorkerRegistration />
        <Sidebar>{children}</Sidebar>
      </body>
    </html>
  );
}
