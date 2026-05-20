import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Sidebar from '../components/Sidebar';

export const metadata: Metadata = { title: 'WhatsApp CRM SA — Admin' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Sidebar>{children}</Sidebar>
      </body>
    </html>
  );
}
