'use client';
import { useEffect, useState } from 'react';
import { getCompliance } from '@/lib/api';
import { BadgeCheck, ChevronDown, ChevronRight, Download, ShieldCheck, AlertTriangle } from 'lucide-react';

export default function CompliancePage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    getCompliance()
      .then(r => {
        setData(r.data);
        // expand the active framework by default
        if (r.data?.active_framework) setExpanded({ [r.data.active_framework]: true });
      })
      .catch(() => setData({ frameworks: [] }))
      .finally(() => setLoading(false));
  }, []);

  const toggle = (key: string) => setExpanded(e => ({ ...e, [key]: !e[key] }));

  const downloadCsv = (fw: any) => {
    const rows = [['Control ID', 'Title', 'Category', 'Weight', 'Status', 'Open Findings']];
    fw.controls.forEach((c: any) => {
      rows.push([c.id, c.title, c.label || c.category, c.weight || '', c.status, String(c.open_findings)]);
    });
    const csv = rows.map(r => r.map(f => `"${String(f).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${fw.short || fw.key}-compliance.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const downloadAll = () => {
    if (!data?.frameworks?.length) return;
    const rows = [['Framework', 'Control ID', 'Title', 'Category', 'Status', 'Open Findings']];
    data.frameworks.forEach((fw: any) => {
      fw.controls.forEach((c: any) => {
        rows.push([fw.short || fw.key, c.id, c.title, c.label || c.category, c.status, String(c.open_findings)]);
      });
    });
    const csv = rows.map(r => r.map(f => `"${String(f).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `compliance-all-frameworks.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading compliance…</div>;

  const frameworks = data?.frameworks || [];

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2"><BadgeCheck className="w-5 h-5 text-teal-600" /> Compliance</h1>
            <p className="text-sm text-slate-400">Your readiness across every selected framework. Expand a framework to see its controls.</p>
          </div>
          {frameworks.length > 0 && (
            <button onClick={downloadAll} className="btn btn-primary flex items-center gap-2 text-sm">
              <Download className="w-4 h-4" /> Download all
            </button>
          )}
        </div>

        {frameworks.length === 0 && (
          <div className="card p-8 text-center text-slate-400">
            <p className="text-sm">No frameworks selected. Choose your compliance frameworks in Settings to see your compliance posture here.</p>
          </div>
        )}

        <div className="space-y-4">
          {frameworks.map((fw: any) => {
            const isOpen = expanded[fw.key];
            const s = fw.summary;
            const readinessColor = s.readiness_pct >= 80 ? 'text-emerald-600' : s.readiness_pct >= 50 ? 'text-amber-600' : 'text-red-600';
            const barColor = s.readiness_pct >= 80 ? 'bg-emerald-500' : s.readiness_pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
            return (
              <div key={fw.key} className="card overflow-hidden">
                {/* Framework header */}
                <div className="p-5 flex items-center justify-between cursor-pointer hover:bg-slate-50" onClick={() => toggle(fw.key)}>
                  <div className="flex items-center gap-3">
                    <button className="text-slate-400">{isOpen ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}</button>
                    <div className="w-3 h-3 rounded-full" style={{ background: fw.color || '#666' }} />
                    <div>
                      <p className="font-bold text-slate-800">{fw.name}</p>
                      <p className="text-xs text-slate-400">{s.total_controls} controls · {s.passing} passing · {s.failing} with findings</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className={`text-2xl font-bold ${readinessColor}`}>{s.readiness_pct}%</p>
                      <p className="text-[10px] text-slate-400 uppercase tracking-wide">Readiness</p>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); downloadCsv(fw); }}
                      className="p-2 rounded-lg hover:bg-slate-100 text-slate-500" title="Download this framework">
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Readiness bar */}
                <div className="px-5 pb-1">
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full ${barColor}`} style={{ width: `${s.readiness_pct}%` }} />
                  </div>
                </div>

                {/* Controls table */}
                {isOpen && (
                  <div className="px-5 pb-5 pt-3">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-slate-400 border-b border-slate-100">
                          <th className="py-2 font-medium">Control</th>
                          <th className="py-2 font-medium">Category</th>
                          <th className="py-2 font-medium">Status</th>
                          <th className="py-2 font-medium">Findings</th>
                        </tr>
                      </thead>
                      <tbody>
                        {fw.controls.map((c: any) => (
                          <tr key={c.id} className="border-b border-slate-50">
                            <td className="py-2.5">
                              <p className="font-medium text-slate-700">{c.id}</p>
                              <p className="text-xs text-slate-400">{c.title}</p>
                            </td>
                            <td className="py-2.5 text-xs text-slate-500">{c.label || c.category}</td>
                            <td className="py-2.5">
                              {c.status === 'passing'
                                ? <span className="inline-flex items-center gap-1 text-xs text-emerald-600"><ShieldCheck className="w-3.5 h-3.5" /> Passing</span>
                                : <span className="inline-flex items-center gap-1 text-xs text-red-600"><AlertTriangle className="w-3.5 h-3.5" /> Findings</span>}
                            </td>
                            <td className="py-2.5 text-xs text-slate-500">
                              {c.open_findings > 0 ? (
                                <span title={c.finding_titles?.join('\n')}>{c.open_findings} open</span>
                              ) : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
