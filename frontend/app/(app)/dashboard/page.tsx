'use client';
import { useEffect, useState } from 'react';
import { getDashboard, getMyTenant, getTickets, createTicket } from '@/lib/api';
import { AlertTriangle, Ticket, Plug, TrendingUp, ChevronRight, Zap, Clock } from 'lucide-react';

const SEV_COLOR: any = { critical:'bg-red-500', high:'bg-orange-400', medium:'bg-yellow-400', low:'bg-green-400' };
const CAT_LABELS: any = {
  access_control:'Access Control', identity:'Identity & Auth', encryption:'Encryption',
  logging:'Audit Logging', network_security:'Network Security', config:'Secure Config',
  patching:'Vuln & Patching', data_protection:'Data Protection', endpoint:'Endpoint',
  availability:'Availability', risk:'Risk Management',
};

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [tenant, setTenant] = useState<any>(null);
  const [tickets, setTickets] = useState<any[]>([]);
  const [creating, setCreating] = useState<number|null>(null);
  const [msg, setMsg] = useState('');

  const load = async () => {
    // Each call independent — one failing must not blank the whole dashboard
    try { const s = await getDashboard(); setStats(s.data); }
    catch (e) { console.error('dashboard stats failed', e); }
    try { const t = await getMyTenant(); setTenant(t.data); }
    catch (e) { console.error('tenant fetch failed', e); }
    try { const tk = await getTickets(); setTickets(tk.data); }
    catch (e) { console.error('tickets fetch failed', e); }
  };

  useEffect(() => { load(); }, []);

  // Poll every 15s for new events
  useEffect(() => {
    const id = setInterval(() => load(), 15000);
    return () => clearInterval(id);
  }, []);

  const handleCreateTicket = async (eventId: number) => {
    setCreating(eventId); setMsg('Creating ticket…');
    try {
      await createTicket(eventId);
      setMsg('Ticket created successfully.');
      load();
    } catch (e: any) { setMsg(e.response?.data?.detail || 'Failed'); }
    finally { setCreating(null); }
  };

  const score = stats?.score ?? 0;
  const scoreColor = score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-yellow-500' : 'text-red-500';
  const openTickets = tickets.filter(t => ['open','assigned','in_review'].includes(t.status)).length;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">{tenant?.name || 'Dashboard'}</h1>
            <p className="text-sm text-slate-400">
              {tenant?.active_framework?.toUpperCase().replace('_',' ')} Governance · {tenant?.industry}
              <span className="ml-2 inline-flex items-center gap-1 text-teal-600">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse inline-block" />
                Real-time monitoring
              </span>
            </p>
          </div>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* Score + Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          {/* Score ring */}
          <div className="card p-5 lg:col-span-1 flex flex-col items-center justify-center">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Compliance Score</p>
            <div className={`text-5xl font-bold ${scoreColor}`}>{score}</div>
            <div className="text-slate-400 text-sm">/ 100</div>
            <div className="w-full bg-slate-100 rounded-full h-2 mt-3">
              <div className="h-2 rounded-full transition-all" style={{width:`${score}%`, background: score>=80?'#10b981':score>=60?'#f59e0b':'#ef4444'}} />
            </div>
          </div>
          {[
            { label:'Critical Findings', value: stats?.critical, color:'text-red-600', icon: AlertTriangle, bg:'bg-red-50', href:'/governance' },
            { label:'High Findings',     value: stats?.high,     color:'text-orange-500', icon: AlertTriangle, bg:'bg-orange-50', href:'/governance' },
            { label:'Open Tickets',      value: openTickets,     color:'text-blue-600', icon: Ticket, bg:'bg-blue-50', href:'/tickets' },
            { label:'Connectors',        value: stats?.connectors, color:'text-teal-600', icon: Plug, bg:'bg-teal-50', href:'/connectors' },
          ].map(({ label, value, color, icon: Icon, bg, href }) => (
            <a key={label} href={href} className="card p-5 hover:shadow-md hover:border-slate-300 transition-all block">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">{label}</p>
                  <p className={`text-3xl font-bold ${color}`}>{value ?? '—'}</p>
                </div>
                <div className={`w-9 h-9 ${bg} rounded-xl flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${color}`} />
                </div>
              </div>
            </a>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
          {/* Recent events */}
          <div className="card lg:col-span-2">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
                Live Governance Events
              </h2>
              <a href="/governance" className="text-xs text-teal-600 hover:underline flex items-center gap-0.5">
                All events <ChevronRight className="w-3 h-3" />
              </a>
            </div>
            <div className="divide-y divide-slate-50 max-h-72 overflow-y-auto">
              {!stats?.recent_events?.length && (
                <div className="px-5 py-8 text-center text-sm text-slate-400">
                  No events yet — add a connector to start collecting data.
                </div>
              )}
              {stats?.recent_events?.map((ev: any) => (
                <div key={ev.id} className="px-5 py-3 flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${SEV_COLOR[ev.severity]||'bg-slate-300'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-700 truncate">{ev.title}</p>
                    <p className="text-xs text-slate-400">{CAT_LABELS[ev.category]||ev.category}</p>
                  </div>
                  <span className={`badge badge-${ev.severity} flex-shrink-0`}>{ev.severity}</span>
                  {ev.status === 'open' && (
                    <button onClick={() => handleCreateTicket(ev.id)}
                      disabled={creating === ev.id}
                      className="btn text-xs py-1 px-2 flex-shrink-0">
                      <Ticket className="w-3 h-3" />
                      {creating === ev.id ? '…' : 'Ticket'}
                    </button>
                  )}
                  {ev.status === 'ticketed' && <span className="badge badge-info flex-shrink-0">Ticketed</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Category breakdown */}
          <div className="card">
            <div className="px-5 py-4 border-b border-slate-100">
              <h2 className="text-sm font-semibold">Findings by Category</h2>
            </div>
            <div className="p-4 space-y-2.5">
              {!stats?.categories || !Object.keys(stats.categories).length ? (
                <p className="text-xs text-slate-400 text-center py-4">No data yet</p>
              ) : Object.entries(stats.categories).sort((a:any,b:any)=>b[1]-a[1]).map(([cat, count]: any) => {
                const max = Math.max(...Object.values(stats.categories) as number[]);
                return (
                  <div key={cat}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-500">{CAT_LABELS[cat]||cat}</span>
                      <span className="font-semibold text-slate-700">{count}</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-teal-500" style={{width:`${(count/max)*100}%`}} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Recent tickets */}
        <div className="card">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent Tickets</h2>
            <a href="/tickets" className="text-xs text-teal-600 hover:underline">View all</a>
          </div>
          <div className="divide-y divide-slate-50">
            {!tickets.length ? (
              <div className="px-5 py-6 text-center text-sm text-slate-400">No tickets yet</div>
            ) : tickets.slice(0,5).map(t => (
              <a key={t.id} href={`/tickets/${t.id}`} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50 block">
                <span className="text-xs font-mono text-slate-400 flex-shrink-0">{t.ref}</span>
                <span className="text-sm text-slate-700 flex-1 truncate">{t.title}</span>
                <span className={`badge badge-${t.severity} flex-shrink-0`}>{t.severity}</span>
                <span className={`badge badge-${t.status} flex-shrink-0`}>{t.status.replace('_',' ')}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
