'use client';
import { useEffect, useState } from 'react';
import { getPolicies, createPolicy, updatePolicy, deletePolicy, evaluatePolicies, bulkUploadPolicies, downloadPolicyTemplate } from '@/lib/api';
import { Plus, Zap, Trash2, X, CheckCircle, XCircle, Clock, FileText, Upload, Download, Search, ToggleLeft, ToggleRight } from 'lucide-react';

const CATEGORIES = ['access_control','identity','encryption','logging','network_security','config','patching','data_protection','endpoint','availability','risk'];
const CONNECTOR_CATS = ['network','server','cloud','identity','siem','database','custom'];
const OPERATORS = [
  {v:'equals',l:'equals'},{v:'not_equals',l:'does not equal'},
  {v:'contains',l:'contains'},{v:'not_contains',l:'does not contain'},
  {v:'gt',l:'greater than'},{v:'lt',l:'less than'},
  {v:'gte',l:'at least'},{v:'lte',l:'at most'},
  {v:'exists',l:'exists'},{v:'not_exists',l:'does not exist'},
];

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<any[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [msg, setMsg] = useState('');
  const [search, setSearch] = useState('');
  const [uploading, setUploading] = useState(false);
  const [page, setPage] = useState(1);
  const PER_PAGE = 25;
  const [form, setForm] = useState<any>({
    policy_id:'', title:'', description:'', category:'config', severity:'medium',
    framework:'custom', mapped_control:'', eval_mode:'manual',
    target_connector_category:'', rule_logic:{ field:'', operator:'equals', value:'' },
  });

  const load = () => getPolicies().then(r => setPolicies(r.data)).catch(()=>{});
  useEffect(() => { load(); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {...form};
    if (form.eval_mode !== 'rule') delete payload.rule_logic;
    if (form.eval_mode === 'manual') delete payload.target_connector_category;
    try {
      await createPolicy(payload);
      setMsg('Policy created.');
      setShowAdd(false);
      setForm({policy_id:'',title:'',description:'',category:'config',severity:'medium',framework:'custom',mapped_control:'',eval_mode:'manual',target_connector_category:'',rule_logic:{field:'',operator:'equals',value:''}});
      load();
    } catch (e: any) { setMsg(e.response?.data?.detail || 'Failed'); }
  };

  const attest = async (id: number, status: string) => {
    await updatePolicy(id, { status, last_result: `Manually attested as ${status}` });
    load();
  };

  const runEval = async () => {
    setEvaluating(true); setMsg('Evaluating all automated policies…');
    try { const r = await evaluatePolicies(); setMsg(`Evaluated ${r.data.evaluated} policies.`); load(); }
    finally { setEvaluating(false); }
  };

  const remove = async (id: number) => { await deletePolicy(id); load(); };

  const toggleEnabled = async (p: any) => {
    await updatePolicy(p.id, { enabled: !p.enabled });
    load();
  };

  const handleBulkUpload = async (file: File) => {
    if (!file) return;
    setUploading(true); setMsg('Uploading policies…');
    try {
      const r = await bulkUploadPolicies(file);
      setMsg(`Imported ${r.data.created} policies${r.data.error_count ? `, ${r.data.error_count} rows skipped` : ''}.`);
      load();
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Upload failed');
    } finally { setUploading(false); }
  };

  // search filter
  const filtered = policies.filter(p => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (p.title || '').toLowerCase().includes(q)
      || (p.policy_id || '').toLowerCase().includes(q)
      || (p.category || '').toLowerCase().includes(q)
      || (p.mapped_control || '').toLowerCase().includes(q);
  });
  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const pageItems = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  const passing = policies.filter(p => p.status === 'passing').length;
  const failing = policies.filter(p => p.status === 'failing').length;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold">Custom Policies</h1>
            <p className="text-sm text-slate-400">Your organization's own controls — layered on top of the mandated framework</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => downloadPolicyTemplate().catch(() => setMsg('Could not download template'))} className="btn" title="Download CSV template">
              <Download className="w-4 h-4" /> Template
            </button>
            <label className={`btn cursor-pointer ${uploading ? 'opacity-50' : ''}`}>
              <Upload className="w-4 h-4" /> {uploading ? 'Importing…' : 'Bulk Upload'}
              <input type="file" accept=".csv" className="hidden" disabled={uploading}
                onChange={e => { const f = e.target.files?.[0]; if (f) handleBulkUpload(f); e.currentTarget.value=''; }} />
            </label>
            <button onClick={runEval} disabled={evaluating} className="btn">
              <Zap className="w-4 h-4" /> {evaluating ? 'Evaluating…' : 'Run Evaluation'}
            </button>
            <button onClick={() => setShowAdd(true)} className="btn btn-primary">
              <Plus className="w-4 h-4" /> Add Policy
            </button>
          </div>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-800">{msg}</div>}

        <div className="grid grid-cols-3 gap-3 mb-5">
          <div className="card p-4"><p className="text-xs text-slate-400 uppercase tracking-wider">Total Policies</p><p className="text-2xl font-bold">{policies.length}</p></div>
          <div className="card p-4"><p className="text-xs text-slate-400 uppercase tracking-wider">Passing</p><p className="text-2xl font-bold text-emerald-600">{passing}</p></div>
          <div className="card p-4"><p className="text-xs text-slate-400 uppercase tracking-wider">Failing</p><p className="text-2xl font-bold text-red-500">{failing}</p></div>
        </div>

        {/* Search */}
        <div className="mb-3 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            className="input pl-9"
            placeholder="Search policies by title, ID, category, or control…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
        </div>

        <div className="card divide-y divide-slate-50">
          {!policies.length && (
            <div className="px-5 py-12 text-center">
              <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-400">No custom policies yet.</p>
              <p className="text-xs text-slate-400 mt-1">Add your company's internal controls one at a time, or use Bulk Upload to import many at once.</p>
            </div>
          )}
          {policies.length > 0 && !filtered.length && (
            <div className="px-5 py-8 text-center text-sm text-slate-400">No policies match "{search}".</div>
          )}
          {pageItems.map(p => (
            <div key={p.id} className={`px-5 py-4 ${!p.enabled ? 'opacity-50' : ''}`}>
              <div className="flex items-start gap-3">
                {p.status === 'passing' ? <CheckCircle className="w-5 h-5 text-emerald-500 mt-0.5 flex-shrink-0" />
                  : p.status === 'failing' ? <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                  : <Clock className="w-5 h-5 text-slate-300 mt-0.5 flex-shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    {p.policy_id && <span className="text-xs font-mono font-bold text-slate-500">{p.policy_id}</span>}
                    <span className={`badge badge-${p.severity}`}>{p.severity}</span>
                    <span className="badge badge-info">{p.eval_mode}</span>
                    {!p.enabled && <span className="text-[10px] px-1.5 py-0.5 bg-slate-200 text-slate-500 rounded font-medium">DISABLED</span>}
                    {p.mapped_control && <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded font-mono">→ {p.mapped_control}</span>}
                  </div>
                  <p className="text-sm font-medium text-slate-800">{p.title}</p>
                  {p.description && <p className="text-xs text-slate-500 mt-0.5">{p.description}</p>}
                  {p.rule_description && <p className="text-xs text-violet-600 mt-1 font-mono">{p.rule_description}</p>}
                  {p.last_result && <p className="text-xs text-slate-400 mt-1">{p.last_result}</p>}
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  {/* Enable/disable toggle */}
                  <button onClick={() => toggleEnabled(p)} className="text-slate-400 hover:text-teal-600" title={p.enabled ? 'Disable (exclude from scanning)' : 'Enable'}>
                    {p.enabled ? <ToggleRight className="w-6 h-6 text-teal-500" /> : <ToggleLeft className="w-6 h-6" />}
                  </button>
                  {p.eval_mode === 'manual' && p.enabled && (
                    <div className="flex gap-1">
                      <button onClick={() => attest(p.id,'passing')} className="btn text-xs py-1 px-2 text-emerald-600">Pass</button>
                      <button onClick={() => attest(p.id,'failing')} className="btn text-xs py-1 px-2 text-red-500">Fail</button>
                    </div>
                  )}
                  <button onClick={() => remove(p.id)} className="btn text-xs py-1 px-2 text-slate-400"><Trash2 className="w-3 h-3" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 text-sm">
            <span className="text-slate-400">Showing {(page-1)*PER_PAGE+1}–{Math.min(page*PER_PAGE, filtered.length)} of {filtered.length}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page<=1} className="btn text-xs disabled:opacity-40">Previous</button>
              <span className="px-3 py-1 text-slate-500">Page {page} of {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page>=totalPages} className="btn text-xs disabled:opacity-40">Next</button>
            </div>
          </div>
        )}

        {/* Add modal */}
        {showAdd && (
          <div className="fixed inset-0 bg-black/60 flex items-start justify-center z-50 p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl w-full max-w-xl shadow-2xl my-8">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <h2 className="font-bold text-lg">Add Custom Policy</h2>
                <button onClick={() => setShowAdd(false)} className="btn py-1 px-2"><X className="w-4 h-4" /></button>
              </div>
              <form onSubmit={submit} className="p-6 space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Policy ID</label>
                    <input className="input" placeholder="ACME-001" value={form.policy_id} onChange={e=>setForm({...form,policy_id:e.target.value})} />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs font-medium text-slate-600 mb-1">Title *</label>
                    <input className="input" required value={form.title} onChange={e=>setForm({...form,title:e.target.value})} />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Description</label>
                  <textarea className="input h-16 resize-none" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Category</label>
                    <select className="select" value={form.category} onChange={e=>setForm({...form,category:e.target.value})}>
                      {CATEGORIES.map(c=><option key={c} value={c}>{c.replace('_',' ')}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Severity</label>
                    <select className="select" value={form.severity} onChange={e=>setForm({...form,severity:e.target.value})}>
                      {['critical','high','medium','low'].map(s=><option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Maps to control</label>
                    <input className="input" placeholder="CC6.1" value={form.mapped_control} onChange={e=>setForm({...form,mapped_control:e.target.value})} />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Evaluation mode</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[{v:'manual',l:'Manual',d:'Human attests'},{v:'connector',l:'Connector',d:'Auto-check findings'},{v:'rule',l:'Rule logic',d:'Custom condition'}].map(m=>(
                      <button key={m.v} type="button" onClick={()=>setForm({...form,eval_mode:m.v})}
                        className={`p-2 rounded-lg border-2 text-left transition-all ${form.eval_mode===m.v?'border-teal-400 bg-teal-50':'border-slate-100'}`}>
                        <p className="text-xs font-semibold">{m.l}</p>
                        <p className="text-[10px] text-slate-400">{m.d}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {(form.eval_mode === 'connector' || form.eval_mode === 'rule') && (
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Target connector category</label>
                    <select className="select" value={form.target_connector_category} onChange={e=>setForm({...form,target_connector_category:e.target.value})}>
                      <option value="">Select…</option>
                      {CONNECTOR_CATS.map(c=><option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                )}

                {form.eval_mode === 'rule' && (
                  <div className="bg-violet-50 border border-violet-100 rounded-lg p-3">
                    <label className="block text-xs font-semibold text-violet-700 mb-2">Rule: FAIL the policy if…</label>
                    <div className="grid grid-cols-3 gap-2">
                      <input className="input text-sm" placeholder="field (e.g. mfa_enabled)" value={form.rule_logic.field} onChange={e=>setForm({...form,rule_logic:{...form.rule_logic,field:e.target.value}})} />
                      <select className="select text-sm" value={form.rule_logic.operator} onChange={e=>setForm({...form,rule_logic:{...form.rule_logic,operator:e.target.value}})}>
                        {OPERATORS.map(o=><option key={o.v} value={o.v}>{o.l}</option>)}
                      </select>
                      <input className="input text-sm" placeholder="value" value={form.rule_logic.value} onChange={e=>setForm({...form,rule_logic:{...form.rule_logic,value:e.target.value}})} />
                    </div>
                    <p className="text-[10px] text-violet-500 mt-2">Evaluated against data collected from the target connector category.</p>
                  </div>
                )}

                <div className="flex gap-2 justify-end pt-2">
                  <button type="button" onClick={()=>setShowAdd(false)} className="btn">Cancel</button>
                  <button type="submit" className="btn btn-primary">Create Policy</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
