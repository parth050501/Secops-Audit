'use client';
import { useEffect, useState } from 'react';
import { getCompliance, getComplianceHeatmap, getComplianceDetail, captureSnapshot, getComplianceHistory } from '@/lib/api';
import { ShieldCheck, ChevronDown, ChevronRight, CheckCircle2, XCircle, Grid3x3, ListTree, LayoutGrid, Search, TrendingUp, Camera } from 'lucide-react';

// readiness -> color (green good, red bad) — light theme, matches GRCBridge
function readinessColor(pct: number): string {
  if (pct >= 90) return '#16a34a';
  if (pct >= 75) return '#65a30d';
  if (pct >= 50) return '#d97706';
  if (pct >= 30) return '#ea580c';
  return '#dc2626';
}
function readinessBg(pct: number): string {
  if (pct >= 90) return '#dcfce7';
  if (pct >= 75) return '#ecfccb';
  if (pct >= 50) return '#fef3c7';
  if (pct >= 30) return '#ffedd5';
  return '#fee2e2';
}

function Bar({ pct }: { pct: number }) {
  return (
    <div className="w-24 h-2 rounded-full bg-slate-100 overflow-hidden inline-block align-middle">
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: readinessColor(pct) }} />
    </div>
  );
}

function TrendCard({ fw }: { fw: any }) {
  const pts = fw.points || [];
  if (pts.length === 0) return null;
  const W = 640, H = 160, pad = 30;
  const latest = pts[pts.length - 1];
  const first = pts[0];
  const delta = pts.length > 1 ? Math.round((latest.readiness_pct - first.readiness_pct) * 10) / 10 : 0;

  // x by index, y by readiness (0-100)
  const xFor = (i: number) => pad + (pts.length === 1 ? (W - 2 * pad) / 2 : (i / (pts.length - 1)) * (W - 2 * pad));
  const yFor = (v: number) => H - pad - (v / 100) * (H - 2 * pad);
  const line = pts.map((p: any, i: number) => `${i === 0 ? 'M' : 'L'} ${xFor(i)} ${yFor(p.readiness_pct)}`).join(' ');
  const area = `${line} L ${xFor(pts.length - 1)} ${H - pad} L ${xFor(0)} ${H - pad} Z`;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="font-semibold text-slate-800">{fw.name}</span>
          <span className="text-xs text-slate-400 ml-2">{pts.length} snapshot{pts.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-2xl font-bold text-teal-600">{latest.readiness_pct}%</span>
          {pts.length > 1 && (
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${delta >= 0 ? 'text-emerald-600 bg-emerald-50' : 'text-red-600 bg-red-50'}`}>
              {delta >= 0 ? '▲' : '▼'} {Math.abs(delta)}%
            </span>
          )}
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 160 }}>
        {[0, 25, 50, 75, 100].map(g => (
          <g key={g}>
            <line x1={pad} y1={yFor(g)} x2={W - pad} y2={yFor(g)} stroke="#f1f5f9" strokeWidth="1" />
            <text x={pad - 6} y={yFor(g) + 3} textAnchor="end" fontSize="9" fill="#cbd5e1">{g}</text>
          </g>
        ))}
        <path d={area} fill="#0f8b8d" opacity="0.08" />
        <path d={line} fill="none" stroke="#0f8b8d" strokeWidth="2" strokeLinejoin="round" />
        {pts.map((p: any, i: number) => (
          <circle key={i} cx={xFor(i)} cy={yFor(p.readiness_pct)} r="3" fill="#0f8b8d">
            <title>{new Date(p.at).toLocaleDateString()}: {p.readiness_pct}% ({p.passing}/{p.total})</title>
          </circle>
        ))}
      </svg>
      <div className="flex justify-between text-[10px] text-slate-400 mt-1 px-2">
        <span>{new Date(first.at).toLocaleDateString()}</span>
        <span>{new Date(latest.at).toLocaleDateString()}</span>
      </div>
    </div>
  );
}

export default function CompliancePosturePage() {
  const [view, setView] = useState<'posture' | 'heatmap' | 'history'>('posture');
  const [frameworks, setFrameworks] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [selectedFw, setSelectedFw] = useState<string>('');
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [search, setSearch] = useState('');
  const [history, setHistory] = useState<any>(null);
  const [snapshotting, setSnapshotting] = useState(false);
  const [msg, setMsg] = useState('');

  const loadHistory = () => {
    getComplianceHistory(undefined, 180).then(r => setHistory(r.data)).catch(() => setHistory({ frameworks: [] }));
  };

  const doSnapshot = async () => {
    setSnapshotting(true); setMsg('');
    try {
      const r = await captureSnapshot();
      setMsg(`Snapshot captured for ${r.data.captured} framework(s). History will build over time.`);
      loadHistory();
    } catch (e: any) { setMsg(e.response?.data?.detail || 'Could not capture snapshot'); }
    finally { setSnapshotting(false); }
  };

  useEffect(() => {
    Promise.all([getCompliance(), getComplianceHeatmap()])
      .then(([c, h]) => {
        const fws = c.data?.frameworks || [];
        setFrameworks(fws);
        setHeatmap(h.data?.frameworks || []);
        const first = c.data?.active_framework || fws[0]?.key;
        if (first) setSelectedFw(first);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedFw) return;
    setLoadingDetail(true);
    getComplianceDetail(selectedFw)
      .then(r => { setDetail(r.data); setExpanded({}); })
      .catch(() => setDetail(null))
      .finally(() => setLoadingDetail(false));
  }, [selectedFw]);

  const toggle = (cat: string) => setExpanded(e => ({ ...e, [cat]: !e[cat] }));

  useEffect(() => { if (view === 'history' && !history) loadHistory(); }, [view]);

  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading compliance posture…</div>;

  const filteredFamilies = detail?.families?.map((fam: any) => ({
    ...fam,
    controls: search
      ? fam.controls.filter((c: any) => (c.id + ' ' + c.title).toLowerCase().includes(search.toLowerCase()))
      : fam.controls,
  })).filter((fam: any) => !search || fam.controls.length > 0) || [];

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-6xl mx-auto">
        <div className="mb-5">
          <h1 className="text-xl font-bold flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-teal-600" /> Compliance Posture</h1>
          <p className="text-sm text-slate-400">Drill into any framework — families, controls, and what's passing or failing — or compare readiness across all frameworks.</p>
        </div>

        {/* View toggle */}
        <div className="flex items-center justify-between mb-6 border-b border-slate-200">
          <div className="flex gap-1">
            {[
              { key: 'posture', label: 'Posture (drill-down)', icon: ListTree },
              { key: 'heatmap', label: 'Heatmap (all frameworks)', icon: LayoutGrid },
              { key: 'history', label: 'History (trend)', icon: TrendingUp },
            ].map(({ key, label, icon: Icon }) => (
              <button key={key} onClick={() => setView(key as any)}
                className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${view === key ? 'border-teal-500 text-teal-700 font-medium' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
                <Icon className="w-4 h-4" /> {label}
              </button>
            ))}
          </div>
          <button onClick={doSnapshot} disabled={snapshotting} className="btn text-sm flex items-center gap-2 mb-1">
            <Camera className="w-4 h-4" /> {snapshotting ? 'Capturing…' : 'Snapshot now'}
          </button>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-100 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* ── POSTURE DRILL-DOWN (Image 1) ── */}
        {view === 'posture' && (
          <>
            {/* Framework selector */}
            <div className="flex items-center gap-3 mb-5 flex-wrap">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide bg-slate-100 px-2.5 py-1.5 rounded-lg">Framework</span>
              <select className="input max-w-xs" value={selectedFw} onChange={e => setSelectedFw(e.target.value)}>
                {frameworks.map(fw => <option key={fw.key} value={fw.key}>{fw.name}</option>)}
              </select>
            </div>

            {loadingDetail || !detail ? (
              <div className="text-slate-400 text-sm py-8 text-center">Loading framework detail…</div>
            ) : (
              <>
                {/* Metric cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                  <div className="card p-5">
                    <div className="text-sm font-semibold text-slate-700 mb-1">Passed Checks</div>
                    <div className="flex items-end justify-between">
                      <span className="text-xs text-slate-400">{detail.summary.passing} passing of {detail.summary.total_controls} controls</span>
                      <span className="text-3xl font-bold text-slate-800">{detail.summary.passing}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden mt-2">
                      <div className="h-full rounded-full bg-teal-500" style={{ width: `${detail.summary.total_controls ? (detail.summary.passing / detail.summary.total_controls) * 100 : 0}%` }} />
                    </div>
                  </div>
                  <div className="card p-5">
                    <div className="text-sm font-semibold text-slate-700 mb-1">Compliance Posture</div>
                    <div className="flex items-end justify-between">
                      <span className="text-xs text-slate-400">{detail.summary.readiness_pct}% average readiness</span>
                      <span className="text-3xl font-bold" style={{ color: readinessColor(detail.summary.readiness_pct) }}>{detail.summary.readiness_pct}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden mt-2">
                      <div className="h-full rounded-full" style={{ width: `${detail.summary.readiness_pct}%`, background: readinessColor(detail.summary.readiness_pct) }} />
                    </div>
                  </div>
                </div>

                {/* Search */}
                <div className="relative mb-3">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input className="input pl-9" placeholder="Search controls…" value={search} onChange={e => setSearch(e.target.value)} />
                </div>

                {/* Families -> controls -> findings */}
                <div className="card overflow-hidden">
                  <div className="flex items-center px-5 py-2.5 border-b border-slate-100 text-xs font-semibold text-slate-400 uppercase tracking-wide">
                    <span className="flex-1">Control family / control</span>
                    <span className="w-32 text-right">Posture</span>
                    <span className="w-24 text-right">Passed</span>
                  </div>
                  {filteredFamilies.length === 0 ? (
                    <div className="px-5 py-8 text-center text-sm text-slate-400">No controls match "{search}".</div>
                  ) : filteredFamilies.map((fam: any) => (
                    <div key={fam.category} className="border-b border-slate-50 last:border-0">
                      {/* Family row */}
                      <button onClick={() => toggle(fam.category)} className="w-full flex items-center px-5 py-3 hover:bg-slate-50 transition-colors text-left">
                        <span className="flex-1 flex items-center gap-2">
                          {expanded[fam.category] ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                          <span className="font-medium text-slate-800">{fam.label}</span>
                        </span>
                        <span className="w-32 flex items-center justify-end gap-2">
                          <Bar pct={fam.readiness_pct} />
                          <span className="text-sm font-semibold w-9 text-right" style={{ color: readinessColor(fam.readiness_pct) }}>{fam.readiness_pct}%</span>
                        </span>
                        <span className="w-24 text-right text-sm text-slate-500">{fam.passing} of {fam.total}</span>
                      </button>

                      {/* Controls */}
                      {expanded[fam.category] && (
                        <div className="bg-slate-50/50">
                          {fam.controls.map((c: any) => {
                            const passing = c.status === 'passing';
                            const ckey = fam.category + ':' + c.id;
                            return (
                              <div key={c.id} className="border-t border-slate-100">
                                <button onClick={() => c.open_findings > 0 && toggle(ckey)}
                                  className={`w-full flex items-center px-5 py-2.5 pl-11 text-left ${c.open_findings > 0 ? 'hover:bg-white cursor-pointer' : 'cursor-default'}`}>
                                  <span className="flex-1 flex items-center gap-2 min-w-0">
                                    {c.open_findings > 0
                                      ? (expanded[ckey] ? <ChevronDown className="w-3.5 h-3.5 text-slate-300 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-300 flex-shrink-0" />)
                                      : <span className="w-3.5 flex-shrink-0" />}
                                    <span className="text-xs font-mono text-slate-400 flex-shrink-0">{c.id}</span>
                                    <span className="text-sm text-slate-700 truncate">{c.title}</span>
                                  </span>
                                  <span className="w-32 text-right">
                                    {c.weight && <span className="text-[10px] px-1.5 py-0.5 rounded-full mr-1" style={{ background: readinessBg(passing ? 100 : 0), color: readinessColor(passing ? 100 : 0) }}>{c.weight}</span>}
                                  </span>
                                  <span className="w-24 flex items-center justify-end gap-1.5">
                                    {passing
                                      ? <span className="inline-flex items-center gap-1 text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full"><CheckCircle2 className="w-3 h-3" /> Pass</span>
                                      : <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full"><XCircle className="w-3 h-3" /> Fail</span>}
                                  </span>
                                </button>
                                {/* Findings under a failing control */}
                                {expanded[ckey] && c.finding_titles?.length > 0 && (
                                  <div className="pl-[4.5rem] pr-5 pb-2 space-y-1">
                                    {c.finding_titles.map((ft: string, i: number) => (
                                      <div key={i} className="text-xs text-slate-500 flex items-center gap-2 py-1">
                                        <span className="w-1 h-1 rounded-full bg-red-400" />{ft}
                                      </div>
                                    ))}
                                    {c.open_findings > c.finding_titles.length && (
                                      <div className="text-[11px] text-slate-400 pl-3">+{c.open_findings - c.finding_titles.length} more finding(s)</div>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400 mt-3">Families are ordered worst-readiness first, so the gaps needing attention surface at the top. Expand a failing control to see the findings behind it.</p>
              </>
            )}
          </>
        )}

        {/* ── HEATMAP (Image 3) ── */}
        {view === 'heatmap' && (
          <div>
            {heatmap.length === 0 ? (
              <div className="card p-8 text-center text-sm text-slate-400">No frameworks selected for this tenant yet.</div>
            ) : (
              <>
                <div className="card p-6">
                  <div className="text-sm font-semibold text-slate-700 mb-4">Cross-framework readiness</div>
                  <div className="flex gap-2 items-end" style={{ minHeight: '260px' }}>
                    {heatmap.map(fw => (
                      <div key={fw.key} className="flex-1 flex flex-col items-center gap-2 min-w-0">
                        <div className="w-full rounded-lg flex items-center justify-center text-white font-bold text-lg transition-all hover:opacity-90 cursor-default"
                          style={{ background: readinessColor(fw.readiness_pct), height: `${Math.max(fw.readiness_pct, 12) * 2}px` }}
                          title={`${fw.name}: ${fw.passing}/${fw.total_controls} controls passing`}>
                          {fw.readiness_pct}%
                        </div>
                        <div className="text-[11px] text-slate-500 text-center leading-tight truncate w-full" title={fw.name}>{fw.short || fw.name}</div>
                      </div>
                    ))}
                  </div>
                </div>
                {/* legend + cards */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-4">
                  {heatmap.map(fw => (
                    <button key={fw.key} onClick={() => { setSelectedFw(fw.key); setView('posture'); }}
                      className="card p-4 text-left hover:shadow-md transition-shadow">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-slate-700 truncate">{fw.short || fw.name}</span>
                        <span className="text-lg font-bold" style={{ color: readinessColor(fw.readiness_pct) }}>{fw.readiness_pct}%</span>
                      </div>
                      <Bar pct={fw.readiness_pct} />
                      <div className="text-[11px] text-slate-400 mt-2">{fw.passing} of {fw.total_controls} controls passing</div>
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400 mt-3 text-center">Click any framework to drill into its posture. Color runs green (strong) to red (needs work).</p>
              </>
            )}
          </div>
        )}

        {/* ── HISTORY / TREND ── */}
        {view === 'history' && (
          <div>
            {!history ? (
              <div className="text-slate-400 text-sm py-8 text-center">Loading history…</div>
            ) : history.frameworks.length === 0 || history.snapshot_count === 0 ? (
              <div className="card p-8 text-center">
                <TrendingUp className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No history yet.</p>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">Capture a snapshot to start building your compliance history. Snapshots record your posture over time so you can show trends and prove posture as of any past date — valuable for audits.</p>
                <button onClick={doSnapshot} disabled={snapshotting} className="btn btn-primary text-sm mt-4 inline-flex items-center gap-2">
                  <Camera className="w-4 h-4" /> {snapshotting ? 'Capturing…' : 'Capture first snapshot'}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-xs text-slate-400">{history.snapshot_count} snapshots over the last 180 days. Each line shows a framework's readiness trend.</p>
                {history.frameworks.map((fw: any) => <TrendCard key={fw.key} fw={fw} />)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
