'use client';
import { useEffect, useState } from 'react';
import { getReportLevels, getReport, downloadReportPdf, getReportSchedule, setReportSchedule, sendReportsNow, getReportHistory, saveReportToHistory, downloadStoredReport } from '@/lib/api';
import { FileText, Download, Briefcase, Wrench, ClipboardCheck, TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, XCircle, Eye, CalendarClock, History, Send, Save } from 'lucide-react';

const LEVEL_ICONS: Record<string, any> = { ciso: Briefcase, engineer: Wrench, auditor: ClipboardCheck };

function readinessColor(pct: number): string {
  if (pct >= 90) return '#16a34a';
  if (pct >= 75) return '#65a30d';
  if (pct >= 50) return '#d97706';
  if (pct >= 30) return '#ea580c';
  return '#dc2626';
}

export default function ReportingPage() {
  const [tab, setTab] = useState<'reports' | 'schedule' | 'history'>('reports');
  const [levels, setLevels] = useState<any[]>([]);
  const [active, setActive] = useState<string>('ciso');
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [role, setRole] = useState('');
  const [schedule, setSchedule] = useState<any>(null);
  const [historyList, setHistoryList] = useState<any[]>([]);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const isAdmin = role === 'admin';

  useEffect(() => {
    try { setRole(JSON.parse(localStorage.getItem('user') || '{}').role || ''); } catch {}
    getReportLevels().then(r => setLevels(r.data || [])).catch(() => {});
  }, []);
  useEffect(() => {
    if (tab === 'schedule' && !schedule) getReportSchedule().then(r => setSchedule(r.data)).catch(() => {});
    if (tab === 'history') getReportHistory().then(r => setHistoryList(r.data || [])).catch(() => {});
  }, [tab]);

  const saveSchedule = async (patch: any) => {
    const next = { ...schedule, ...patch }; setSchedule(next);
    try { const r = await setReportSchedule(patch); setSchedule(r.data); setMsg('Schedule saved.'); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Could not save'); }
  };
  const sendNow = async () => {
    setBusy(true); setMsg('');
    try { const r = await sendReportsNow(); const sent = r.data.results.reduce((a: number, x: any) => a + (x.sent || 0), 0);
      setMsg(`Reports generated and sent to ${sent} recipient(s) for ${r.data.period}.`); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Could not send'); }
    finally { setBusy(false); }
  };
  const saveToHistory = async () => {
    setBusy(true);
    try { await saveReportToHistory(active); setMsg('Report saved to history.'); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Could not save'); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (tab !== 'reports') return;
    setLoading(true);
    getReport(active).then(r => setReport(r.data)).catch(() => setReport(null)).finally(() => setLoading(false));
  }, [active, tab]);

  const download = async () => {
    setDownloading(true);
    try { await downloadReportPdf(active, report?.tenant?.name?.replace(/\s+/g, '_') || 'report'); }
    finally { setDownloading(false); }
  };

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="mb-4">
          <h1 className="text-xl font-bold flex items-center gap-2"><FileText className="w-5 h-5 text-teal-600" /> Reporting</h1>
          <p className="text-sm text-slate-400">Audience-appropriate compliance reports — view, download, schedule delivery, and keep a history.</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-slate-200">
          {[
            { key: 'reports', label: 'Reports', icon: FileText },
            { key: 'schedule', label: 'Schedule', icon: CalendarClock },
            { key: 'history', label: 'History', icon: History },
          ].map(({ key, label, icon: Icon }) => (
            <button key={key} onClick={() => setTab(key as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${tab === key ? 'border-teal-500 text-teal-700 font-medium' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
              <Icon className="w-4 h-4" /> {label}
            </button>
          ))}
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-100 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* ── SCHEDULE TAB ── */}
        {tab === 'schedule' && (
          !isAdmin ? (
            <div className="card p-8 text-center text-sm text-slate-400">Only a tenant admin can configure report scheduling.</div>
          ) : !schedule ? (
            <div className="text-slate-400 text-sm py-8 text-center">Loading…</div>
          ) : (
            <div className="max-w-xl space-y-5">
              <div className="card p-5">
                <h2 className="font-semibold text-slate-800 mb-1">Automatic delivery</h2>
                <p className="text-xs text-slate-400 mb-4">Reports are emailed on this cadence to whoever opted into each level (set in Notifications).</p>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Cadence</label>
                <select className="input max-w-xs mb-4" value={schedule.cadence} onChange={e => saveSchedule({ cadence: e.target.value })}>
                  <option value="off">Off (manual only)</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                </select>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-slate-600">Which reports to send:</div>
                  {[['send_ciso', 'Executive / CISO'], ['send_engineer', 'Engineering'], ['send_auditor', 'Auditor / Evidence']].map(([k, label]) => (
                    <label key={k} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={!!schedule[k]} onChange={e => saveSchedule({ [k]: e.target.checked })} /> {label}
                    </label>
                  ))}
                </div>
                {schedule.next_run_at && schedule.cadence !== 'off' && (
                  <p className="text-xs text-slate-400 mt-4">Next delivery: {new Date(schedule.next_run_at).toLocaleDateString()}</p>
                )}
              </div>
              <button onClick={sendNow} disabled={busy} className="btn btn-primary flex items-center gap-2 text-sm">
                <Send className="w-4 h-4" /> {busy ? 'Sending…' : 'Send now'}
              </button>
              <p className="text-[11px] text-slate-400">"Send now" generates and emails the selected reports immediately, and stores them in History.</p>
            </div>
          )
        )}

        {/* ── HISTORY TAB ── */}
        {tab === 'history' && (
          historyList.length === 0 ? (
            <div className="card p-8 text-center">
              <History className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No saved reports yet.</p>
              <p className="text-xs text-slate-400 mt-1">Reports are stored here when sent on a schedule, sent now, or saved from the Reports tab.</p>
            </div>
          ) : (
            <div className="card divide-y divide-slate-50">
              {historyList.map(h => (
                <div key={h.id} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50/50">
                  <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{h.title}</p>
                    <p className="text-xs text-slate-400">
                      {new Date(h.created_at).toLocaleString()} · by {h.generated_by}
                      {h.emailed_to > 0 && ` · emailed to ${h.emailed_to}`}
                      {h.overall_readiness != null && ` · ${h.overall_readiness}%`}
                    </p>
                  </div>
                  <button onClick={() => downloadStoredReport(h.id, h.title)} className="btn text-xs py-1 px-2 flex items-center gap-1 flex-shrink-0">
                    <Download className="w-3.5 h-3.5" /> PDF
                  </button>
                </div>
              ))}
            </div>
          )
        )}

        {/* ── REPORTS TAB ── */}
        {tab === 'reports' && (<>
        <div className="flex items-center justify-end gap-2 mb-4">
          {isAdmin && <button onClick={saveToHistory} disabled={busy || !report} className="btn text-sm flex items-center gap-2"><Save className="w-4 h-4" /> Save to history</button>}
          <button onClick={download} disabled={downloading || !report} className="btn btn-primary flex items-center gap-2 text-sm">
            <Download className="w-4 h-4" /> {downloading ? 'Preparing…' : 'Download PDF'}
          </button>
        </div>

        {/* Level selector */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
          {levels.map(lv => {
            const Icon = LEVEL_ICONS[lv.key] || FileText;
            const on = active === lv.key;
            return (
              <button key={lv.key} onClick={() => setActive(lv.key)}
                className={`card p-4 text-left transition-all ${on ? 'ring-2 ring-teal-400 shadow-sm' : 'hover:shadow-sm'}`}>
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${on ? 'bg-teal-500 text-white' : 'bg-slate-100 text-slate-500'}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="font-semibold text-slate-800 text-sm">{lv.label}</span>
                </div>
                <p className="text-xs text-slate-400">{lv.desc}</p>
              </button>
            );
          })}
        </div>

        {loading ? (
          <div className="text-slate-400 text-sm py-8 text-center">Loading report…</div>
        ) : !report ? (
          <div className="card p-8 text-center text-sm text-slate-400">Could not load report.</div>
        ) : (
          <div className="card p-6">
            {/* Report header */}
            <div className="border-b border-slate-100 pb-4 mb-4">
              <h2 className="text-lg font-bold text-slate-800">{report.level_label}</h2>
              <p className="text-sm text-slate-500">{report.tenant?.name} · {report.tenant?.industry}</p>
              <p className="text-xs text-slate-400 mt-0.5">Generated {report.generated_at}</p>
            </div>

            {/* CISO */}
            {report.level === 'ciso' && (
              <div className="space-y-5">
                <div className="flex items-center gap-6">
                  <div>
                    <div className="text-xs text-slate-400 uppercase tracking-wide">Overall Readiness</div>
                    <div className="text-4xl font-bold" style={{ color: readinessColor(report.overall_readiness) }}>{report.overall_readiness}%</div>
                  </div>
                  <div className={`flex-1 rounded-xl p-4 ${report.risk.critical > 0 ? 'bg-red-50' : report.risk.high > 0 ? 'bg-orange-50' : 'bg-emerald-50'}`}>
                    <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                      <AlertTriangle className={`w-4 h-4 ${report.risk.critical > 0 ? 'text-red-500' : report.risk.high > 0 ? 'text-orange-500' : 'text-emerald-500'}`} />
                      {report.risk.headline}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">{report.risk.critical} critical · {report.risk.high} high open</div>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-700 mb-2">Framework posture</div>
                  <div className="space-y-2">
                    {report.frameworks.map((f: any, i: number) => (
                      <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                        <span className="flex-1 text-sm text-slate-700">{f.name}</span>
                        <span className="w-28 h-2 rounded-full bg-slate-100 overflow-hidden">
                          <span className="block h-full rounded-full" style={{ width: `${f.readiness_pct}%`, background: readinessColor(f.readiness_pct) }} />
                        </span>
                        <span className="w-12 text-right text-sm font-semibold" style={{ color: readinessColor(f.readiness_pct) }}>{f.readiness_pct}%</span>
                        <span className="w-16 text-right text-xs text-slate-400">{f.passing}/{f.total}</span>
                        <span className="w-14 text-right text-xs">
                          {f.delta === null ? <span className="text-slate-300">—</span> :
                            f.delta >= 0 ? <span className="text-emerald-600 inline-flex items-center gap-0.5"><TrendingUp className="w-3 h-3" />{f.delta}%</span>
                                         : <span className="text-red-600 inline-flex items-center gap-0.5"><TrendingDown className="w-3 h-3" />{Math.abs(f.delta)}%</span>}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Engineer */}
            {report.level === 'engineer' && (
              <div className="space-y-5">
                {report.frameworks.map((f: any, i: number) => (
                  <div key={i}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-semibold text-slate-800">{f.name}</span>
                      <span className="text-xs text-slate-400">{f.readiness_pct}% ready · {f.failing_count} failing</span>
                    </div>
                    {f.failing_controls.length === 0 ? (
                      <p className="text-sm text-emerald-600 flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> No failing controls.</p>
                    ) : (
                      <div className="space-y-2">
                        {f.failing_controls.map((c: any, j: number) => (
                          <div key={j} className="border border-slate-100 rounded-lg p-3">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-mono font-bold text-slate-500">{c.id}</span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-50 text-red-600 capitalize">{c.weight}</span>
                              <span className="text-sm text-slate-700">{c.title}</span>
                            </div>
                            {c.findings?.length > 0 && (
                              <div className="pl-2 space-y-0.5 mt-1">
                                {c.findings.slice(0, 5).map((ft: string, k: number) => (
                                  <p key={k} className="text-xs text-red-600 flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-red-400" />{ft}</p>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Auditor */}
            {report.level === 'auditor' && (
              <div className="space-y-6">
                {report.frameworks.map((f: any, i: number) => (
                  <div key={i}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-semibold text-slate-800">{f.name}</span>
                      {f.version && <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">{f.version}</span>}
                      <span className="text-xs text-slate-400">{f.readiness_pct}% · {f.passing}/{f.total}</span>
                    </div>
                    <div className="border border-slate-100 rounded-lg overflow-hidden">
                      {f.controls.slice(0, 40).map((c: any, j: number) => (
                        <div key={j} className="flex items-center gap-3 px-3 py-1.5 text-xs border-b border-slate-50 last:border-0">
                          <span className="font-mono text-slate-400 w-20 flex-shrink-0">{c.id}</span>
                          <span className="flex-1 text-slate-600 truncate">{c.title}</span>
                          {c.status === 'passing'
                            ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                            : <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />}
                        </div>
                      ))}
                      {f.controls.length > 40 && <div className="px-3 py-1.5 text-[11px] text-slate-400">+{f.controls.length - 40} more in the PDF</div>}
                    </div>
                  </div>
                ))}
                {report.evidence_sources?.length > 0 && (
                  <div>
                    <div className="text-sm font-semibold text-slate-700 mb-2">Evidence sources</div>
                    <div className="flex flex-wrap gap-2">
                      {report.evidence_sources.map((s: any, i: number) => (
                        <span key={i} className="text-xs px-2 py-1 bg-slate-100 rounded-lg text-slate-600">{s.source} · {s.status}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        <p className="text-[11px] text-slate-400 mt-4 text-center">Schedule automatic delivery and view past reports in the tabs above.</p>
        </>)}
      </div>
    </div>
  );
}
