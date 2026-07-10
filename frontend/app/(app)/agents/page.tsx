'use client';
import { useEffect, useState } from 'react';
import { listAgents, listCollectors } from '@/lib/api';
import { Server, CheckCircle2, XCircle, Clock, RefreshCw, Cpu, Database, Shield, HardDrive } from 'lucide-react';

const ICONS: Record<string, any> = {
  linux: Server, windows_server: HardDrive, postgres: Database,
  paloalto: Shield, default: Cpu,
};

function timeAgo(iso: string | null): string {
  if (!iso) return 'never';
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [collectors, setCollectors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [a, c] = await Promise.all([listAgents(), listCollectors()]);
      setAgents(a.data || []);
      setCollectors(c.data || []);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 15000); // refresh every 15s so status stays live
    return () => clearInterval(t);
  }, []);

  const connected = agents.filter(a => a.status === 'connected').length;
  const disconnected = agents.length - connected;

  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading agents…</div>;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2"><Cpu className="w-5 h-5 text-teal-600" /> Agents</h1>
            <p className="text-sm text-slate-400">Agents scanning your internal systems, reporting through your collectors.</p>
          </div>
          <button onClick={load} className="btn flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="card p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Total Agents</p>
            <p className="text-2xl font-bold text-slate-800">{agents.length}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Connected</p>
            <p className="text-2xl font-bold text-emerald-600">{connected}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide">Disconnected</p>
            <p className="text-2xl font-bold text-slate-400">{disconnected}</p>
          </div>
        </div>

        {/* Empty state */}
        {agents.length === 0 && (
          <div className="card p-8 text-center">
            <Cpu className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No agents have reported yet.</p>
            <p className="text-xs text-slate-400 mt-1">
              Deploy an agent on a system and point it at one of your collectors
              {collectors.length > 0 ? ` (e.g. ${collectors[0].name})` : ''}. Once it enrolls and reports, it appears here.
            </p>
          </div>
        )}

        {/* Agent list */}
        {agents.length > 0 && (
          <div className="space-y-3">
            {agents.map(a => {
              const Icon = ICONS[a.system_type] || ICONS.default;
              const isConnected = a.status === 'connected';
              return (
                <div key={a.id} className="card p-4">
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${isConnected ? 'bg-emerald-50' : 'bg-slate-100'}`}>
                      <Icon className={`w-5 h-5 ${isConnected ? 'text-emerald-600' : 'text-slate-400'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <p className="font-semibold text-slate-800">{a.name}</p>
                        {isConnected
                          ? <span className="inline-flex items-center gap-1 text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full"><CheckCircle2 className="w-3 h-3" /> Connected</span>
                          : <span className="inline-flex items-center gap-1 text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full"><XCircle className="w-3 h-3" /> Disconnected</span>}
                        <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded font-mono">{a.system_type}</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs text-slate-500 mt-2">
                        <div><span className="text-slate-400">Target:</span> {a.target || '—'}</div>
                        <div><span className="text-slate-400">Collector:</span> {a.collector_name || `#${a.collector_id}`}</div>
                        <div><span className="text-slate-400">Schedule:</span> {a.schedule || 'manual'}</div>
                        <div className="flex items-center gap-1"><Clock className="w-3 h-3 text-slate-300" /> seen {timeAgo(a.last_seen)}</div>
                      </div>
                      <div className="mt-2 pt-2 border-t border-slate-50 flex items-center gap-4 text-xs">
                        <span className="text-slate-400">Last scan:</span>
                        <span className="text-slate-600">{a.last_scan_at ? timeAgo(a.last_scan_at) : 'no scans yet'}</span>
                        {a.last_result && <span className="text-teal-600 font-medium">{a.last_result}</span>}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <p className="text-[11px] text-slate-400 mt-4 text-center">Status updates automatically. An agent shows "connected" if it has reported within the heartbeat window.</p>
      </div>
    </div>
  );
}
