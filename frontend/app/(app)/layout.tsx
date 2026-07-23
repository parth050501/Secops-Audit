'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';
import CodyWidget from '@/components/CodyWidget';
import { getMyTenant } from '@/lib/api';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [tenant, setTenant] = useState<any>(null);
  const [liveCount, setLiveCount] = useState(0);
  const [liveEvents, setLiveEvents] = useState<any[]>([]);
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) { router.push('/login'); return; }
    getMyTenant()
      .then(r => setTenant(r.data))
      .catch(() => {
        if (path !== '/onboarding') router.push('/onboarding');
      });
  }, []);

  // WebSocket for real-time events (optional — silently disabled if unavailable)
  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    try {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const host = window.location.host;  // includes port if any
      const token = localStorage.getItem('token');
      // Only connect if authenticated; pass the token so the server can scope
      // the stream to this user's tenant.
      if (!token) return;
      // In production (behind Caddy on 443) connect on the same host/port via /ws.
      // In local dev the backend is on :8000.
      const isLocal = host.includes('localhost') || host.includes('127.0.0.1');
      const wsBase = isLocal ? `${proto}://${window.location.hostname}:8000` : `${proto}://${host}`;
      ws = new WebSocket(`${wsBase}/ws/events?token=${encodeURIComponent(token)}`);
      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          if (data.type === 'governance_event') {
            setLiveCount(n => n + 1);
            setLiveEvents(prev => [data.event, ...prev].slice(0, 10));
            setTimeout(() => setLiveCount(n => Math.max(0, n - 1)), 8000);
          }
        } catch {}
      };
      // Suppress all connection errors — live events are a non-critical enhancement
      ws.onerror = (e) => { e.stopPropagation?.(); };
      ws.onclose = () => {};
    } catch {}
    return () => { closed = true; try { ws?.close(); } catch {} };
  }, []);

  if (!mounted) {
    return <div className="flex min-h-screen"><div className="w-56 bg-slate-900" /><div className="flex-1" /></div>;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar tenant={tenant} liveCount={liveCount} />
      <main className="flex-1 overflow-hidden relative">
        {/* QC environment banner */}
        <div className="bg-amber-400 text-amber-950 text-center text-xs font-semibold py-1 flex items-center justify-center gap-3">
          <span>⚠ QC ENVIRONMENT — Not for production data</span>
        </div>
        {/* Live event toast */}
        {liveEvents.length > 0 && (
          <div className="fixed top-4 right-4 z-50 space-y-2 max-w-xs">
            {liveEvents.slice(0,3).map((ev, i) => (
              <div key={i} className="bg-slate-900 text-white text-xs px-3 py-2 rounded-lg shadow-lg border border-teal-500/30 flex items-center gap-2 animate-pulse">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${ev.severity==='critical'?'bg-red-400':ev.severity==='high'?'bg-orange-400':'bg-yellow-400'}`} />
                <span className="truncate">{ev.title}</span>
              </div>
            ))}
          </div>
        )}
        {children}
      </main>
      <CodyWidget />
    </div>
  );
}
