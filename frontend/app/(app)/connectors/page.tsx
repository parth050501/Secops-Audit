'use client';
import { useEffect, useState } from 'react';
import { getConnectorCatalog, getConnectors, addConnector, triggerScan, removeConnector } from '@/lib/api';
import { Plus, Zap, Trash2, X, Check, Clock } from 'lucide-react';

const CAT_ICONS: any = { network:'🔥', server:'🖥️', cloud:'☁️', identity:'🔑', siem:'📊', database:'🗄️', custom:'🔧' };

export default function ConnectorsPage() {
  const [catalog, setCatalog] = useState<any[]>([]);
  const [connected, setConnected] = useState<any[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [selected, setSelected] = useState<any>(null);
  const [form, setForm] = useState({ name:'', host:'', port:'', credentials:{} as any, realtime: true, collection_mode:'polling' });
  const [scanning, setScanning] = useState<number|null>(null);
  const [msg, setMsg] = useState('');
  const [role, setRole] = useState('');
  useEffect(() => { try { setRole(JSON.parse(localStorage.getItem('user')||'{}').role||''); } catch {} }, []);
  const canManage = ['admin','engineer'].includes(role);
  const [catFilter, setCatFilter] = useState('all');

  const load = async () => {
    try { const cat = await getConnectorCatalog(); setCatalog(cat.data); }
    catch (e) { console.error('catalog fetch failed', e); }
    try { const conn = await getConnectors(); setConnected(conn.data); }
    catch (e) { console.error('connectors fetch failed', e); }
  };
  useEffect(() => { load(); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await addConnector({
        name: form.name || selected.name,
        category: selected.category,
        connector_type: selected.type,
        host: form.credentials.host || form.host || null,
        port: (form.credentials.port || form.credentials.ssh_port || form.credentials.winrm_port || form.credentials.listen_port)
              ? parseInt(form.credentials.port || form.credentials.ssh_port || form.credentials.winrm_port || form.credentials.listen_port) : null,
        credentials: form.credentials,
        realtime: form.realtime,
        collection_mode: form.collection_mode,
      });
      setMsg(`${selected.name} connected. Initial scan running…`);
      setShowAdd(false); setSelected(null);
      load();
    } catch (e: any) { setMsg(e.response?.data?.detail || 'Failed'); }
  };

  const scan = async (id: number, name: string) => {
    setScanning(id); setMsg(`Scanning ${name}…`);
    await triggerScan(id);
    setTimeout(() => { setScanning(null); setMsg(`Scan complete for ${name}.`); load(); }, 2000);
  };

  const remove = async (id: number) => {
    await removeConnector(id); load();
  };

  const cats = ['all', ...Array.from(new Set(catalog.map(c => c.category)))];
  const filtered = catFilter === 'all' ? catalog : catalog.filter(c => c.category === catFilter);

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold">Connectors</h1>
            <p className="text-sm text-slate-400">Connect cloud accounts and API-based services directly — {connected.length} connected</p>
          </div>
          {canManage && <button onClick={() => setShowAdd(true)} className="btn btn-primary"><Plus className="w-4 h-4" /> Add Connector</button>}
        </div>

        <div className="mb-4 px-4 py-3 bg-blue-50 border border-blue-100 rounded-xl text-sm text-blue-800 flex items-start gap-2">
          <span className="text-base leading-none">💡</span>
          <span>Connectors link your <strong>cloud and API-based services</strong> (AWS, Azure, GCP, identity, SaaS) directly. To assess <strong>internal servers, databases, or network devices</strong>, use the <a href="/collectors" className="underline font-medium">Collectors</a> tab — they're reached securely through an on-prem collector and agents.</span>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* Connected */}
        {connected.length > 0 && (
          <div className="mb-6">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Connected Systems</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {connected.map(c => (
                <div key={c.id} className="card p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{CAT_ICONS[c.category]||'🔧'}</span>
                      <div>
                        <p className="text-sm font-semibold text-slate-800">{c.name}</p>
                        <p className="text-xs text-slate-400 capitalize">{c.connector_type.replace('_',' ')}</p>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => scan(c.id, c.name)} disabled={scanning===c.id}
                        className="btn text-xs py-1 px-2 text-teal-600">
                        <Zap className="w-3 h-3" />
                      </button>
                      <button onClick={() => remove(c.id)} className="btn text-xs py-1 px-2 text-red-400">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="badge badge-passing flex items-center gap-1">
                      <Check className="w-2.5 h-2.5" /> {c.status}
                    </span>
                    {c.realtime && <span className="badge badge-info flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />Real-time</span>}
                  </div>
                  {c.last_seen && (
                    <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {new Date(c.last_seen).toLocaleString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Add Connector Modal */}
        {showAdd && (
          <div className="fixed inset-0 bg-black/60 flex items-start justify-center z-50 p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl w-full max-w-2xl shadow-2xl my-8">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <h2 className="font-bold text-lg">{selected ? `Configure ${selected.name}` : 'Select a connector'}</h2>
                <button onClick={() => { setShowAdd(false); setSelected(null); }} className="btn py-1 px-2"><X className="w-4 h-4" /></button>
              </div>

              {!selected ? (
                <div className="p-6">
                  {/* Category filter */}
                  <div className="flex gap-2 flex-wrap mb-4">
                    {cats.map(c => (
                      <button key={c} onClick={() => setCatFilter(c)}
                        className={`px-3 py-1 text-xs rounded-full capitalize font-medium transition-colors ${catFilter===c?'bg-slate-900 text-white':'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                        {c === 'all' ? 'All' : `${CAT_ICONS[c]||''} ${c}`}
                      </button>
                    ))}
                  </div>
                  <div className="grid grid-cols-2 gap-2 max-h-96 overflow-y-auto">
                    {filtered.map(c => (
                      <button key={c.type} onClick={() => { setSelected(c); setForm(f => ({...f, name: c.name, host:'', port:'', credentials:{}})); }}
                        className="flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-teal-400 hover:bg-teal-50 transition-all text-left">
                        <span className="text-xl">{c.icon}</span>
                        <div>
                          <p className="text-sm font-medium text-slate-800">{c.name}</p>
                          <p className="text-xs text-slate-400 capitalize">{c.category}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <form onSubmit={submit} className="p-6 space-y-4">
                  <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl mb-4">
                    <span className="text-2xl">{selected.icon}</span>
                    <div>
                      <p className="font-semibold text-slate-800">{selected.name}</p>
                      <p className="text-xs text-slate-400">Collects: {selected.collection.join(', ')}</p>
                    </div>
                    <button type="button" onClick={() => setSelected(null)} className="ml-auto btn text-xs py-1 px-2">Change</button>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Display name</label>
                    <input className="input" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} required />
                  </div>
                  {/* Dynamic connection fields per connector type */}
                  {(selected.fields || []).map((field: any) => {
                    if (field.type === 'note') {
                      return (
                        <div key={field.name} className="text-xs text-slate-500 bg-blue-50 border border-blue-100 rounded-lg p-3">
                          {field.help}
                        </div>
                      );
                    }
                    return (
                      <div key={field.name}>
                        <label className="block text-xs font-medium text-slate-600 mb-1">
                          {field.label}{field.required && <span className="text-red-400"> *</span>}
                        </label>
                        {field.type === 'select' ? (
                          <select className="select" required={field.required}
                            value={form.credentials[field.name] || ''}
                            onChange={e=>setForm(f=>({...f,credentials:{...f.credentials,[field.name]:e.target.value}}))}>
                            <option value="">Select…</option>
                            {field.options?.map((o: string) => <option key={o} value={o}>{o}</option>)}
                          </select>
                        ) : (
                          <input
                            className="input"
                            type={field.type === 'password' ? 'password' : field.type === 'number' ? 'number' : 'text'}
                            placeholder={field.placeholder || ''}
                            required={field.required}
                            value={form.credentials[field.name] || ''}
                            onChange={e=>setForm(f=>({...f,credentials:{...f.credentials,[field.name]:e.target.value}}))}
                          />
                        )}
                        {field.help && <p className="text-[10px] text-slate-400 mt-1">{field.help}</p>}
                      </div>
                    );
                  })}
                  <div className="flex items-center gap-3">
                    <input type="checkbox" id="rt" checked={form.realtime} onChange={e=>setForm(f=>({...f,realtime:e.target.checked}))} className="w-4 h-4 text-teal-600" />
                    <label htmlFor="rt" className="text-sm text-slate-700">Enable real-time monitoring</label>
                  </div>
                  <div className="flex gap-2 justify-end pt-2">
                    <button type="button" onClick={() => setShowAdd(false)} className="btn">Cancel</button>
                    <button type="submit" className="btn btn-primary">Connect & Scan</button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
