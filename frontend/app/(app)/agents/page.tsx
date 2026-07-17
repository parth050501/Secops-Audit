'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// Agents moved under the unified Inventory tab.
export default function AgentsRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/inventory'); }, [router]);
  return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Redirecting to Inventory…</div>;
}
