'use client';
import { useEffect, useState } from 'react';
import { listCollectors, listAgents, listScanJobs, scanNow, registerCollector, deleteCollector } from '@/lib/api';
import { Server, Plus, X, Copy, CheckCircle2, XCircle, Clock, Play, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';

const SYSTEM_TYPES = [
  { key:'linux', label:'Linux (OpenSCAP)' },
  { key:'windows_server', label:'Windows Server' },
  { key:'postgres', label:'PostgreSQL' },
  { key:'paloalto', label:'Palo Alto Firewall' },
];

function StatusBadge({ status }: { status: string }) {
  const map: any = {
    connected: { c:'text-emerald-600 bg-emerald-50', i:<CheckCircle2 className="w-3.5 h-3.5"/>, t:'Connected' },
    disconnected: { c:'text-red-600 bg-red-50', i:<XCircle className="w-3.5 h-3.5"/>, t:'Disconnected' },
    pending: { c:'text-amber-600 bg-amber-50', i:<Clock className="w-3.5 h-3.5"/>, t:'Pending' },
  };
  const s = map[status] || map.pending;
  return <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${s.c}`}>{s.i}{s.t}</span>;
}

export default function CollectorsPage() {
  const [collectors, setCollectors] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [role, setRole] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState('');
  const [newToken, setNewToken] = useState('');
  const [copied, setCopied] = useState(false);
  const [showScan, setShowScan] = useState(false);
  const [scanType, setScanType] = useState('linux');
  const [scanTarget, setScanTarget] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  useEffect(() => { try { setRole(JSON.parse(localStorage.getItem('user')||'{}').role||''); } catch {} }, []);
  const isAdmin = role === 'admin';
  const canScan = ['admin','engineer'].includes(role);

  const load = () => {
    setLoading(true);
    Promise.all([
      listCollectors().then(r=>setCollectors(r.data)).catch(()=>{}),
      listAgents().then(r=>setAgents(r.data)).catch(()=>{}),
      listScanJobs().then(r=>setJobs(r.data)).catch(()=>{}),
    ]).finally(()=>setLoading(false));
  };
  useEffect(() => { load(); const t = setInterval(load, 30000); return ()=>clearInterval(t); }, []);

  const addCCE = async (e: React.FormEvent) => {
    e.preventDefault(); setErr('');
    try {
      const r = await registerCollector({ name });
      setNewToken(r.data.token);   // shown once
      setName('');
      load();
    } catch (e:any) { setErr(e.response?.data?.detail || 'Failed to register collector'); }
  };

  const doScan = async (e: React.FormEvent) => {
    e.preventDefault(); setErr('');
    try {
      await scanNow({ system_type: scanType, target: scanTarget || null });
      setMsg('Scan queued — the collector will run it on its next poll.');
      setShowScan(false); setScanTarget('');
      load();
    } catch (e:any) { setErr(e.response?.data?.detail || 'Failed to queue scan'); }
  };

  const copyToken = () => { navigator.clipboard.writeText(newToken); setCopied(true); setTimeout(()=>setCopied(false), 2000); };

  const closeAdd = () => { setShowAdd(false); setNewToken(''); setName(''); setErr(''); };

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2"><Server className="w-6 h-6 text-teal-600" /> Collectors (CCE)</h1>
            <p className="text-sm text-slate-400">On-prem collection engines that scan your internal systems and report findings.</p>
          </div>
          <div className="flex gap-2">
            <button onClick={load} className="btn"><RefreshCw className="w-4 h-4"/></button>
            {canScan && <button onClick={()=>setShowScan(true)} className="btn"><Play className="w-4 h-4"/> Scan now</button>}
            {isAdmin && <button onClick={()=>setShowAdd(true)} className="btn btn-primary bg-teal-600 hover:bg-teal-700"><Plus className="w-4 h-4"/> Add CCE</button>}
          </div>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-800 flex justify-between"><span>{msg}</span><button onClick={()=>setMsg('')}><X className="w-4 h-4"/></button></div>}

        {!isAdmin && (
          <div className="mb-4 text-xs text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> Only an admin can add a collector. {canScan ? 'You can trigger scans.' : 'Your role is read-only here.'}
          </div>
        )}

        {/* Collectors */}
        <div className="card overflow-hidden mb-5">
          <div className="px-5 py-3 border-b border-slate-100"><h2 className="font-semibold text-slate-800 text-sm">Collection Engines</h2></div>
          {loading ? <div className="p-5 text-sm text-slate-400">Loading…</div> :
            collectors.length === 0 ? <div className="p-8 text-center text-slate-400 text-sm">No collectors yet. {isAdmin && 'Click "Add CCE" to register one and get its enrollment token.'}</div> :
            <div className="divide-y divide-slate-50">
              {collectors.map(c => (
                <div key={c.id} className="px-5 py-3 flex items-center gap-3">
                  <Server className="w-5 h-5 text-slate-400"/>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-800">{c.name}</p>
                    <p className="text-xs text-slate-400">{c.version ? `v${c.version}` : 'not yet enrolled'} {c.last_seen ? `· last seen ${new Date(c.last_seen).toLocaleString()}` : ''}</p>
                  </div>
                  <StatusBadge status={c.status}/>
                  {isAdmin && (
                    <button
                      onClick={async () => {
                        if (!confirm(`Delete collector "${c.name}"? This also removes its agents. This cannot be undone.`)) return;
                        try {
                          await deleteCollector(c.id);
                          setMsg(`Collector "${c.name}" deleted.`);
                          listCollectors().then(r=>setCollectors(r.data)).catch(()=>{});
                          listAgents().then(r=>setAgents(r.data)).catch(()=>{});
                        } catch (e:any) { setErr(e.response?.data?.detail || 'Could not delete collector'); }
                      }}
                      className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500"
                      title="Delete collector">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>}
        </div>

        {/* Agents */}
        {agents.length > 0 && (
          <div className="card overflow-hidden mb-5">
            <div className="px-5 py-3 border-b border-slate-100"><h2 className="font-semibold text-slate-800 text-sm">Agents</h2></div>
            <div className="divide-y divide-slate-50">
              {agents.map(a => (
                <div key={a.id} className="px-5 py-3 flex items-center gap-3">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-800">{a.name} <span className="text-xs text-slate-400">({a.system_type})</span></p>
                    <p className="text-xs text-slate-400">{a.target}</p>
                  </div>
                  <StatusBadge status={a.status}/>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scan jobs */}
        <div className="card overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100"><h2 className="font-semibold text-slate-800 text-sm">Recent Scan Jobs</h2></div>
          {jobs.length === 0 ? <div className="p-6 text-center text-slate-400 text-sm">No scan jobs yet.</div> :
            <div className="divide-y divide-slate-50">
              {jobs.slice(0,15).map(j => (
                <div key={j.id} className="px-5 py-2.5 flex items-center gap-3 text-sm">
                  <span className="font-mono text-xs text-slate-400">#{j.id}</span>
                  <span className="flex-1">{j.system_type}{j.target?` · ${j.target}`:''}</span>
                  {j.findings_count != null && <span className="text-xs text-slate-500">{j.findings_count} findings</span>}
                  <span className={`text-xs px-2 py-0.5 rounded-full ${j.status==='done'?'bg-emerald-50 text-emerald-600':j.status==='error'?'bg-red-50 text-red-600':'bg-amber-50 text-amber-600'}`}>{j.status}</span>
                </div>
              ))}
            </div>}
        </div>
      </div>

      {/* Add CCE modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={closeAdd}>
          <div className="bg-white rounded-2xl w-full max-w-md" onClick={e=>e.stopPropagation()}>
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="font-bold">{newToken ? 'Collector token' : 'Add a collector (CCE)'}</h2>
              <button onClick={closeAdd}><X className="w-5 h-5 text-slate-400"/></button>
            </div>
            {!newToken ? (
              <form onSubmit={addCCE} className="p-6 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Collector name *</label>
                  <input className="input" required value={name} onChange={e=>setName(e.target.value)} placeholder="e.g. HQ-CCE1" />
                  <p className="text-[10px] text-slate-400 mt-1">A label to identify this engine (e.g. by site).</p>
                </div>
                {err && <p className="text-red-500 text-sm">{err}</p>}
                <div className="flex gap-2 justify-end">
                  <button type="button" onClick={closeAdd} className="btn">Cancel</button>
                  <button type="submit" className="btn btn-primary bg-teal-600 hover:bg-teal-700">Generate token</button>
                </div>
              </form>
            ) : (
              <div className="p-6 space-y-4">
                <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                  Copy this token now — it will not be shown again. Enter it (with the platform URL) when deploying the CCE.
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs bg-slate-900 text-teal-300 p-3 rounded-lg break-all">{newToken}</code>
                  <button onClick={copyToken} className="btn py-2 px-3">{copied ? <CheckCircle2 className="w-4 h-4 text-emerald-500"/> : <Copy className="w-4 h-4"/>}</button>
                </div>
                <div className="flex justify-end">
                  <button onClick={closeAdd} className="btn btn-primary bg-teal-600 hover:bg-teal-700">Done</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Scan now modal */}
      {showScan && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={()=>setShowScan(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md" onClick={e=>e.stopPropagation()}>
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="font-bold">Run a scan now</h2>
              <button onClick={()=>setShowScan(false)}><X className="w-5 h-5 text-slate-400"/></button>
            </div>
            <form onSubmit={doScan} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">System type *</label>
                <select className="select" value={scanType} onChange={e=>setScanType(e.target.value)}>
                  {SYSTEM_TYPES.map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Target (optional)</label>
                <input className="input" value={scanTarget} onChange={e=>setScanTarget(e.target.value)} placeholder="hostname / IP if applicable" />
              </div>
              <p className="text-[10px] text-slate-400">The collector picks this up on its next poll (within ~1 min) and runs it locally. Findings appear when complete.</p>
              {err && <p className="text-red-500 text-sm">{err}</p>}
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={()=>setShowScan(false)} className="btn">Cancel</button>
                <button type="submit" className="btn btn-primary bg-teal-600 hover:bg-teal-700">Queue scan</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
