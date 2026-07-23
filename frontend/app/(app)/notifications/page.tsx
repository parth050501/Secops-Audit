'use client';
import { useEffect, useState } from 'react';
import { getMyNotifPrefs, setMyNotifPrefs, getNotifDefaults, setNotifDefault } from '@/lib/api';
import { Bell, Shield, User as UserIcon, Check } from 'lucide-react';

const TYPE_LABELS: Record<string, string> = {
  report_ciso: 'Executive / CISO report',
  report_engineer: 'Engineering report',
  report_auditor: 'Auditor / evidence report',
  ticket_assigned: 'Ticket assigned to me',
  ticket_status: 'Ticket status changes',
  finding_critical: 'New critical / high finding',
};
const TYPE_GROUPS = [
  { label: 'Reports', types: ['report_ciso', 'report_engineer', 'report_auditor'] },
  { label: 'Activity', types: ['ticket_assigned', 'ticket_status', 'finding_critical'] },
];
const ROLES = ['admin', 'manager', 'engineer', 'auditor'];

function Toggle({ on, onChange, disabled }: { on: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button onClick={onChange} disabled={disabled}
      className={`w-9 h-5 rounded-full transition-colors relative flex-shrink-0 ${on ? 'bg-teal-500' : 'bg-slate-200'} ${disabled ? 'opacity-40' : ''}`}>
      <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all ${on ? 'left-4' : 'left-0.5'}`} />
    </button>
  );
}

export default function NotificationsPage() {
  const [role, setRole] = useState('');
  const [myPrefs, setMyPrefs] = useState<any>(null);
  const [source, setSource] = useState('');
  const [defaults, setDefaults] = useState<any>(null);
  const [msg, setMsg] = useState('');
  const isAdmin = role === 'admin';

  useEffect(() => {
    try { setRole(JSON.parse(localStorage.getItem('user') || '{}').role || ''); } catch {}
    getMyNotifPrefs().then(r => { setMyPrefs(r.data.prefs); setSource(r.data.source); }).catch(() => {});
  }, []);
  useEffect(() => {
    if (isAdmin) getNotifDefaults().then(r => setDefaults(r.data.defaults)).catch(() => {});
  }, [isAdmin]);

  const toggleMine = async (type: string) => {
    const next = { ...myPrefs, [type]: !myPrefs[type] };
    setMyPrefs(next); setSource('custom');
    try { await setMyNotifPrefs({ custom: true, [type]: next[type] }); setMsg('Your preferences saved.'); }
    catch { setMsg('Could not save'); }
  };

  const resetMine = async () => {
    try { await setMyNotifPrefs({ custom: false }); setMsg('Reverted to your role default.');
      const r = await getMyNotifPrefs(); setMyPrefs(r.data.prefs); setSource(r.data.source); }
    catch { setMsg('Could not reset'); }
  };

  const toggleDefault = async (r: string, type: string) => {
    const next = { ...defaults, [r]: { ...defaults[r], [type]: !defaults[r][type] } };
    setDefaults(next);
    try { await setNotifDefault(r, { [type]: next[r][type] }); setMsg(`Default for ${r} updated.`); }
    catch { setMsg('Could not save default'); }
  };

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-3xl mx-auto">
        <div className="mb-5">
          <h1 className="text-xl font-bold flex items-center gap-2"><Bell className="w-5 h-5 text-teal-600" /> Notifications</h1>
          <p className="text-sm text-slate-400">Choose what you receive by email. {isAdmin && 'As an admin, you also set the defaults for each role.'}</p>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-100 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* My preferences */}
        <div className="card p-5 mb-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <UserIcon className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-800">My preferences</h2>
              <span className={`text-[10px] px-2 py-0.5 rounded-full ${source === 'custom' ? 'bg-violet-50 text-violet-600' : 'bg-slate-100 text-slate-500'}`}>
                {source === 'custom' ? 'Custom' : 'Using role default'}
              </span>
            </div>
            {source === 'custom' && <button onClick={resetMine} className="text-xs text-slate-400 hover:text-slate-600 underline">Reset to role default</button>}
          </div>
          {myPrefs && TYPE_GROUPS.map(g => (
            <div key={g.label} className="mb-3 last:mb-0">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">{g.label}</div>
              <div className="space-y-2">
                {g.types.map(t => (
                  <div key={t} className="flex items-center justify-between py-1">
                    <span className="text-sm text-slate-700">{TYPE_LABELS[t]}</span>
                    <Toggle on={!!myPrefs[t]} onChange={() => toggleMine(t)} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Admin: role defaults */}
        {isAdmin && defaults && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-800">Role defaults (tenant-wide)</h2>
            </div>
            <p className="text-xs text-slate-400 mb-4">What each role receives by default. Individual users can override their own — your defaults apply to anyone who hasn't customized.</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-400 border-b border-slate-100">
                    <th className="text-left font-medium py-2 pr-2">Notification</th>
                    {ROLES.map(r => <th key={r} className="text-center font-medium py-2 px-2 capitalize">{r}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {TYPE_GROUPS.map(g => (
                    <>
                      <tr key={g.label}><td colSpan={5} className="pt-3 pb-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wide">{g.label}</td></tr>
                      {g.types.map(t => (
                        <tr key={t} className="border-b border-slate-50">
                          <td className="py-2 pr-2 text-slate-700">{TYPE_LABELS[t]}</td>
                          {ROLES.map(r => (
                            <td key={r} className="text-center py-2 px-2">
                              <div className="flex justify-center"><Toggle on={!!defaults[r]?.[t]} onChange={() => toggleDefault(r, t)} /></div>
                            </td>
                          ))}
                        </tr>
                      ))}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        <p className="text-[11px] text-slate-400 mt-4 text-center">Email delivery uses your platform's configured sender. Scheduled report delivery is wired next.</p>
      </div>
    </div>
  );
}
