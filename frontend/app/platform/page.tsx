'use client';
import { useEffect, useState } from 'react';
import { platformLogin, platformOverview, platformTenants, platformUpdatePlan, platformUpdateStatus, platformDeleteTenant, platformImpersonate, platformOnboardTenant, platformListTeam, platformAddTeam, platformUpdateTeamRole, platformRemoveTeam } from '@/lib/api';
import { Shield, Building2, DollarSign, Users, Plug, TrendingUp, LogIn, Trash2, AlertTriangle, Plus, X, UserCog } from 'lucide-react';

export default function PlatformConsole() {
  const [authed, setAuthed] = useState(false);
  const [email, setEmail] = useState('super@secops.ai');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [overview, setOverview] = useState<any>(null);
  const [tenants, setTenants] = useState<any[]>([]);
  const [msg, setMsg] = useState('');
  const [showOnboard, setShowOnboard] = useState(false);
  const [onb, setOnb] = useState<any>({name:'',industry:'technology',active_framework:'soc2',plan:'starter',admin_name:'',admin_email:'',admin_password:''});
  const [onbErr, setOnbErr] = useState('');
  const [team, setTeam] = useState<any[]>([]);
  const [showTeam, setShowTeam] = useState(false);
  const [tm, setTm] = useState<any>({name:'',email:'',password:'',role:'analyst'});
  const [tmErr, setTmErr] = useState('');
  const [myRole, setMyRole] = useState('');

  const PLATFORM_ROLES = [
    {key:'super_admin', label:'Super Admin', desc:'Everything incl. billing & team'},
    {key:'admin', label:'Admin', desc:'Onboard tenants & manage team, no billing'},
    {key:'analyst', label:'Analyst', desc:'Work in tenants, no onboarding/billing/team'},
    {key:'read_only', label:'Read Only', desc:'View everything, change nothing'},
  ];

  const addTeamMember = async (e: React.FormEvent) => {
    e.preventDefault(); setTmErr('');
    try {
      await platformAddTeam(tm);
      setMsg(`Added ${tm.name} to the team`);
      setShowTeam(false);
      setTm({name:'',email:'',password:'',role:'analyst'});
      loadTeam();
    } catch (err: any) { setTmErr(err.response?.data?.detail || 'Failed to add team member'); }
  };

  const changeTeamRole = async (id: number, role: string) => {
    try { await platformUpdateTeamRole(id, role); loadTeam(); }
    catch (err: any) { setMsg(err.response?.data?.detail || 'Failed'); }
  };

  const removeTeamMember = async (id: number, name: string) => {
    if (!confirm(`Remove ${name} from the platform team?`)) return;
    try { await platformRemoveTeam(id); loadTeam(); }
    catch (err: any) { setMsg(err.response?.data?.detail || 'Failed'); }
  };

  const loadTeam = () => { platformListTeam().then(r => setTeam(r.data)).catch(()=>{}); };

  const onboard = async (e: React.FormEvent) => {
    e.preventDefault(); setOnbErr('');
    try {
      const r = await platformOnboardTenant(onb);
      setMsg(`Onboarded ${r.data.name}`);
      setShowOnboard(false);
      setOnb({name:'',industry:'technology',active_framework:'soc2',plan:'starter',admin_name:'',admin_email:'',admin_password:''});
      load();
    } catch (err: any) { setOnbErr(err.response?.data?.detail || 'Failed to onboard tenant'); }
  };

  useEffect(() => {
    if (typeof window !== 'undefined' && localStorage.getItem('platform_token')) {
      setAuthed(true);
    }
  }, []);

  useEffect(() => { if (authed) load(); }, [authed]);

  const load = () => {
    platformOverview().then(r => setOverview(r.data)).catch(()=>{});
    platformTenants().then(r => setTenants(r.data)).catch(()=>{});
    loadTeam();
    // capture my own role from the token (for hiding team-management actions)
    try {
      const t = localStorage.getItem('platform_token');
      if (t) { const p = JSON.parse(atob(t.split('.')[1])); setMyRole(p.role || ''); }
    } catch {}
  };

  const login = async (e: React.FormEvent) => {
    e.preventDefault(); setErr('');
    try {
      const r = await platformLogin(email, password);
      localStorage.setItem('platform_token', r.data.token);
      setAuthed(true);
    } catch { setErr('Invalid platform credentials'); }
  };

  const logout = () => { localStorage.removeItem('platform_token'); setAuthed(false); };

  const changePlan = async (id: number, plan: string) => {
    await platformUpdatePlan(id, plan); setMsg(`Plan updated to ${plan}`); load();
  };
  const changeStatus = async (id: number, status: string) => {
    await platformUpdateStatus(id, status); setMsg(`Status set to ${status}`); load();
  };
  const impersonate = async (id: number, name: string) => {
    const r = await platformImpersonate(id);
    localStorage.setItem('token', r.data.token);
    localStorage.setItem('user', JSON.stringify(r.data.user));
    window.location.href = '/dashboard';
  };
  const removeTenant = async (id: number, name: string) => {
    if (!confirm(`Delete tenant "${name}" and ALL its data? This cannot be undone.`)) return;
    await platformDeleteTenant(id); setMsg(`Tenant deleted`); load();
  };

  // ── Login screen ──
  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="w-full max-w-sm">
          <div className="flex items-center justify-center gap-2.5 mb-6">
            <div className="w-9 h-9 bg-violet-500 rounded-xl flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-white font-bold">SecOps AI</div>
              <div className="text-violet-300 text-xs">Platform Console</div>
            </div>
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-2xl">
            <h1 className="font-bold text-lg mb-1">Platform Admin</h1>
            <p className="text-xs text-slate-400 mb-5">Super-admin access — manage all tenants</p>
            <form onSubmit={login} className="space-y-3">
              <input className="input" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} />
              <input className="input" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
              {err && <p className="text-red-500 text-sm">{err}</p>}
              <button className="btn btn-primary w-full bg-violet-600 hover:bg-violet-700">Sign in</button>
            </form>
            <p className="text-xs text-slate-300 mt-4 text-center">super@secops.ai / superpassword</p>
          </div>
        </div>
      </div>
    );
  }

  // ── Console ──
  const fmt = (n: number) => '$' + (n||0).toLocaleString();

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-violet-500 rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-bold text-sm">Platform Console</div>
              <div className="text-violet-300 text-xs">SecOps AI — all tenants</div>
            </div>
          </div>
          <button onClick={logout} className="text-sm text-slate-300 hover:text-white">Sign out</button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {msg && <div className="mb-4 px-4 py-2 bg-violet-50 border border-violet-200 rounded-lg text-sm text-violet-800">{msg}</div>}

        {/* Metrics */}
        {overview && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard icon={<DollarSign className="w-5 h-5"/>} label="Monthly Recurring Revenue" value={fmt(overview.total_mrr)} sub={`ARR ${fmt(overview.arr)}`} color="text-emerald-600" />
            <MetricCard icon={<Building2 className="w-5 h-5"/>} label="Total Tenants" value={overview.total_tenants} sub={`${overview.active} active · ${overview.trial} trial`} color="text-blue-600" />
            <MetricCard icon={<Users className="w-5 h-5"/>} label="Total Users" value={overview.total_users} sub={`${overview.total_connectors} connectors`} color="text-violet-600" />
            <MetricCard icon={<TrendingUp className="w-5 h-5"/>} label="AI Credits Consumed" value={overview.ai_credits_consumed} sub={`${overview.total_tickets} tickets total`} color="text-amber-600" />
          </div>
        )}

        {/* Plan distribution */}
        {overview && (
          <div className="card p-5 mb-6">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">Plan Distribution</h2>
            <div className="flex gap-6">
              {Object.entries(overview.plan_distribution).map(([plan, count]: any) => (
                <div key={plan} className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${plan==='enterprise'?'bg-violet-500':plan==='professional'?'bg-blue-500':'bg-slate-400'}`} />
                  <span className="text-sm capitalize text-slate-600">{plan}</span>
                  <span className="text-sm font-bold">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tenants table */}
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="font-semibold text-slate-800">Tenants</h2>
            <button onClick={()=>setShowOnboard(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium rounded-lg">
              <Plus className="w-4 h-4" /> Add tenant
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="text-left px-5 py-3">Organization</th>
                  <th className="text-left px-3 py-3">Plan</th>
                  <th className="text-left px-3 py-3">MRR</th>
                  <th className="text-left px-3 py-3">Status</th>
                  <th className="text-left px-3 py-3">Usage</th>
                  <th className="text-right px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {tenants.map(t => (
                  <tr key={t.id} className="hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-800">{t.name}</div>
                      <div className="text-xs text-slate-400 capitalize">{t.industry} · {t.active_framework?.replace('_',' ').toUpperCase()}</div>
                    </td>
                    <td className="px-3 py-3">
                      <select value={t.plan} onChange={e=>changePlan(t.id, e.target.value)}
                        className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white">
                        <option value="starter">Starter</option>
                        <option value="professional">Professional</option>
                        <option value="enterprise">Enterprise</option>
                      </select>
                    </td>
                    <td className="px-3 py-3 font-medium text-emerald-600">{fmt(t.mrr)}</td>
                    <td className="px-3 py-3">
                      <select value={t.status} onChange={e=>changeStatus(t.id, e.target.value)}
                        className={`text-xs border rounded-lg px-2 py-1 ${t.status==='active'?'bg-emerald-50 text-emerald-700 border-emerald-200':t.status==='trial'?'bg-blue-50 text-blue-700 border-blue-200':t.status==='suspended'?'bg-red-50 text-red-700 border-red-200':'bg-slate-50 text-slate-500 border-slate-200'}`}>
                        <option value="active">Active</option>
                        <option value="trial">Trial</option>
                        <option value="suspended">Suspended</option>
                        <option value="churned">Churned</option>
                      </select>
                    </td>
                    <td className="px-3 py-3 text-xs text-slate-500">
                      {t.users}u · {t.connectors}c · {t.events}e
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex gap-1 justify-end">
                        <button onClick={()=>impersonate(t.id, t.name)} title="Impersonate for support"
                          className="btn text-xs py-1 px-2 text-blue-600"><LogIn className="w-3.5 h-3.5"/></button>
                        <button onClick={()=>removeTenant(t.id, t.name)} title="Delete tenant"
                          className="btn text-xs py-1 px-2 text-red-500"><Trash2 className="w-3.5 h-3.5"/></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2 text-xs text-slate-400">
          <AlertTriangle className="w-3.5 h-3.5" />
          Impersonation issues a support session into the tenant and is logged in their audit trail.
        </div>

        {/* Internal team management */}
        <div className="card overflow-hidden mt-6">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <UserCog className="w-5 h-5 text-violet-500" />
              <h2 className="font-semibold text-slate-800">Internal Team</h2>
            </div>
            {['super_admin','admin'].includes(myRole) && (
              <button onClick={()=>setShowTeam(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium rounded-lg">
                <Plus className="w-4 h-4" /> Add team member
              </button>
            )}
          </div>
          <div className="divide-y divide-slate-50">
            {team.length === 0 ? (
              <div className="px-5 py-6 text-sm text-slate-400">No team members loaded.</div>
            ) : team.map(m => (
              <div key={m.id} className="px-5 py-3 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-violet-500 flex items-center justify-center text-white font-bold text-sm">
                  {m.name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800">{m.name}</p>
                  <p className="text-xs text-slate-400">{m.email}</p>
                </div>
                {['super_admin','admin'].includes(myRole) ? (
                  <select value={m.role} onChange={e=>changeTeamRole(m.id, e.target.value)}
                    className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white">
                    {PLATFORM_ROLES.map(r => <option key={r.key} value={r.key}>{r.label}</option>)}
                  </select>
                ) : (
                  <span className="text-xs px-2 py-1 bg-slate-100 text-slate-600 rounded-lg">{m.role}</span>
                )}
                {['super_admin','admin'].includes(myRole) && (
                  <button onClick={()=>removeTeamMember(m.id, m.name)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4"/></button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {showOnboard && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={()=>setShowOnboard(false)}>
          <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={e=>e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white">
              <h2 className="font-bold text-slate-800">Onboard a new client</h2>
              <button onClick={()=>setShowOnboard(false)} className="text-slate-400 hover:text-slate-600"><X className="w-5 h-5"/></button>
            </div>
            <form onSubmit={onboard} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Client organization name *</label>
                <input className="input" required value={onb.name} onChange={e=>setOnb({...onb,name:e.target.value})} placeholder="Acme Corp" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Industry</label>
                  <input className="input" value={onb.industry} onChange={e=>setOnb({...onb,industry:e.target.value})} placeholder="technology" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Primary framework</label>
                  <select className="select" value={onb.active_framework} onChange={e=>setOnb({...onb,active_framework:e.target.value})}>
                    <option value="soc2">SOC 2</option><option value="iso27001">ISO 27001</option>
                    <option value="pci_dss">PCI DSS</option><option value="hipaa">HIPAA</option>
                    <option value="nist_csf">NIST CSF</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Plan</label>
                <select className="select" value={onb.plan} onChange={e=>setOnb({...onb,plan:e.target.value})}>
                  <option value="starter">Starter</option><option value="professional">Professional</option><option value="enterprise">Enterprise</option>
                </select>
              </div>
              <div className="border-t border-slate-100 pt-4">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">First admin user</p>
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">Admin name *</label>
                      <input className="input" required value={onb.admin_name} onChange={e=>setOnb({...onb,admin_name:e.target.value})} placeholder="Jane Doe" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">Admin email *</label>
                      <input className="input" type="email" required value={onb.admin_email} onChange={e=>setOnb({...onb,admin_email:e.target.value})} placeholder="jane@acme.com" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Temporary password *</label>
                    <input className="input" required value={onb.admin_password} onChange={e=>setOnb({...onb,admin_password:e.target.value})} placeholder="They'll use this to first log in" />
                  </div>
                </div>
              </div>
              {onbErr && <p className="text-red-500 text-sm">{onbErr}</p>}
              <div className="flex gap-2 justify-end pt-2">
                <button type="button" onClick={()=>setShowOnboard(false)} className="btn">Cancel</button>
                <button type="submit" className="btn btn-primary bg-violet-600 hover:bg-violet-700">Onboard client</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showTeam && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={()=>setShowTeam(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md" onClick={e=>e.stopPropagation()}>
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="font-bold text-slate-800">Add internal team member</h2>
              <button onClick={()=>setShowTeam(false)}><X className="w-5 h-5 text-slate-400"/></button>
            </div>
            <form onSubmit={addTeamMember} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Name *</label>
                  <input className="input" required value={tm.name} onChange={e=>setTm({...tm,name:e.target.value})} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Email *</label>
                  <input className="input" type="email" required value={tm.email} onChange={e=>setTm({...tm,email:e.target.value})} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Temporary password *</label>
                <input className="input" required value={tm.password} onChange={e=>setTm({...tm,password:e.target.value})} placeholder="They change it on first login" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
                <select className="select" value={tm.role} onChange={e=>setTm({...tm,role:e.target.value})}>
                  {PLATFORM_ROLES.map(r => <option key={r.key} value={r.key}>{r.label} — {r.desc}</option>)}
                </select>
                {tm.role === 'super_admin' && myRole !== 'super_admin' && (
                  <p className="text-[10px] text-red-500 mt-1">Only a super-admin can create another super-admin.</p>
                )}
              </div>
              {tmErr && <p className="text-red-500 text-sm">{tmErr}</p>}
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={()=>setShowTeam(false)} className="btn">Cancel</button>
                <button type="submit" className="btn btn-primary bg-violet-600 hover:bg-violet-700">Add member</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ icon, label, value, sub, color }: any) {
  return (
    <div className="card p-4">
      <div className={`${color} mb-2`}>{icon}</div>
      <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-slate-800">{value}</p>
      <p className="text-xs text-slate-400 mt-0.5">{sub}</p>
    </div>
  );
}
