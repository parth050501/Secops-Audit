'use client';
import { useEffect, useState } from 'react';
import { getSoc2Readiness, setupSoc2, updateSoc2Criterion } from '@/lib/api';
import { ShieldCheck, CheckCircle, XCircle, Clock, Circle, Calendar, Settings2 } from 'lucide-react';

const TRUST_CATS = [
  { key:'security', name:'Security', mandatory:true, desc:'Common Criteria — always required' },
  { key:'availability', name:'Availability', mandatory:false, desc:'Uptime & resilience commitments' },
  { key:'confidentiality', name:'Confidentiality', mandatory:false, desc:'Protection of confidential data' },
  { key:'processing_integrity', name:'Processing Integrity', mandatory:false, desc:'Complete, accurate processing' },
  { key:'privacy', name:'Privacy', mandatory:false, desc:'Personal information handling' },
];

const READINESS = {
  ready:       { label:'Ready', color:'text-emerald-600', bg:'bg-emerald-50', icon: CheckCircle },
  in_progress: { label:'In Progress', color:'text-blue-600', bg:'bg-blue-50', icon: Clock },
  gap:         { label:'Gap', color:'text-red-600', bg:'bg-red-50', icon: XCircle },
  not_started: { label:'Not Started', color:'text-slate-400', bg:'bg-slate-50', icon: Circle },
};

export default function Soc2Page() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showSetup, setShowSetup] = useState(false);
  const [reportType, setReportType] = useState('type2');
  const [cats, setCats] = useState<string[]>(['security']);
  const [targetDate, setTargetDate] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [filter, setFilter] = useState('all');

  const load = () => getSoc2Readiness().then(r => setData(r.data)).catch(()=>{}).finally(()=>setLoading(false));
  useEffect(() => { load(); }, []);

  const runSetup = async () => {
    await setupSoc2({ report_type: reportType, trust_categories: cats, target_date: targetDate || undefined,
                      audit_period_start: periodStart || undefined, audit_period_end: periodEnd || undefined });
    setShowSetup(false); load();
  };

  const setCriterion = async (id: string, readiness: string) => {
    const r = await updateSoc2Criterion(id, { readiness });
    setData(r.data);
  };

  const toggleCat = (key: string) => {
    if (key === 'security') return;
    setCats(c => c.includes(key) ? c.filter(x=>x!==key) : [...c, key]);
  };

  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading SOC 2 readiness…</div>;

  // ── Not configured: show setup ──
  if (!data?.configured && !showSetup) {
    return (
      <div className="h-screen overflow-y-auto bg-slate-50">
        <div className="p-6 max-w-2xl mx-auto">
          <div className="card p-8 text-center mt-8">
            <div className="w-14 h-14 bg-cyan-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <ShieldCheck className="w-8 h-8 text-cyan-600" />
            </div>
            <h1 className="text-xl font-bold mb-2">SOC 2 Readiness</h1>
            <p className="text-sm text-slate-500 mb-6 max-w-md mx-auto">
              Track your readiness against the SOC 2 Trust Services Criteria. Choose Type I or Type II,
              select trust categories, and we'll map your existing findings to criteria gaps automatically.
            </p>
            <button onClick={()=>setShowSetup(true)} className="btn btn-primary bg-cyan-600 hover:bg-cyan-700">
              <Settings2 className="w-4 h-4" /> Set up SOC 2 engagement
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Setup form ──
  if (showSetup) {
    return (
      <div className="h-screen overflow-y-auto bg-slate-50">
        <div className="p-6 max-w-2xl mx-auto">
          <h1 className="text-xl font-bold mb-1">SOC 2 Engagement Setup</h1>
          <p className="text-sm text-slate-400 mb-6">Configure your readiness assessment</p>

          <div className="card p-6 space-y-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Report Type</label>
              <div className="grid grid-cols-2 gap-3">
                <button onClick={()=>setReportType('type1')}
                  className={`p-4 rounded-xl border-2 text-left ${reportType==='type1'?'border-cyan-400 bg-cyan-50':'border-slate-100'}`}>
                  <p className="font-bold text-sm">Type I</p>
                  <p className="text-xs text-slate-400">Controls at a point in time</p>
                </button>
                <button onClick={()=>setReportType('type2')}
                  className={`p-4 rounded-xl border-2 text-left ${reportType==='type2'?'border-cyan-400 bg-cyan-50':'border-slate-100'}`}>
                  <p className="font-bold text-sm">Type II</p>
                  <p className="text-xs text-slate-400">Controls over a period (3-12 mo)</p>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Trust Service Categories</label>
              <div className="space-y-2">
                {TRUST_CATS.map(c => (
                  <button key={c.key} onClick={()=>toggleCat(c.key)} disabled={c.mandatory}
                    className={`w-full p-3 rounded-xl border-2 text-left flex items-center gap-3 ${cats.includes(c.key)?'border-cyan-400 bg-cyan-50':'border-slate-100'} ${c.mandatory?'opacity-100':''}`}>
                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${cats.includes(c.key)?'bg-cyan-500 border-cyan-500':'border-slate-300'}`}>
                      {cats.includes(c.key) && <CheckCircle className="w-4 h-4 text-white" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{c.name} {c.mandatory && <span className="text-xs text-cyan-600">(required)</span>}</p>
                      <p className="text-xs text-slate-400">{c.desc}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {reportType === 'type2' && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Observation period start</label>
                  <input type="date" className="input" value={periodStart} onChange={e=>setPeriodStart(e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Observation period end</label>
                  <input type="date" className="input" value={periodEnd} onChange={e=>setPeriodEnd(e.target.value)} />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Target audit date</label>
              <input type="date" className="input" value={targetDate} onChange={e=>setTargetDate(e.target.value)} />
            </div>

            <div className="flex gap-2 justify-end pt-2">
              {data?.configured && <button onClick={()=>setShowSetup(false)} className="btn">Cancel</button>}
              <button onClick={runSetup} className="btn btn-primary bg-cyan-600 hover:bg-cyan-700">Create engagement</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Readiness dashboard ──
  const filtered = filter === 'all' ? data.criteria : data.criteria.filter((c:any)=>c.readiness===filter);

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-cyan-600" /> SOC 2 Readiness
            </h1>
            <p className="text-sm text-slate-400">
              {data.report_type === 'type2' ? 'Type II' : 'Type I'} ·
              {data.target_date && <span> Target: {new Date(data.target_date).toLocaleDateString()}</span>}
            </p>
          </div>
          <button onClick={()=>setShowSetup(true)} className="btn"><Settings2 className="w-4 h-4" /> Reconfigure</button>
        </div>

        {/* Overall readiness */}
        <div className="card p-6 mb-5 bg-slate-900 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Overall Readiness</p>
              <p className="text-4xl font-bold text-cyan-400">{data.overall_readiness}%</p>
              <p className="text-slate-400 text-xs mt-1 capitalize">Status: {data.status}</p>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <div className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400"/> {data.summary.ready} ready</div>
              <div className="flex items-center gap-2"><Clock className="w-4 h-4 text-blue-400"/> {data.summary.in_progress} in progress</div>
              <div className="flex items-center gap-2"><XCircle className="w-4 h-4 text-red-400"/> {data.summary.gaps} gaps</div>
              <div className="flex items-center gap-2"><Circle className="w-4 h-4 text-slate-500"/> {data.summary.not_started} not started</div>
            </div>
          </div>
          <div className="w-full bg-white/10 rounded-full h-2 mt-4">
            <div className="h-2 rounded-full bg-cyan-400" style={{width:`${data.overall_readiness}%`}} />
          </div>
        </div>

        {/* By category */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {Object.entries(data.by_category).map(([key, v]: any) => (
            <div key={key} className="card p-4">
              <p className="text-xs text-slate-400 mb-1">{v.name}</p>
              <p className="text-lg font-bold">{v.ready}/{v.total}</p>
              <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
                <div className="h-1.5 rounded-full bg-cyan-500" style={{width:`${v.total?v.ready/v.total*100:0}%`}} />
              </div>
            </div>
          ))}
        </div>

        {/* Filter */}
        <div className="flex gap-1 mb-4 bg-slate-100 p-1 rounded-xl w-fit">
          {['all','gap','in_progress','ready','not_started'].map(f => (
            <button key={f} onClick={()=>setFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg capitalize ${filter===f?'bg-white shadow-sm':'text-slate-500'}`}>
              {f.replace('_',' ')}
            </button>
          ))}
        </div>

        {/* Criteria list */}
        <div className="card divide-y divide-slate-50">
          {filtered.map((c: any) => {
            const r = READINESS[c.readiness as keyof typeof READINESS] || READINESS.not_started;
            const Icon = r.icon;
            return (
              <div key={c.criterion_id} className="px-5 py-3 flex items-center gap-3">
                <Icon className={`w-5 h-5 ${r.color} flex-shrink-0`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-500">{c.criterion_id}</span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded capitalize">{c.category.replace('_',' ')}</span>
                  </div>
                  <p className="text-sm text-slate-700">{c.title}</p>
                </div>
                <select value={c.readiness} onChange={e=>setCriterion(c.criterion_id, e.target.value)}
                  className={`text-xs border rounded-lg px-2 py-1 ${r.bg} ${r.color} border-current/20`}>
                  <option value="not_started">Not Started</option>
                  <option value="in_progress">In Progress</option>
                  <option value="ready">Ready</option>
                  <option value="gap">Gap</option>
                </select>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
