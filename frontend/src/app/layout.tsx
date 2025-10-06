import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AI Offer Agent - IT Consulting Angebotsgenerator',
  description:
    'Generieren Sie professionelle IT-Consulting Angebote durch intelligente AI-gestützte Gespräche. Präzise Aufwandsschätzungen mit COCOMO-Modellen.',
  keywords: [
    'IT Consulting',
    'Angebotsgenerator',
    'AI',
    'Aufwandsschätzung',
    'COCOMO',
    'Projektmanagement',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          {children}
        </div>
      </body>
    </html>
  );
}
