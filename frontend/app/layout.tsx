import type { Metadata } from 'next';
import './globals.css';
import ErrorSuppressor from '@/components/ErrorSuppressor';

export const metadata: Metadata = { title: 'SecOps AI', description: 'Governance & Compliance Platform' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-slate-50 text-slate-900" suppressHydrationWarning>
        <ErrorSuppressor />
        {children}
      </body>
    </html>
  );
}
