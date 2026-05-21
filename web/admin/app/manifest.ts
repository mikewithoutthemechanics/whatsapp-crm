import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'WhatsApp CRM SA',
    short_name: 'WACRM',
    description: 'WhatsApp CRM for South African SMMEs',
    start_url: '/dashboard',
    display: 'standalone',
    background_color: '#0B0B0F',
    theme_color: '#6366F1',
    orientation: 'portrait',
    scope: '/',
    icons: [
      {
        src: '/icon.svg',
        sizes: 'any',
        type: 'image/svg+xml',
      },
    ],
  };
}
