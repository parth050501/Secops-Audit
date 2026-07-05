'use client';
import { useEffect, useState } from 'react';
import { listTenantUsers, addTenantUser, updateTenantUserRole, removeTenantUser } from '@/lib/api';
import { Users, Plus, Trash2, X, ShieldCheck } from 'lucide-react';

const ROLES = [
  { key:'admin', label:'Admin', desc:'Full access, manages users' },
  { key:'manager', label:'Manager', desc:'Approve tickets, view reports' },
  { key:'engineer', label:'Engineer', desc:'Work tickets, run scans' },
  { key:'auditor', label:'Auditor', desc:'Read-only access to reports & evidence' },
];

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [msg, setMsg] = useState('');
  const [myRole, setMyRole] = useState('');
  const [form, setForm] = useState<any>({ name:'', email:'', password:'', role:'engineer' });

  useEffect(() => {
    try { setMyRole(JSON.parse(localStorage.getItem('user')||'{}').role || ''); } catch {}
  }, []);
  const isAdmin = myRole === 'admin';

  const load = () => { setLoading(true); listTenantUsers().then(r=>setUsers(r.data)).catch(()=>{}).finally(()=>setLoading(false)); };
  useEffect(() => { load(); }, []);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await addTenantUser(form);
      setMsg(`Added ${form.name}`); setShowAdd(false);
      setForm({ name:'', email:'', password:'', role:'engineer' });
      load();
    } catch (err: any) { setMsg(err.response?.data?.detail || 'Failed to add user'); }
  };

  const changeRole = async (id: number, role: string) => {
    try { await updateTenantUserRole(id, role); load(); }
    catch (err: any) { setMsg(err.response?.data?.detail || 'Failed'); }
  };

  const remove = async (id: number, name: string) => {
    if (!confirm(`Remove ${name}?`)) return;
    try { await removeTenantUser(id); load(); }
    catch (err: any) { setMsg(err.response?.data?.detail || 'Failed'); }
  };

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2"><Users className="w-6 h-6 text-teal-600" /> Team</h1>
            <p className="text-sm text-slate-400">Manage who in your organization can access this workspace.</p>
          </div>
          {isAdmin && (
            <button onClick={()=>setShowAdd(true)} className="btn btn-primary bg-teal-600 hover:bg-teal-700">
              <Plus className="w-4 h-4" /> Add user
            </button>
          )}
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-800 flex justify-between">
          <span>{msg}</span><button onClick={()=>setMsg('')}><X className="w-4 h-4"/></button></div>}

        {!isAdmin && (
          <div className="mb-4 text-xs text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" /> Only an admin can add or change users. You can view the team.
          </div>
        )}

        {loading ? <div className="text-sm text-slate-400">Loading…</div> : (
          <div className="card divide-y divide-slate-50">
            {users.map(u => (
              <div key={u.id} className="px-5 py-3 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-teal-500 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                  {u.name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800">{u.name}</p>
                  <p className="text-xs text-slate-400">{u.email}</p>
                </div>
                {isAdmin ? (
                  <select value={u.role} onChange={e=>changeRole(u.id, e.target.value)}
                    className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white">
                    {ROLES.map(r => <option key={r.key} value={r.key}>{r.label}</option>)}
                  </select>
                ) : (
                  <span className="text-xs px-2 py-1 bg-slate-100 text-slate-600 rounded-lg capitalize">{u.role}</span>
                )}
                {isAdmin && (
                  <button onClick={()=>remove(u.id, u.name)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={()=>setShowAdd(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md" onClick={e=>e.stopPropagation()}>
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="font-bold">Add team member</h2>
              <button onClick={()=>setShowAdd(false)}><X className="w-5 h-5 text-slate-400"/></button>
            </div>
            <form onSubmit={add} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Name *</label>
                  <input className="input" required value={form.name} onChange={e=>setForm({...form,name:e.target.value})} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Email *</label>
                  <input className="input" type="email" required value={form.email} onChange={e=>setForm({...form,email:e.target.value})} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Temporary password *</label>
                <input className="input" required value={form.password} onChange={e=>setForm({...form,password:e.target.value})} placeholder="They change it on first login" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
                <select className="select" value={form.role} onChange={e=>setForm({...form,role:e.target.value})}>
                  {ROLES.map(r => <option key={r.key} value={r.key}>{r.label} — {r.desc}</option>)}
                </select>
              </div>
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={()=>setShowAdd(false)} className="btn">Cancel</button>
                <button type="submit" className="btn btn-primary bg-teal-600 hover:bg-teal-700">Add user</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
