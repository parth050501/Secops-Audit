'use client';
import { useEffect, useState } from 'react';
import { getMyTenant, getFrameworks, updateTenant, getAIUsage } from '@/lib/api';

const FW_COLORS: any = { pci_dss:'#1a56db',hipaa:'#057a55',sox:'#9f580a',iso27001:'#5521b5',nist_csf:'#1f2937',hitrust:'#c81e1e' };

export default function SettingsPage() {
  const [tenant, setTenant] = useState<any>(null);
  const [frameworks, setFrameworks] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [jiraUrl, setJiraUrl] = useState('');
  const [jiraToken, setJiraToken] = useState('');
  const [snowUrl, setSnowUrl] = useState('');
  const [snowToken, setSnowToken] = useState('');
  const [usage, setUsage] = useState<any[]>([]);

  useEffect(() => {
    getMyTenant().then(t => setTenant(t.data)).catch(e => console.error('tenant fetch failed', e));
    getFrameworks().then(f => setFrameworks(f.data)).catch(e => console.error('frameworks fetch failed', e));
    getAIUsage().then(r => setUsage(r.data)).catch(()=>{});
  }, []);

  const switchFramework = async (fw: string) => {
    setSaving(true);
    try {
      const r = await updateTenant({ active_framework: fw });
      setTenant(r.data); setMsg(`Switched to ${fw.toUpperCase().replace('_',' ')}`);
    } finally { setSaving(false); }
  };

  // Toggle a framework in/out of the tenant's selected set
  const toggleFramework = async (fw: string) => {
    const current: string[] = tenant.frameworks || [];
    const isSelected = current.includes(fw);
    let next: string[];
    if (isSelected) {
      // don't allow removing the last framework
      if (current.length <= 1) { setMsg('At least one framework must be selected.'); return; }
      next = current.filter(f => f !== fw);
    } else {
      next = [...current, fw];
    }
    setSaving(true);
    try {
      // if we removed the active framework, move active to the first remaining
      const payload: any = { frameworks: next };
      if (isSelected && tenant.active_framework === fw) {
        payload.active_framework = next[0];
      }
      const r = await updateTenant(payload);
      setTenant(r.data);
      setMsg(isSelected ? `Removed ${fw.toUpperCase().replace('_',' ')}` : `Added ${fw.toUpperCase().replace('_',' ')}`);
    } finally { setSaving(false); }
  };

  const saveIntegrations = async () => {
    setSaving(true);
    try {
      await updateTenant({ jira_url: jiraUrl||undefined, jira_token: jiraToken||undefined,
                            servicenow_url: snowUrl||undefined, servicenow_token: snowToken||undefined });
      setMsg('Integrations saved.');
    } finally { setSaving(false); }
  };

  if (!tenant) return <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading…</div>;

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-3xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-bold">Settings</h1>
          <p className="text-sm text-slate-400">{tenant.name} · {tenant.industry}</p>
        </div>

        {msg && <div className="mb-4 px-4 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-800">{msg}</div>}

        {/* Compliance Frameworks — choose which apply */}
        <div className="card p-6 mb-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-1">Compliance Frameworks</h2>
          <p className="text-xs text-slate-400 mb-4">Select every framework your organization is assessed against. Findings, governance, and tickets will be mapped and labeled for each selected framework. You can choose one or many.</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.keys(frameworks).map((fw: string) => {
              const meta = frameworks[fw];
              const selected = tenant.frameworks?.includes(fw);
              return (
                <button key={fw} onClick={() => toggleFramework(fw)} disabled={saving}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${selected?'border-teal-400 bg-teal-50':'border-slate-100 hover:border-slate-300 opacity-70'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-2.5 h-2.5 rounded-full" style={{background: FW_COLORS[fw]||'#666'}} />
                    {selected
                      ? <span className="text-[10px] bg-teal-500 text-white px-1.5 py-0.5 rounded-full font-medium">SELECTED</span>
                      : <span className="text-[10px] bg-slate-200 text-slate-500 px-1.5 py-0.5 rounded-full font-medium">OFF</span>}
                  </div>
                  <p className="text-sm font-bold text-slate-800">{meta?.short || fw}</p>
                  <p className="text-xs text-slate-400 line-clamp-2">{meta?.description}</p>
                </button>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-400 mt-3">At least one framework must remain selected. The active framework below is the default view; selecting multiple lets you see findings across all of them.</p>
        </div>

        {/* Active framework */}
        <div className="card p-6 mb-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-1">Active Framework</h2>
          <p className="text-xs text-slate-400 mb-4">Switching framework reconfigures dashboards, controls, and ticket mappings instantly.</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {tenant.frameworks?.map((fw: string) => {
              const meta = frameworks[fw];
              const isActive = tenant.active_framework === fw;
              return (
                <button key={fw} onClick={() => switchFramework(fw)} disabled={saving || isActive}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${isActive?'border-teal-400 bg-teal-50':'border-slate-100 hover:border-slate-300'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-2.5 h-2.5 rounded-full" style={{background: FW_COLORS[fw]||'#666'}} />
                    {isActive && <span className="text-[10px] bg-teal-500 text-white px-1.5 py-0.5 rounded-full font-medium">ACTIVE</span>}
                  </div>
                  <p className="text-sm font-bold text-slate-800">{meta?.short || fw}</p>
                  <p className="text-xs text-slate-400 line-clamp-2">{meta?.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Monitoring */}
        <div className="card p-6 mb-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Monitoring Mode</h2>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
            <span className="text-sm font-medium text-teal-700">Real-time + Scheduled</span>
            <span className="text-xs text-slate-400">Events stream in live · Daily full scan</span>
          </div>
        </div>

        {/* Integrations */}
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-1">External Integrations</h2>
          <p className="text-xs text-slate-400 mb-4">Tickets will be auto-pushed to these systems when created.</p>
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Jira</p>
              <div className="grid grid-cols-2 gap-2">
                <input className="input text-sm" placeholder="https://company.atlassian.net" value={jiraUrl} onChange={e=>setJiraUrl(e.target.value)} />
                <input className="input text-sm" type="password" placeholder="API token" value={jiraToken} onChange={e=>setJiraToken(e.target.value)} />
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">ServiceNow</p>
              <div className="grid grid-cols-2 gap-2">
                <input className="input text-sm" placeholder="https://instance.service-now.com" value={snowUrl} onChange={e=>setSnowUrl(e.target.value)} />
                <input className="input text-sm" type="password" placeholder="Token" value={snowToken} onChange={e=>setSnowToken(e.target.value)} />
              </div>
            </div>
            <button onClick={saveIntegrations} disabled={saving} className="btn btn-primary">
              {saving ? 'Saving…' : 'Save integrations'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
