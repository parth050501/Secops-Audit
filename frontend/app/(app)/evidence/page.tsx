'use client';
import { useEffect, useState } from 'react';
import { listEvidence, uploadEvidenceDoc, createAttestation, deleteEvidence, getCoverage } from '@/lib/api';
import { FileCheck, Upload, FileText, UserCheck, Trash2, Plus, X, ShieldCheck } from 'lucide-react';

const FRAMEWORKS = [
  { key:'soc2', label:'SOC 2' }, { key:'iso27001', label:'ISO 27001' },
  { key:'pci_dss', label:'PCI DSS' }, { key:'hipaa', label:'HIPAA' }, { key:'nist_csf', label:'NIST CSF' },
];

export default function EvidencePage() {
  const [framework, setFramework] = useState('soc2');
  const [evidence, setEvidence] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showDoc, setShowDoc] = useState(false);
  const [showAttest, setShowAttest] = useState(false);
  const [msg, setMsg] = useState('');
  const [role, setRole] = useState('');

  // document form
  const [docForm, setDocForm] = useState<any>({ control_id:'', title:'', description:'', file:null });
  // attestation form
  const [attForm, setAttForm] = useState<any>({ control_id:'', title:'', attestation_note:'' });

  useEffect(() => {
    try { setRole(JSON.parse(localStorage.getItem('user')||'{}').role || ''); } catch {}
  }, []);

  const canManage = ['admin','manager','engineer'].includes(role);

  const load = () => {
    setLoading(true);
    listEvidence({ framework }).then(r => setEvidence(r.data)).catch(()=>{});
    getCoverage(framework).then(r => setCoverage(r.data)).catch(()=>{}).finally(()=>setLoading(false));
  };
  useEffect(() => { load(); }, [framework]);

  const submitDoc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docForm.file) { setMsg('Please choose a file'); return; }
    const fd = new FormData();
    fd.append('framework', framework);
    fd.append('control_id', docForm.control_id);
    fd.append('title', docForm.title);
    fd.append('description', docForm.description || '');
    fd.append('file', docForm.file);
    try {
      await uploadEvidenceDoc(fd);
      setMsg('Document uploaded'); setShowDoc(false);
      setDocForm({ control_id:'', title:'', description:'', file:null });
      load();
    } catch (err: any) { setMsg(err.response?.data?.detail || 'Upload failed'); }
  };

  const submitAttest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createAttestation({ framework, ...attForm });
      setMsg('Attestation recorded'); setShowAttest(false);
      setAttForm({ control_id:'', title:'', attestation_note:'' });
      load();
    } catch (err: any) { setMsg(err.response?.data?.detail || 'Failed'); }
  };

  const remove = async (id: number) => {
    if (!confirm('Delete this evidence?')) return;
    await deleteEvidence(id); load();
  };

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <FileCheck className="w-6 h-6 text-teal-600" /> Evidence &amp; Attestations
            </h1>
            <p className="text-sm text-slate-400">Satisfy controls with documents and human attestations — not just technical scans.</p>
          </div>
          <select className="select w-auto" value={framework} onChange={e=>setFramework(e.target.value)}>
            {FRAMEWORKS.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
          </select>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-800 flex justify-between">
          <span>{msg}</span><button onClick={()=>setMsg('')}><X className="w-4 h-4"/></button></div>}

        {/* Coverage summary */}
        {coverage && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            <div className="card p-4">
              <p className="text-xs text-slate-400">Readiness</p>
              <p className="text-2xl font-bold text-teal-600">{coverage.readiness_pct}%</p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-slate-400">Controls tracked</p>
              <p className="text-2xl font-bold">{coverage.total_controls_tracked}</p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-slate-400">Satisfied</p>
              <p className="text-2xl font-bold text-emerald-600">{coverage.satisfied}</p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-slate-400">Evidence items</p>
              <p className="text-2xl font-bold">{coverage.evidence_count}</p>
            </div>
          </div>
        )}

        {/* Actions */}
        {canManage && (
          <div className="flex gap-2 mb-5">
            <button onClick={()=>setShowDoc(true)} className="btn btn-primary bg-teal-600 hover:bg-teal-700">
              <Upload className="w-4 h-4" /> Upload document
            </button>
            <button onClick={()=>setShowAttest(true)} className="btn">
              <UserCheck className="w-4 h-4" /> Record attestation
            </button>
          </div>
        )}
        {!canManage && (
          <div className="mb-5 text-xs text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> Your role has read-only access to evidence.
          </div>
        )}

        {/* Evidence list */}
        {loading ? (
          <div className="text-sm text-slate-400">Loading…</div>
        ) : evidence.length === 0 ? (
          <div className="card p-10 text-center text-slate-400">
            <FileCheck className="w-10 h-10 mx-auto mb-3 opacity-40" />
            No evidence yet for {FRAMEWORKS.find(f=>f.key===framework)?.label}.
            {canManage && <p className="text-xs mt-1">Upload a document or record an attestation to get started.</p>}
          </div>
        ) : (
          <div className="card divide-y divide-slate-50">
            {evidence.map(e => (
              <div key={e.id} className="px-5 py-3 flex items-center gap-3">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${e.evidence_type==='document'?'bg-blue-50':'bg-violet-50'}`}>
                  {e.evidence_type==='document' ? <FileText className="w-5 h-5 text-blue-600"/> : <UserCheck className="w-5 h-5 text-violet-600"/>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-500">{e.control_id}</span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded capitalize">{e.evidence_type}</span>
                  </div>
                  <p className="text-sm text-slate-700">{e.title}</p>
                  {e.file_name && <p className="text-xs text-slate-400">{e.file_name}</p>}
                  {e.attestation_note && <p className="text-xs text-slate-400 truncate">{e.attestation_note}</p>}
                  <p className="text-[10px] text-slate-400 mt-0.5">by {e.created_by}</p>
                </div>
                {canManage && (
                  <button onClick={()=>remove(e.id)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload document modal */}
      {showDoc && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={()=>setShowDoc(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md" onClick={e=>e.stopPropagation()}>
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="font-bold">Upload evidence document</h2>
              <button onClick={()=>setShowDoc(false)}><X className="w-5 h-5 text-slate-400"/></button>
            </div>
            <form onSubmit={submitDoc} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Control ID *</label>
                <input className="input" required placeholder="e.g. CC6.1" value={docForm.control_id} onChange={e=>setDocForm({...docForm,control_id:e.target.value})} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Title *</label>
                <input className="input" required placeholder="Information Security Policy" value={docForm.title} onChange={e=>setDocForm({...docForm,title:e.target.value})} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Description</label>
                <input className="input" value={docForm.description} onChange={e=>setDocForm({...docForm,description:e.target.value})} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">File *</label>
                <input type="file" className="text-sm" required onChange={e=>setDocForm({...docForm,file:e.target.files?.[0]||null})} />
                <p className="text-[10px] text-slate-400 mt-1">PDF, Word, Excel, images, or text. Max 25MB.</p>
              </div>
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={()=>setShowDoc(false)} className="btn">Cancel</button>
                <button type="submit" className="btn btn-primary bg-teal-600 hover:bg-teal-700">Upload</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Attestation modal */}
      {showAttest && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={()=>setShowAttest(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md" onClick={e=>e.stopPropagation()}>
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="font-bold">Record an attestation</h2>
              <button onClick={()=>setShowAttest(false)}><X className="w-5 h-5 text-slate-400"/></button>
            </div>
            <form onSubmit={submitAttest} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Control ID *</label>
                <input className="input" required placeholder="e.g. CC1.1" value={attForm.control_id} onChange={e=>setAttForm({...attForm,control_id:e.target.value})} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Title *</label>
                <input className="input" required placeholder="Code of conduct in place" value={attForm.title} onChange={e=>setAttForm({...attForm,title:e.target.value})} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Attestation *</label>
                <textarea className="input" rows={3} required placeholder="Describe what you're attesting to and how it's evidenced…" value={attForm.attestation_note} onChange={e=>setAttForm({...attForm,attestation_note:e.target.value})} />
              </div>
              <p className="text-[10px] text-slate-400">This records you as the attesting person, with a timestamp.</p>
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={()=>setShowAttest(false)} className="btn">Cancel</button>
                <button type="submit" className="btn btn-primary bg-violet-600 hover:bg-violet-700">Record</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
