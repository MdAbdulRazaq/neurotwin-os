import type { Metadata } from 'next';
import { Sora } from 'next/font/google';
import { Toaster } from 'react-hot-toast';
import './globals.css';

const sora = Sora({
  subsets: ['latin'],
  variable: '--font-sora',
  display: 'swap',
  weight: ['300', '400', '500', '600', '700', '800'],
});

export const metadata: Metadata = {
  title: 'NEUROTWIN OS — Your Digital Companion',
  description: 'A multimodal AI companion that remembers you, senses your emotions, and grows with you every day.',
  keywords: 'AI companion, digital twin, emotional AI, memory AI',
  openGraph: {
    title: 'NEUROTWIN OS',
    description: 'Your intelligent digital companion',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={sora.variable}>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#0f1522',
              color: 'rgba(255,255,255,0.9)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '12px',
              fontFamily: 'var(--font-sora)',
              fontSize: '14px',
            },
          }}
        />
      </body>
    </html>
  );
}
