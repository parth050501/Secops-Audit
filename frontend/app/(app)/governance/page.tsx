'use client';
import { useEffect, useState } from 'react';
import { getEvents, getControls, createTicket } from '@/lib/api';
import { Ticket, Filter, CheckCircle, XCircle } from 'lucide-react';

const CAT_LABELS: any = {
  access_control:'Access Control', identity:'Identity & Auth', encryption:'Encryption',
  logging:'Audit Logging', network_security:'Network Security', config:'Secure Config',
  patching:'Vuln & Patching', data_protection:'Data Protection', endpoint:'Endpoint',
  availability:'Availability', risk:'Risk Management',
};

export default function GovernancePage() {
  const [tab, setTab] = useState<'events'|'controls'>('events');
  const [events, setEvents] = useState<any[]>([]);
  const [controls, setControls] = useState<any[]>([]);
  const [sevFilter, setSevFilter] = useState('all');
  const [catFilter, setCatFilter] = useState('all');
  const [creating, setCreating] = useState<number|null>(null);
  const [msg, setMsg] = useState('');

  const load = async () => {
    try { const ev = await getEvents(); setEvents(ev.data); }
    catch (e) { console.error('events fetch failed', e); }
    try { const ctrl = await getControls(); setControls(ctrl.data); }
    catch (e) { console.error('controls fetch failed', e); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { const id = setInterval(load, 20000); return () => clearInterval(id); }, []);

  const handleTicket = async (eventId: number) => {
    setCreating(eventId); setMsg('Generating AI ticket…');
    try { await createTicket(eventId); setMsg('Ticket created.'); load(); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Failed'); }
    finally { setCreating(null); }
  };

  const filteredEvents = events.filter(e =>
    (sevFilter === 'all' || e.severity === sevFilter) &&
    (catFilter === 'all' || e.category === catFilter)
  );
  const passing = controls.filter(c => c.status === 'passing').length;
  const failing = controls.filter(c => c.status === 'failing').length;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-bold">Governance</h1>
          <p className="text-sm text-slate-400">Real-time and scheduled findings mapped to your compliance framework</p>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* Tabs */}
        <div className="flex gap-1 mb-5 bg-slate-100 p-1 rounded-xl w-fit">
          {(['events','controls'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg capitalize transition-colors ${tab===t?'bg-white shadow-sm text-slate-900':'text-slate-500 hover:text-slate-700'}`}>
              {t} {t==='events'?`(${events.filter(e=>e.status==='open').length})`:
                    `${passing}✓ ${failing}✗`}
            </button>
          ))}
        </div>

        {tab === 'events' && (
          <div>
            {/* Filters */}
            <div className="flex gap-2 flex-wrap mb-4">
              {['all','critical','high','medium','low'].map(s => (
                <button key={s} onClick={() => setSevFilter(s)}
                  className={`px-3 py-1 text-xs rounded-full capitalize font-medium transition-colors ${sevFilter===s?'bg-slate-900 text-white':'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}>
                  {s}
                </button>
              ))}
              <div className="h-5 w-px bg-slate-200 self-center mx-1" />
              {['all',...Array.from(new Set(events.map(e=>e.category)))].map(c => (
                <button key={c} onClick={() => setCatFilter(c)}
                  className={`px-3 py-1 text-xs rounded-full capitalize font-medium transition-colors ${catFilter===c?'bg-slate-900 text-white':'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}>
                  {c==='all'?'All categories':CAT_LABELS[c]||c}
                </button>
              ))}
            </div>

            {/* Severity summary bar (risk-forward, Wiz-style) */}
            <div className="grid grid-cols-4 gap-3 mb-4">
              {([
                { key: 'critical', label: 'Critical', color: '#dc2626', bg: '#fef2f2' },
                { key: 'high', label: 'High', color: '#ea580c', bg: '#fff7ed' },
                { key: 'medium', label: 'Medium', color: '#d97706', bg: '#fffbeb' },
                { key: 'low', label: 'Low', color: '#16a34a', bg: '#f0fdf4' },
              ] as const).map(s => {
                const count = events.filter(e => e.status === 'open' && e.severity === s.key).length;
                const active = sevFilter === s.key;
                return (
                  <button key={s.key} onClick={() => setSevFilter(active ? 'all' : s.key)}
                    className={`rounded-xl p-3 text-left transition-all border ${active ? 'ring-2 ring-offset-1' : 'border-slate-100 hover:border-slate-200'}`}
                    style={{ background: s.bg, borderColor: active ? s.color : undefined, ...(active ? { '--tw-ring-color': s.color } as any : {}) }}>
                    <div className="text-2xl font-bold" style={{ color: s.color }}>{count}</div>
                    <div className="text-xs font-medium text-slate-500">{s.label}</div>
                  </button>
                );
              })}
            </div>

            <div className="card divide-y divide-slate-50">
              {!filteredEvents.length && (
                <div className="px-5 py-10 text-center text-sm text-slate-400">No events matching filters.</div>
              )}
              {filteredEvents.map(ev => (
                <div key={ev.id} className="px-5 py-4 hover:bg-slate-50/50 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                      ev.severity==='critical'?'bg-red-500':ev.severity==='high'?'bg-orange-400':ev.severity==='medium'?'bg-yellow-400':'bg-green-400'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className={`badge badge-${ev.severity}`}>{ev.severity}</span>
                        <span className="badge badge-info">{CAT_LABELS[ev.category]||ev.category}</span>
                        <span className="text-xs text-slate-400">{ev.source_type}</span>
                        {ev.status==='ticketed' && <span className="badge badge-accepted">Ticketed</span>}
                      </div>
                      <p className="text-sm font-medium text-slate-800">{ev.title}</p>
                      {ev.description && <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{ev.description}</p>}
                      {ev.framework_mappings && Object.entries(ev.framework_mappings).length > 0 && (
                        <div className="flex gap-1 flex-wrap mt-1">
                          {Object.entries(ev.framework_mappings).map(([fw, controls]: any) =>
                            (controls as string[]).map(c => (
                              <span key={`${fw}-${c}`} className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded font-mono">{fw.toUpperCase().replace('_',' ')} {c}</span>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-1 flex-shrink-0">
                      <p className="text-xs text-slate-400 text-right">{ev.occurred_at ? new Date(ev.occurred_at).toLocaleString() : ''}</p>
                      {ev.status === 'open' && (
                        <button onClick={() => handleTicket(ev.id)} disabled={creating===ev.id}
                          className="btn text-xs py-1 px-2">
                          <Ticket className="w-3 h-3" />
                          {creating===ev.id ? 'Creating…' : 'Create Ticket'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'controls' && (
          <>
            {controls.length > 0 && (
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="card p-3">
                  <div className="text-2xl font-bold text-slate-800">{controls.length}</div>
                  <div className="text-xs text-slate-500">Total controls</div>
                </div>
                <div className="card p-3">
                  <div className="text-2xl font-bold text-emerald-600">{controls.filter(c => c.status === 'passing').length}</div>
                  <div className="text-xs text-slate-500">Passing</div>
                </div>
                <div className="card p-3">
                  <div className="text-2xl font-bold text-red-600">{controls.filter(c => c.status !== 'passing').length}</div>
                  <div className="text-xs text-slate-500">Failing</div>
                </div>
              </div>
            )}
            <div className="card divide-y divide-slate-50">
              {!controls.length && (
                <div className="px-5 py-10 text-center text-sm text-slate-400">No controls — connect a system and run a scan.</div>
              )}
              {controls.map(ctrl => {
                const passing = ctrl.status === 'passing';
                return (
                  <div key={ctrl.id} className="px-5 py-3.5 flex items-center gap-3 hover:bg-slate-50/50 transition-colors">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${passing ? 'bg-emerald-50' : 'bg-red-50'}`}>
                      {passing
                        ? <CheckCircle className="w-5 h-5 text-emerald-500" />
                        : <XCircle className="w-5 h-5 text-red-500" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs font-mono font-bold text-slate-500">{ctrl.id}</span>
                        <span className="text-[10px] text-slate-400 capitalize px-1.5 py-0.5 bg-slate-100 rounded">{ctrl.weight}</span>
                      </div>
                      <p className="text-sm font-medium text-slate-800 truncate">{ctrl.title}</p>
                      {ctrl.open_findings > 0 && (
                        <div className="mt-1 space-y-0.5">
                          {ctrl.finding_titles.map((t: string, i: number) => (
                            <p key={i} className="text-xs text-red-600 flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-red-400" />{t}</p>
                          ))}
                          {ctrl.open_findings > 3 && <p className="text-xs text-slate-400 pl-3">+{ctrl.open_findings-3} more finding(s)</p>}
                        </div>
                      )}
                    </div>
                    <div className="flex-shrink-0">
                      {passing
                        ? <span className="inline-flex items-center gap-1 text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full font-medium">Pass</span>
                        : <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2.5 py-1 rounded-full font-medium">{ctrl.open_findings} Fail</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
