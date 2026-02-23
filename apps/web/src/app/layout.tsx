import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Volo — AI Life OS',
  description: 'One agent. Total control. Your AI operating system for code, trading, communications, and life.',
  keywords: ['AI assistant', 'life OS', 'productivity', 'trading', 'coding', 'agent'],
  authors: [{ name: 'Volo' }],
  openGraph: {
    title: 'Volo — AI Life OS',
    description: 'One agent. Total control.',
    type: 'website',
  },
};

export const viewport: Viewport = {
  themeColor: '#09090b',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-surface-dark-0 text-zinc-200 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
