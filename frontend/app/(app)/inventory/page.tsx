'use client';
import { useEffect, useState } from 'react';
import { listAgents, listCollectors, listDevices, deviceCatalog, createDevice, deleteDevice, scanDevice } from '@/lib/api';
import { Server, CheckCircle2, XCircle, Clock, RefreshCw, Cpu, Database, Shield, HardDrive, Boxes, Plus, X, Trash2, Play, Wifi, WifiOff, Globe } from 'lucide-react';

const AGENT_ICONS: Record<string, any> = {
  linux: Server, windows_server: HardDrive, postgres: Database,
  mysql: Database, mssql: Database, paloalto: Shield, default: Cpu,
};

function timeAgo(iso: string | null): string {
  if (!iso) return 'never';
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

export default function InventoryPage() {
  const [subtab, setSubtab] = useState<'devices' | 'agents'>('devices');
  const [agents, setAgents] = useState<any[]>([]);
  const [collectors, setCollectors] = useState<any[]>([]);
  const [devices, setDevices] = useState<any[]>([]);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');
  const [role, setRole] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  const emptyForm = { name: '', device_type: 'paloalto', host: '', port: '', api_key: '', username: '', password: '', via_collector: true, collector_id: 0 };
  const [form, setForm] = useState<any>(emptyForm);

  const load = async () => {
    try {
      const [a, c, d, cat] = await Promise.all([listAgents(), listCollectors(), listDevices(), deviceCatalog()]);
      setAgents(a.data || []); setCollectors(c.data || []); setDevices(d.data || []); setCatalog(cat.data || []);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    try { setRole(JSON.parse(localStorage.getItem('user') || '{}').role || ''); } catch {}
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);

  const canManage = role === 'admin' || role === 'engineer';

  const openAdd = () => {
    setForm({ ...emptyForm, collector_id: collectors[0]?.id || 0 });
    setShowAdd(true);
  };

  const saveDevice = async () => {
    if (!form.name.trim() || !form.host.trim()) { setMsg('Name and host/IP are required'); return; }
    if (form.via_collector && !form.collector_id) { setMsg('Select which collector reaches this device'); return; }
    const credentials: any = {};
    if (form.api_key) credentials.api_key = form.api_key;
    if (form.username) credentials.username = form.username;
    if (form.password) credentials.password = form.password;
    try {
      await createDevice({
        name: form.name, device_type: form.device_type, host: form.host,
        port: form.port ? parseInt(form.port) : null,
        credentials: Object.keys(credentials).length ? credentials : null,
        via_collector: form.via_collector,
        collector_id: form.via_collector ? form.collector_id : null,
      });
      setMsg(`Device "${form.name}" added.`); setShowAdd(false); load();
    } catch (e: any) { setMsg(e.response?.data?.detail || 'Could not add device'); }
  };

  const removeDevice = async (d: any) => {
    if (!confirm(`Delete device "${d.name}"?`)) return;
    try { await deleteDevice(d.id); setMsg('Device deleted.'); load(); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Could not delete'); }
  };

  const runScan = async (d: any) => {
    try { const r = await scanDevice(d.id); setMsg(r.data.note || 'Scan requested.'); load(); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Could not scan'); }
  };

  const catalogType = (t: string) => catalog.find(c => c.type === t);

  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading inventory…</div>;

  const agentsConnected = agents.filter(a => a.status === 'connected').length;
  const devicesReachable = devices.filter(d => d.status === 'reachable').length;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2"><Boxes className="w-5 h-5 text-teal-600" /> Inventory</h1>
            <p className="text-sm text-slate-400">Everything being assessed — network devices reached by your collectors, and agents on your systems.</p>
          </div>
          <button onClick={load} className="btn flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-100 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* Sub-tabs */}
        <div className="flex gap-1 mb-6 border-b border-slate-200">
          {[
            { key: 'devices', label: `Devices (${devices.length})`, icon: Shield },
            { key: 'agents', label: `Agents (${agents.length})`, icon: Cpu },
          ].map(({ key, label, icon: Icon }) => (
            <button key={key} onClick={() => setSubtab(key as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${subtab === key ? 'border-teal-500 text-teal-700 font-medium' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
              <Icon className="w-4 h-4" /> {label}
            </button>
          ))}
        </div>

        {/* DEVICES SUB-TAB */}
        {subtab === 'devices' && (
          <>
            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-4">
                <div className="card px-4 py-2"><span className="text-xs text-slate-400">Total</span><div className="text-lg font-bold">{devices.length}</div></div>
                <div className="card px-4 py-2"><span className="text-xs text-slate-400">Reachable</span><div className="text-lg font-bold text-emerald-600">{devicesReachable}</div></div>
              </div>
              {canManage && <button onClick={openAdd} className="btn btn-primary flex items-center gap-2 text-sm"><Plus className="w-4 h-4" /> Add Device</button>}
            </div>

            {devices.length === 0 ? (
              <div className="card p-8 text-center">
                <Shield className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No devices registered yet.</p>
                <p className="text-xs text-slate-400 mt-1">Add a firewall, switch, or appliance. If it's on a private network, a collector will reach it; if public, it's scanned directly.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {devices.map(d => {
                  const reachable = d.status === 'reachable';
                  const ct = catalogType(d.device_type);
                  return (
                    <div key={d.id} className="card p-4">
                      <div className="flex items-start gap-4">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${reachable ? 'bg-emerald-50' : 'bg-slate-100'}`}>
                          <Shield className={`w-5 h-5 ${reachable ? 'text-emerald-600' : 'text-slate-400'}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <p className="font-semibold text-slate-800">{d.name}</p>
                            <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded font-mono">{ct?.name || d.device_type}</span>
                            {d.via_collector
                              ? <span className="inline-flex items-center gap-1 text-[10px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded-full"><Wifi className="w-2.5 h-2.5" /> via {d.collector_name || 'collector'}</span>
                              : <span className="inline-flex items-center gap-1 text-[10px] text-violet-600 bg-violet-50 px-1.5 py-0.5 rounded-full"><Globe className="w-2.5 h-2.5" /> direct</span>}
                            {ct && !ct.parser_ready && <span className="text-[10px] px-1.5 py-0.5 bg-amber-50 text-amber-600 rounded-full">scanner pending validation</span>}
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs text-slate-500 mt-1">
                            <div><span className="text-slate-400">Host:</span> {d.host}{d.port ? `:${d.port}` : ''}</div>
                            <div className="flex items-center gap-1">
                              {reachable ? <Wifi className="w-3 h-3 text-emerald-500" /> : <WifiOff className="w-3 h-3 text-slate-300" />}
                              {d.status}
                            </div>
                            <div><span className="text-slate-400">Last scan:</span> {d.last_scan_at ? timeAgo(d.last_scan_at) : 'never'}</div>
                            <div>{d.last_result && <span className="text-teal-600 font-medium">{d.last_result}</span>}</div>
                          </div>
                          {d.last_error && <p className="text-[11px] text-red-500 mt-1">{d.last_error}</p>}
                        </div>
                        {canManage && (
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <button onClick={() => runScan(d)} className="btn btn-primary text-xs py-1 px-2 flex items-center gap-1"><Play className="w-3 h-3" /> Scan</button>
                            {role === 'admin' && <button onClick={() => removeDevice(d)} className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            <p className="text-[11px] text-slate-400 mt-4 text-center">Devices on a private network are reached by an on-prem collector; public devices are scanned directly. Each device type's scanner is validated against real hardware before findings flow.</p>
          </>
        )}

        {/* AGENTS SUB-TAB */}
        {subtab === 'agents' && (
          <>
            <div className="flex gap-4 mb-4">
              <div className="card px-4 py-2"><span className="text-xs text-slate-400">Total</span><div className="text-lg font-bold">{agents.length}</div></div>
              <div className="card px-4 py-2"><span className="text-xs text-slate-400">Connected</span><div className="text-lg font-bold text-emerald-600">{agentsConnected}</div></div>
            </div>
            {agents.length === 0 ? (
              <div className="card p-8 text-center">
                <Cpu className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No agents have reported yet.</p>
                <p className="text-xs text-slate-400 mt-1">Deploy an agent on a system and point it at one of your collectors.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {agents.map(a => {
                  const Icon = AGENT_ICONS[a.system_type] || AGENT_ICONS.default;
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
                            <div className="flex items-center gap-1"><Clock className="w-3 h-3 text-slate-300" /> seen {timeAgo(a.last_seen)}</div>
                            <div>{a.last_result && <span className="text-teal-600 font-medium">{a.last_result}</span>}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>

      {/* Add device modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white">
              <h2 className="font-bold text-slate-800">Add Device</h2>
              <button onClick={() => setShowAdd(false)} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Device type</label>
                <select className="input" value={form.device_type} onChange={e => setForm({ ...form, device_type: e.target.value })}>
                  {catalog.map(c => <option key={c.type} value={c.type}>{c.name} — {c.access}{c.parser_ready ? '' : ' (scanner pending)'}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs font-medium text-slate-600 mb-1 block">Name</label>
                  <input className="input" placeholder="Perimeter Firewall" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
                <div><label className="text-xs font-medium text-slate-600 mb-1 block">Host / IP</label>
                  <input className="input" placeholder="10.0.0.1" value={form.host} onChange={e => setForm({ ...form, host: e.target.value })} /></div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Port (optional)</label>
                <input className="input w-32" placeholder="443" value={form.port} onChange={e => setForm({ ...form, port: e.target.value })} />
              </div>

              {/* Reach model */}
              <div className="border border-slate-200 rounded-lg p-3 space-y-2">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.via_collector} onChange={e => setForm({ ...form, via_collector: e.target.checked })} />
                  Scan via collector (device is on a private/internal network)
                </label>
                {form.via_collector ? (
                  <div>
                    <label className="text-xs font-medium text-slate-600 mb-1 block">Which collector reaches it?</label>
                    {collectors.length === 0 ? (
                      <p className="text-xs text-amber-600">No collectors registered yet — add one in the Collectors tab first.</p>
                    ) : (
                      <select className="input" value={form.collector_id} onChange={e => setForm({ ...form, collector_id: parseInt(e.target.value) })}>
                        <option value={0}>Select a collector…</option>
                        {collectors.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                      </select>
                    )}
                  </div>
                ) : (
                  <p className="text-[11px] text-violet-600">Public device — the platform will reach it directly, no collector needed.</p>
                )}
              </div>

              {/* Credentials */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-slate-600 block">Read-only credentials</label>
                <input className="input" placeholder="API key (e.g. Palo Alto, Fortinet)" value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })} />
                <div className="grid grid-cols-2 gap-2">
                  <input className="input" placeholder="Username (SSH devices)" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} />
                  <input type="password" className="input" placeholder="Password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
                </div>
                <p className="text-[11px] text-slate-400">Use a dedicated read-only account. Credentials are stored encrypted.</p>
              </div>
            </div>
            <div className="px-5 py-4 border-t border-slate-100 flex justify-end gap-2 sticky bottom-0 bg-white">
              <button onClick={() => setShowAdd(false)} className="btn text-sm">Cancel</button>
              <button onClick={saveDevice} className="btn btn-primary text-sm">Add Device</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
