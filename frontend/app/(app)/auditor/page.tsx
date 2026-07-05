'use client';
import { useEffect, useState } from 'react';
import { getAuditReport, enhanceAuditSummaryAI, downloadAuditPDF, downloadAuditExcel } from '@/lib/api';
import { Shield, CheckCircle, XCircle, FileText, Download } from 'lucide-react';

export default function AuditorPage() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'summary'|'controls'|'policies'|'evidence'|'tickets'|'trail'>('summary');
  const [enhancing, setEnhancing] = useState(false);
  const [aiMsg, setAiMsg] = useState('');

  const download = async (kind: 'pdf' | 'excel') => {
    setAiMsg(kind === 'pdf' ? 'Generating PDF…' : 'Generating Excel…');
    try {
      const r = kind === 'pdf' ? await downloadAuditPDF() : await downloadAuditExcel();
      const blob = new Blob([r.data], { type: kind === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = kind === 'pdf' ? 'audit_report.pdf' : 'control_matrix.xlsx';
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
      setAiMsg('Download started.');
    } catch (e) { setAiMsg('Download failed.'); }
  };

  const enhanceSummary = async () => {
    setEnhancing(true); setAiMsg('');
    try {
      const r = await enhanceAuditSummaryAI();
      setReport((rep: any) => ({...rep, ai_summary: r.data.summary}));
      setAiMsg(`AI summary generated. ${r.data.credits_remaining} credits remaining.`);
    } catch (e: any) {
      setAiMsg(e.response?.data?.detail || 'Enhancement failed');
    } finally { setEnhancing(false); }
  };

  useEffect(() => {
    getAuditReport().then(r => setReport(r.data)).catch(e => console.warn("audit report load failed", e)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Generating audit report…</div>;
  if (!report) return null;

  const score = report.score;
  const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
  const passing = report.controls?.filter((c: any) => c.status === 'passing').length || 0;
  const failing = report.controls?.filter((c: any) => c.status === 'failing').length || 0;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-6xl mx-auto">

        {/* Header */}
        <div className="card p-6 mb-5 bg-slate-900 text-white">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-teal-500 rounded-xl flex items-center justify-center flex-shrink-0">
                <Shield className="w-6 h-6 text-slate-900" />
              </div>
              <div>
                <h1 className="text-xl font-bold">{report.tenant?.name}</h1>
                <p className="text-slate-400 text-sm capitalize">{report.tenant?.industry} · {report.tenant?.framework_name}</p>
                <p className="text-slate-500 text-xs mt-0.5">Generated {new Date(report.generated_at).toLocaleString()}</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-5xl font-bold" style={{color: scoreColor}}>{score}</div>
              <div className="text-slate-400 text-sm">Compliance Score</div>
              <div className="flex gap-2 mt-2 justify-end">
                <button onClick={() => download('pdf')} className="btn text-xs py-1 px-3 bg-white/10 border-white/20 text-white hover:bg-white/20">
                  <Download className="w-3.5 h-3.5" /> PDF
                </button>
                <button onClick={() => download('excel')} className="btn text-xs py-1 px-3 bg-white/10 border-white/20 text-white hover:bg-white/20">
                  <Download className="w-3.5 h-3.5" /> Excel
                </button>
              </div>
            </div>
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 pt-5 border-t border-white/10">
            {[
              { label:'Critical', value: report.summary?.critical, color:'text-red-400' },
              { label:'High',     value: report.summary?.high,     color:'text-orange-400' },
              { label:'Open Tickets', value: report.summary?.open_tickets, color:'text-blue-400' },
              { label:'Resolved',  value: report.summary?.resolved, color:'text-emerald-400' },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <p className="text-slate-400 text-xs">{label}</p>
                <p className={`text-2xl font-bold ${color}`}>{value ?? 0}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-5 bg-slate-100 p-1 rounded-xl w-fit">
          {(['summary','controls','policies','evidence','tickets','trail'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg capitalize transition-colors ${tab===t?'bg-white shadow-sm text-slate-900':'text-slate-500 hover:text-slate-700'}`}>
              {t === 'trail' ? 'Audit Trail' : t}
            </button>
          ))}
        </div>

        {/* Summary */}
        {tab === 'summary' && (
          <div className="space-y-4">
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-3">
                <FileText className="w-4 h-4 text-slate-400" />
                <h2 className="text-sm font-semibold text-slate-700">Executive Summary</h2>
                <button onClick={enhanceSummary} disabled={enhancing}
                  className="ml-auto btn text-xs py-1 bg-gradient-to-r from-violet-50 to-teal-50 border-violet-200 text-violet-700">
                  {enhancing ? 'Generating…' : '✨ AI Summary (2 credits)'}
                </button>
              </div>
              {aiMsg && <p className="text-xs text-violet-600 mb-2">{aiMsg}</p>}
              <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{report.ai_summary}</p>
            </div>

            {/* Controls summary */}
            <div className="grid grid-cols-2 gap-4">
              <div className="card p-5">
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">Control Status</p>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-emerald-600">Passing</span><span className="font-semibold">{passing}</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 mb-2">
                      <div className="h-2 rounded-full bg-emerald-500" style={{width:`${report.controls?.length ? passing/report.controls.length*100 : 0}%`}} />
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-red-600">Failing</span><span className="font-semibold">{failing}</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 mt-1">
                      <div className="h-2 rounded-full bg-red-500" style={{width:`${report.controls?.length ? failing/report.controls.length*100 : 0}%`}} />
                    </div>
                  </div>
                </div>
              </div>
              <div className="card p-5">
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">Ticket Resolution</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">Accepted</span><span className="font-semibold text-teal-600">{report.summary?.accepted}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Rejected</span><span className="font-semibold text-red-500">{report.summary?.rejected}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Open</span><span className="font-semibold text-slate-700">{report.summary?.open_tickets}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Evidence sources</span><span className="font-semibold">{report.summary?.connectors}</span></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Controls */}
        {tab === 'controls' && (
          <div className="card divide-y divide-slate-50">
            {!report.controls?.length && <div className="px-5 py-8 text-center text-sm text-slate-400">No controls assessed.</div>}
            {report.controls?.map((ctrl: any) => (
              <div key={ctrl.id} className="px-5 py-4 flex items-start gap-3">
                {ctrl.status === 'passing'
                  ? <CheckCircle className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" />
                  : <XCircle    className="w-5 h-5 text-red-500    mt-0.5 flex-shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-0.5">
                    <span className="text-xs font-mono font-bold text-slate-500">{ctrl.id}</span>
                    <span className={`badge ${ctrl.status==='passing'?'badge-passing':'badge-failing'}`}>{ctrl.status}</span>
                    <span className="text-xs text-slate-400 capitalize">{ctrl.weight} priority</span>
                  </div>
                  <p className="text-sm font-medium text-slate-800">{ctrl.title}</p>
                  {ctrl.open_findings > 0 && (
                    <p className="text-xs text-red-500 mt-0.5">{ctrl.open_findings} open finding{ctrl.open_findings>1?'s':''}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Custom Policies */}
        {tab === 'policies' && (
          <div className="card divide-y divide-slate-50">
            {!report.custom_policies?.length && <div className="px-5 py-8 text-center text-sm text-slate-400">No custom company policies defined.</div>}
            {report.custom_policies?.map((p: any) => (
              <div key={p.id} className="px-5 py-4 flex items-start gap-3">
                {p.status === 'passing' ? <CheckCircle className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" />
                  : p.status === 'failing' ? <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                  : <span className="w-5 h-5 rounded-full bg-slate-200 flex-shrink-0 mt-0.5" />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-0.5">
                    {p.policy_id && <span className="text-xs font-mono font-bold text-slate-500">{p.policy_id}</span>}
                    <span className={`badge badge-${p.severity}`}>{p.severity}</span>
                    <span className="badge badge-info">{p.eval_mode}</span>
                    {p.mapped_control && <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded font-mono">→ {p.mapped_control}</span>}
                  </div>
                  <p className="text-sm font-medium text-slate-800">{p.title}</p>
                  {p.last_result && <p className="text-xs text-slate-400 mt-0.5">{p.last_result}</p>}
                </div>
                <span className={`badge ${p.status==='passing'?'badge-passing':p.status==='failing'?'badge-failing':'badge-open'} flex-shrink-0`}>{p.status?.replace('_',' ')}</span>
              </div>
            ))}
          </div>
        )}

        {/* Evidence */}
        {tab === 'evidence' && (
          <div className="card divide-y divide-slate-50">
            {!report.evidence?.length && <div className="px-5 py-8 text-center text-sm text-slate-400">No evidence collected.</div>}
            {report.evidence?.map((ev: any, i: number) => (
              <div key={i} className="px-5 py-4 flex items-center gap-3">
                <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center text-base flex-shrink-0">
                  {ev.type==='network'?'🔥':ev.type==='server'?'🖥️':ev.type==='cloud'?'☁️':ev.type==='identity'?'🔑':'📊'}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-800">{ev.source}</p>
                  <p className="text-xs text-slate-400 capitalize">{ev.type} · {ev.events_collected} events collected</p>
                  {ev.last_collected && <p className="text-xs text-slate-400">Last: {new Date(ev.last_collected).toLocaleString()}</p>}
                </div>
                <span className={`badge ${ev.status==='current'?'badge-passing':'badge-medium'}`}>{ev.status}</span>
              </div>
            ))}
          </div>
        )}

        {/* Tickets */}
        {tab === 'tickets' && (
          <div className="card divide-y divide-slate-50">
            {!report.tickets?.length && <div className="px-5 py-8 text-center text-sm text-slate-400">No tickets.</div>}
            {report.tickets?.map((t: any) => (
              <a key={t.ref} href={`/tickets/${t.id}`} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50 cursor-pointer block">
                <span className="text-xs font-mono text-slate-400 flex-shrink-0 w-24">{t.ref}</span>
                <span className="text-sm text-slate-700 flex-1 truncate">{t.title}</span>
                <span className={`badge badge-${t.severity} flex-shrink-0`}>{t.severity}</span>
                <span className={`badge badge-${t.status} flex-shrink-0`}>{t.status.replace('_',' ')}</span>
                <span className="text-xs text-teal-600 flex-shrink-0">View →</span>
              </a>
            ))}
          </div>
        )}

        {/* Audit trail */}
        {tab === 'trail' && (
          <div className="card divide-y divide-slate-50">
            {!report.audit_trail?.length && <div className="px-5 py-8 text-center text-sm text-slate-400">No audit trail entries.</div>}
            {report.audit_trail?.map((entry: any, i: number) => (
              <div key={i} className="px-5 py-3 flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500 flex-shrink-0 mt-0.5">
                  {entry.user?.charAt(0) || 'S'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-slate-700">{entry.user || 'System'}</span>
                    <span className="text-xs text-slate-500">{entry.action.replace('_',' ')}</span>
                    <span className="text-xs text-slate-300">{new Date(entry.timestamp).toLocaleString()}</span>
                  </div>
                  {entry.details && (
                    <p className="text-xs text-slate-400 mt-0.5 truncate">
                      {JSON.stringify(entry.details).slice(0,120)}
                    </p>
                  )}
                </div>
                <span className="text-xs text-slate-400 capitalize flex-shrink-0">{entry.entity_type}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
