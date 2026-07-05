'use client';
import { useEffect, useState } from 'react';
import { listGroups, createGroup, updateGroup, deleteGroup, scanGroup, listAgents } from '@/lib/api';
import { CalendarClock, Plus, X, Play, Trash2, Server, Clock, Users, Edit2, CheckCircle2 } from 'lucide-react';

const SCHEDULES = [
  { key: 'manual',  label: 'Manual only' },
  { key: 'daily',   label: 'Daily' },
  { key: 'weekly',  label: 'Weekly' },
  { key: 'monthly', label: 'Monthly' },
];
const DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];

function fmt(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

export default function SchedulerPage() {
  const [groups, setGroups] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [msg, setMsg] = useState('');
  const [role, setRole] = useState('');

  const emptyForm = { name:'', description:'', agent_ids:[] as number[], schedule:'manual', schedule_time:'02:00', schedule_day:'Mon' };
  const [form, setForm] = useState<any>(emptyForm);

  const load = async () => {
    try {
      const [g, a] = await Promise.all([listGroups(), listAgents()]);
      setGroups(g.data || []); setAgents(a.data || []);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    try { setRole(JSON.parse(localStorage.getItem('user') || '{}').role || ''); } catch {}
    load();
  }, []);

  const canManage = role === 'admin' || role === 'engineer';

  const openCreate = () => { setEditing(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (g: any) => {
    setEditing(g);
    setForm({ name:g.name, description:g.description||'', agent_ids:g.agent_ids||[],
      schedule:g.schedule||'manual', schedule_time:g.schedule_time||'02:00', schedule_day:g.schedule_day||'Mon' });
    setShowForm(true);
  };

  const toggleAgent = (id: number) => {
    setForm((f: any) => ({ ...f,
      agent_ids: f.agent_ids.includes(id) ? f.agent_ids.filter((x:number)=>x!==id) : [...f.agent_ids, id] }));
  };

  const save = async () => {
    if (!form.name.trim()) { setMsg('Group name is required'); return; }
    try {
      if (editing) { await updateGroup(editing.id, form); setMsg(`Group "${form.name}" updated`); }
      else { await createGroup(form); setMsg(`Group "${form.name}" created`); }
      setShowForm(false); load();
    } catch (e:any) { setMsg(e.response?.data?.detail || 'Could not save group'); }
  };

  const remove = async (g: any) => {
    if (!confirm(`Delete group "${g.name}"? (Agents themselves are not deleted.)`)) return;
    try { await deleteGroup(g.id); setMsg(`Group "${g.name}" deleted`); load(); }
    catch (e:any) { setMsg(e.response?.data?.detail || 'Could not delete'); }
  };

  const runScan = async (g: any) => {
    try {
      const r = await scanGroup(g.id);
      setMsg(`Queued ${r.data.queued_jobs} scan${r.data.queued_jobs!==1?'s':''} across "${g.name}". Findings appear as agents report.`);
      load();
    } catch (e:any) { setMsg(e.response?.data?.detail || 'Could not start scan'); }
  };

  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading scheduler…</div>;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2"><CalendarClock className="w-5 h-5 text-teal-600" /> Scheduler</h1>
            <p className="text-sm text-slate-400">Group your systems and scan them together — on demand now, on a schedule automatically.</p>
          </div>
          {canManage && <button onClick={openCreate} className="btn btn-primary flex items-center gap-2 text-sm"><Plus className="w-4 h-4" /> New Group</button>}
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-100 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* Empty state */}
        {groups.length === 0 && (
          <div className="card p-8 text-center">
            <Users className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No asset groups yet.</p>
            <p className="text-xs text-slate-400 mt-1">Create a group (e.g. "Production Servers", "PCI Environment") and add your agents to scan them together.</p>
            {agents.length === 0 && <p className="text-xs text-amber-600 mt-2">You don't have any agents yet — deploy an agent first, then group it here.</p>}
          </div>
        )}

        {/* Group cards */}
        <div className="space-y-4">
          {groups.map(g => (
            <div key={g.id} className="card p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-bold text-slate-800">{g.name}</h3>
                    <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded-full">{g.agent_count} agent{g.agent_count!==1?'s':''}</span>
                  </div>
                  {g.description && <p className="text-xs text-slate-400 mb-2">{g.description}</p>}
                  {/* schedule line */}
                  <div className="flex items-center gap-4 text-xs text-slate-500 mt-1">
                    <span className="inline-flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      {g.schedule === 'manual' ? 'Manual only'
                        : `${g.schedule.charAt(0).toUpperCase()+g.schedule.slice(1)} at ${g.schedule_time}${g.schedule==='weekly'?` (${g.schedule_day})`:''}`}
                    </span>
                    {g.schedule !== 'manual' && <span>Next run: {fmt(g.next_run_at)}</span>}
                    {g.last_run_at && <span>Last run: {fmt(g.last_run_at)}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {canManage && (
                    <>
                      <button onClick={() => runScan(g)} disabled={g.agent_count===0}
                        className="btn btn-primary text-xs py-1 px-2 flex items-center gap-1 disabled:opacity-40" title={g.agent_count===0?'Add agents first':'Scan all agents in this group now'}>
                        <Play className="w-3 h-3" /> Scan Now
                      </button>
                      <button onClick={() => openEdit(g)} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400" title="Edit group"><Edit2 className="w-4 h-4" /></button>
                      {role === 'admin' && <button onClick={() => remove(g)} className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500" title="Delete group"><Trash2 className="w-4 h-4" /></button>}
                    </>
                  )}
                </div>
              </div>
              {/* member agents */}
              {g.agents?.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-50 flex flex-wrap gap-2">
                  {g.agents.map((a:any) => (
                    <span key={a.id} className="inline-flex items-center gap-1.5 text-xs bg-slate-50 border border-slate-100 rounded-lg px-2 py-1">
                      <Server className="w-3 h-3 text-slate-400" />
                      {a.name}
                      <span className={`w-1.5 h-1.5 rounded-full ${a.status==='connected'?'bg-emerald-500':'bg-slate-300'}`} />
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <p className="text-[11px] text-slate-400 mt-4 text-center">
          "Scan Now" queues a scan for every agent in the group immediately. Scheduled groups also run automatically at their set time — the collector runs all queued scans on its next poll.
        </p>
      </div>

      {/* Create / edit form */}
      {showForm && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white">
              <h2 className="font-bold text-slate-800">{editing ? 'Edit Group' : 'New Asset Group'}</h2>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Group name</label>
                <input className="input" placeholder="e.g. Production Servers, PCI Environment" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Description (optional)</label>
                <input className="input" placeholder="What's in this group" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} />
              </div>

              {/* agent selection */}
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Agents in this group</label>
                {agents.length === 0 ? (
                  <p className="text-xs text-slate-400 py-2">No agents available yet.</p>
                ) : (
                  <div className="border border-slate-200 rounded-lg divide-y divide-slate-50 max-h-48 overflow-y-auto">
                    {agents.map(a => (
                      <button key={a.id} onClick={() => toggleAgent(a.id)} type="button"
                        className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 ${form.agent_ids.includes(a.id)?'bg-teal-50':''}`}>
                        <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${form.agent_ids.includes(a.id)?'bg-teal-500 border-teal-500':'border-slate-300'}`}>
                          {form.agent_ids.includes(a.id) && <CheckCircle2 className="w-3 h-3 text-white" />}
                        </div>
                        <Server className="w-3.5 h-3.5 text-slate-400" />
                        <span className="flex-1">{a.name}</span>
                        <span className="text-[10px] text-slate-400 font-mono">{a.system_type}</span>
                      </button>
                    ))}
                  </div>
                )}
                <p className="text-[11px] text-slate-400 mt-1">{form.agent_ids.length} selected</p>
              </div>

              {/* schedule */}
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Schedule</label>
                <div className="grid grid-cols-4 gap-2">
                  {SCHEDULES.map(s => (
                    <button key={s.key} type="button" onClick={()=>setForm({...form,schedule:s.key})}
                      className={`text-xs py-2 rounded-lg border ${form.schedule===s.key?'border-teal-400 bg-teal-50 text-teal-700 font-medium':'border-slate-200 text-slate-500'}`}>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
              {form.schedule !== 'manual' && (
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="text-xs font-medium text-slate-600 mb-1 block">Time (UTC)</label>
                    <input type="time" className="input" value={form.schedule_time} onChange={e=>setForm({...form,schedule_time:e.target.value})} />
                  </div>
                  {form.schedule === 'weekly' && (
                    <div className="flex-1">
                      <label className="text-xs font-medium text-slate-600 mb-1 block">Day</label>
                      <select className="input" value={form.schedule_day} onChange={e=>setForm({...form,schedule_day:e.target.value})}>
                        {DAYS.map(d => <option key={d} value={d}>{d}</option>)}
                      </select>
                    </div>
                  )}
                  {form.schedule === 'monthly' && (
                    <div className="flex-1">
                      <label className="text-xs font-medium text-slate-600 mb-1 block">Day of month</label>
                      <input type="number" min={1} max={28} className="input" value={form.schedule_day||1} onChange={e=>setForm({...form,schedule_day:e.target.value})} />
                    </div>
                  )}
                </div>
              )}
              {form.schedule !== 'manual' && (
                <p className="text-[11px] text-teal-700 bg-teal-50 border border-teal-100 rounded-lg px-3 py-2">
                  This group will scan automatically {form.schedule === 'daily' ? 'every day' : form.schedule === 'weekly' ? 'every week' : 'every month'} at {form.schedule_time} UTC. You can also run it any time with "Scan Now."
                </p>
              )}
            </div>
            <div className="px-5 py-4 border-t border-slate-100 flex justify-end gap-2 sticky bottom-0 bg-white">
              <button onClick={() => setShowForm(false)} className="btn text-sm">Cancel</button>
              <button onClick={save} className="btn btn-primary text-sm">{editing ? 'Save changes' : 'Create group'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
