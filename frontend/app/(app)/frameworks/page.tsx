'use client';
import { useEffect, useState } from 'react';
import {
  listFrameworksAdmin, getFrameworkControlsAdmin, createFrameworkAdmin, deleteFrameworkAdmin,
  addControl, editControl, deleteControl, bulkUploadControls, downloadControlsTemplate,
} from '@/lib/api';
import { Library, Plus, X, Upload, Download, Trash2, Edit2, ChevronRight, ArrowLeft, Search } from 'lucide-react';

const WEIGHTS = ['critical', 'high', 'medium', 'low'];

export default function FrameworksPage() {
  const [frameworks, setFrameworks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);   // framework being viewed
  const [controls, setControls] = useState<any[]>([]);
  const [msg, setMsg] = useState('');
  const [role, setRole] = useState('');
  const [search, setSearch] = useState('');

  // modals
  const [showNewFw, setShowNewFw] = useState(false);
  const [newFw, setNewFw] = useState({ name: '', description: '' });
  const [showCtrl, setShowCtrl] = useState(false);
  const [editingCtrl, setEditingCtrl] = useState<any>(null);
  const [ctrlForm, setCtrlForm] = useState({ control_id: '', title: '', category: 'general', weight: 'medium', guidance: '' });
  const [uploading, setUploading] = useState(false);
  const [replaceExisting, setReplaceExisting] = useState(false);

  const loadFrameworks = async () => {
    try { const r = await listFrameworksAdmin(); setFrameworks(r.data || []); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    try { setRole(JSON.parse(localStorage.getItem('user') || '{}').role || ''); } catch {}
    loadFrameworks();
  }, []);

  const canManage = role === 'admin' || role === 'engineer';

  const openFramework = async (fw: any) => {
    setSelected(fw); setSearch('');
    const r = await getFrameworkControlsAdmin(fw.id);
    setControls(r.data.controls || []);
  };
  const reloadControls = async () => {
    if (!selected) return;
    const r = await getFrameworkControlsAdmin(selected.id);
    setControls(r.data.controls || []);
    loadFrameworks(); // refresh counts
  };

  const createFw = async () => {
    if (!newFw.name.trim()) { setMsg('Name required'); return; }
    try { await createFrameworkAdmin(newFw); setShowNewFw(false); setNewFw({ name: '', description: '' }); setMsg('Framework created'); loadFrameworks(); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Could not create'); }
  };
  const removeFw = async (fw: any) => {
    if (!confirm(`Delete framework "${fw.name}" and all its controls?`)) return;
    try { await deleteFrameworkAdmin(fw.id); setMsg('Framework deleted'); if (selected?.id === fw.id) setSelected(null); loadFrameworks(); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Could not delete'); }
  };

  const openAddCtrl = () => { setEditingCtrl(null); setCtrlForm({ control_id: '', title: '', category: 'general', weight: 'medium', guidance: '' }); setShowCtrl(true); };
  const openEditCtrl = (c: any) => { setEditingCtrl(c); setCtrlForm({ control_id: c.control_id, title: c.title, category: c.category, weight: c.weight, guidance: c.guidance || '' }); setShowCtrl(true); };
  const saveCtrl = async () => {
    if (!ctrlForm.control_id.trim() || !ctrlForm.title.trim()) { setMsg('Control ID and title required'); return; }
    try {
      if (editingCtrl) await editControl(editingCtrl.id, ctrlForm);
      else await addControl(selected.id, ctrlForm);
      setShowCtrl(false); reloadControls();
    } catch (e: any) { setMsg(e.response?.data?.detail || 'Could not save control'); }
  };
  const removeCtrl = async (c: any) => {
    if (!confirm(`Delete control ${c.control_id}?`)) return;
    try { await deleteControl(c.id); reloadControls(); } catch (e: any) { setMsg(e.response?.data?.detail || 'Could not delete'); }
  };
  const doBulkUpload = async (file: File) => {
    setUploading(true); setMsg('Uploading controls…');
    try { const r = await bulkUploadControls(selected.id, file, replaceExisting); setMsg(`Imported ${r.data.created} controls${r.data.removed ? `, replaced ${r.data.removed}` : ''}${r.data.error_count ? `, ${r.data.error_count} skipped` : ''}.`); reloadControls(); }
    catch (e: any) { setMsg(e.response?.data?.detail || 'Upload failed'); }
    finally { setUploading(false); }
  };

  const filteredControls = controls.filter(c => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return c.control_id.toLowerCase().includes(q) || c.title.toLowerCase().includes(q) || (c.category || '').toLowerCase().includes(q);
  });

  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading frameworks…</div>;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-100 rounded-lg text-sm text-teal-800">{msg}</div>}

        {!selected ? (
          <>
            {/* Framework list */}
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h1 className="text-xl font-bold flex items-center gap-2"><Library className="w-5 h-5 text-teal-600" /> Frameworks & Controls</h1>
                <p className="text-sm text-slate-400">View and manage the controls in each framework. Add the full official control sets, or create your own.</p>
              </div>
              {canManage && <button onClick={() => setShowNewFw(true)} className="btn btn-primary flex items-center gap-2 text-sm"><Plus className="w-4 h-4" /> New Framework</button>}
            </div>

            <div className="mb-3 px-4 py-3 bg-amber-50 border border-amber-100 rounded-xl text-xs text-amber-800">
              The built-in frameworks currently include a representative set of controls. Use "View & edit" to add the complete official control sets from authoritative sources, or create your own custom framework.
            </div>

            <div className="grid gap-3">
              {frameworks.map(fw => (
                <div key={fw.id} className="card p-4 flex items-center justify-between hover:border-slate-300 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full" style={{ background: fw.color || '#666' }} />
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-slate-800">{fw.name}</p>
                        {fw.is_builtin && <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded-full">Built-in</span>}
                        {fw.custom && <span className="text-[10px] px-1.5 py-0.5 bg-teal-50 text-teal-600 rounded-full">Custom</span>}
                      </div>
                      <p className="text-xs text-slate-400">{fw.control_count} control{fw.control_count !== 1 ? 's' : ''}{fw.description ? ` · ${fw.description}` : ''}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => openFramework(fw)} className="btn text-xs py-1 px-3 flex items-center gap-1">View & edit <ChevronRight className="w-3 h-3" /></button>
                    {canManage && fw.custom && role === 'admin' && (
                      <button onClick={() => removeFw(fw)} className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500" title="Delete framework"><Trash2 className="w-4 h-4" /></button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <>
            {/* Control editor for a framework */}
            <button onClick={() => { setSelected(null); loadFrameworks(); }} className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1 mb-4"><ArrowLeft className="w-4 h-4" /> All frameworks</button>
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h1 className="text-xl font-bold flex items-center gap-2">{selected.name}</h1>
                <p className="text-sm text-slate-400">{controls.length} controls {selected.is_builtin && '· built-in (you can add more)'}</p>
              </div>
              {canManage && (
                <div className="flex gap-2">
                  <button onClick={() => downloadControlsTemplate().catch(() => setMsg('Could not download'))} className="btn text-sm flex items-center gap-1"><Download className="w-4 h-4" /> Template</button>
                  <label className="flex items-center gap-1.5 text-xs text-slate-500 mr-1" title="Delete this framework's current controls before importing, so it ends up with exactly the uploaded set">
                    <input type="checkbox" checked={replaceExisting} onChange={e=>setReplaceExisting(e.target.checked)} />
                    Replace existing
                  </label>
                  <label className={`btn text-sm cursor-pointer flex items-center gap-1 ${uploading ? 'opacity-50' : ''}`}>
                    <Upload className="w-4 h-4" /> {uploading ? 'Importing…' : 'Bulk Upload'}
                    <input type="file" accept=".csv" className="hidden" disabled={uploading} onChange={e => { const f = e.target.files?.[0]; if (f) doBulkUpload(f); e.currentTarget.value = ''; }} />
                  </label>
                  <button onClick={openAddCtrl} className="btn btn-primary text-sm flex items-center gap-1"><Plus className="w-4 h-4" /> Add Control</button>
                </div>
              )}
            </div>

            {/* search */}
            <div className="mb-3 relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input className="input pl-9" placeholder="Search controls…" value={search} onChange={e => setSearch(e.target.value)} />
            </div>

            <div className="card divide-y divide-slate-50">
              {filteredControls.length === 0 && <div className="px-5 py-8 text-center text-sm text-slate-400">{controls.length === 0 ? 'No controls yet. Add them individually or bulk-upload a CSV.' : 'No controls match your search.'}</div>}
              {filteredControls.map(c => (
                <div key={c.id} className="px-5 py-3 flex items-center gap-3">
                  <span className="text-xs font-mono font-bold text-slate-500 w-20 flex-shrink-0">{c.control_id}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-800">{c.title}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-slate-400">{c.category}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${c.weight === 'critical' ? 'bg-red-50 text-red-600' : c.weight === 'high' ? 'bg-orange-50 text-orange-600' : 'bg-slate-100 text-slate-500'}`}>{c.weight}</span>
                    </div>
                  </div>
                  {canManage && (
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button onClick={() => openEditCtrl(c)} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400" title="Edit"><Edit2 className="w-3.5 h-3.5" /></button>
                      <button onClick={() => removeCtrl(c)} className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500" title="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-3">Showing {filteredControls.length} of {controls.length} controls. Bulk upload accepts CSV: control_id, title, category, weight, guidance.</p>
          </>
        )}
      </div>

      {/* New framework modal */}
      {showNewFw && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-bold text-slate-800">New Framework</h2>
              <button onClick={() => setShowNewFw(false)} className="text-slate-400"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-5 space-y-3">
              <div><label className="text-xs font-medium text-slate-600 mb-1 block">Name</label>
                <input className="input" placeholder="e.g. SBI Internal Audit 2026" value={newFw.name} onChange={e => setNewFw({ ...newFw, name: e.target.value })} /></div>
              <div><label className="text-xs font-medium text-slate-600 mb-1 block">Description (optional)</label>
                <input className="input" value={newFw.description} onChange={e => setNewFw({ ...newFw, description: e.target.value })} /></div>
              <p className="text-[11px] text-slate-400">After creating it, open it to add controls (individually or bulk CSV upload).</p>
            </div>
            <div className="px-5 py-4 border-t border-slate-100 flex justify-end gap-2">
              <button onClick={() => setShowNewFw(false)} className="btn text-sm">Cancel</button>
              <button onClick={createFw} className="btn btn-primary text-sm">Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Control add/edit modal */}
      {showCtrl && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-bold text-slate-800">{editingCtrl ? 'Edit Control' : 'Add Control'}</h2>
              <button onClick={() => setShowCtrl(false)} className="text-slate-400"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-5 space-y-3">
              <div><label className="text-xs font-medium text-slate-600 mb-1 block">Control ID</label>
                <input className="input" placeholder="e.g. CC6.1" value={ctrlForm.control_id} onChange={e => setCtrlForm({ ...ctrlForm, control_id: e.target.value })} /></div>
              <div><label className="text-xs font-medium text-slate-600 mb-1 block">Title</label>
                <input className="input" placeholder="What the control requires" value={ctrlForm.title} onChange={e => setCtrlForm({ ...ctrlForm, title: e.target.value })} /></div>
              <div className="flex gap-3">
                <div className="flex-1"><label className="text-xs font-medium text-slate-600 mb-1 block">Category</label>
                  <input className="input" value={ctrlForm.category} onChange={e => setCtrlForm({ ...ctrlForm, category: e.target.value })} /></div>
                <div className="flex-1"><label className="text-xs font-medium text-slate-600 mb-1 block">Weight</label>
                  <select className="input" value={ctrlForm.weight} onChange={e => setCtrlForm({ ...ctrlForm, weight: e.target.value })}>
                    {WEIGHTS.map(w => <option key={w} value={w}>{w}</option>)}
                  </select></div>
              </div>
              <div><label className="text-xs font-medium text-slate-600 mb-1 block">Guidance (optional)</label>
                <textarea className="input h-16 resize-none" value={ctrlForm.guidance} onChange={e => setCtrlForm({ ...ctrlForm, guidance: e.target.value })} /></div>
            </div>
            <div className="px-5 py-4 border-t border-slate-100 flex justify-end gap-2">
              <button onClick={() => setShowCtrl(false)} className="btn text-sm">Cancel</button>
              <button onClick={saveCtrl} className="btn btn-primary text-sm">{editingCtrl ? 'Save' : 'Add'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
