'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getFrameworks, getIndustryFrameworks, onboardTenant } from '@/lib/api';
import { Shield, Check } from 'lucide-react';

const INDUSTRIES = [
  { id:'financial',  label:'Financial Services', desc:'Banks, insurance, fintech', emoji:'🏦' },
  { id:'healthcare', label:'Healthcare',          desc:'Hospitals, clinics, pharma', emoji:'🏥' },
  { id:'retail',     label:'Retail',              desc:'E-commerce, POS, payments', emoji:'🛍️' },
  { id:'government', label:'Government',          desc:'Federal, state, municipal', emoji:'🏛️' },
  { id:'technology', label:'Technology',          desc:'SaaS, cloud, software', emoji:'💻' },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [industry, setIndustry] = useState('');
  const [frameworks, setFrameworks] = useState<any>({});
  const [industryFw, setIndustryFw] = useState<any>({});
  const [selected, setSelected] = useState<string[]>([]);
  const [primary, setPrimary] = useState('');
  const [orgName, setOrgName] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getFrameworks().then(r => setFrameworks(r.data)).catch(e => console.warn("frameworks load failed", e));
    getIndustryFrameworks().then(r => setIndustryFw(r.data)).catch(e => console.warn("industry frameworks load failed", e));
  }, []);

  const pickIndustry = (id: string) => {
    setIndustry(id);
    const recommended = industryFw[id] || [];
    setSelected(recommended);
    setPrimary(recommended[0] || '');
    setStep(2);
  };

  const toggleFw = (fw: string) => {
    setSelected(prev => prev.includes(fw) ? prev.filter(x=>x!==fw) : [...prev, fw]);
  };

  const submit = async () => {
    if (!orgName || !primary || !selected.length) return;
    setLoading(true);
    try {
      await onboardTenant({ name: orgName, industry, frameworks: selected, active_framework: primary, scan_schedule: 'realtime' });
      router.push('/dashboard');
    } catch (e) { setLoading(false); }
  };

  const FW_COLORS: any = { pci_dss:'#1a56db',hipaa:'#057a55',sox:'#9f580a',iso27001:'#5521b5',nist_csf:'#1f2937',hitrust:'#c81e1e' };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-10 h-10 bg-teal-500 rounded-xl flex items-center justify-center">
            <Shield className="w-6 h-6 text-slate-900" />
          </div>
          <div className="text-white">
            <div className="font-bold text-xl">GRCBridge</div>
            <div className="text-slate-400 text-sm">Let's configure your governance platform</div>
          </div>
        </div>

        {/* Steps */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1,2,3].map(s => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${step>=s?'bg-teal-500 text-slate-900':'bg-slate-700 text-slate-400'}`}>
                {step>s ? <Check className="w-4 h-4" /> : s}
              </div>
              {s<3 && <div className={`w-12 h-0.5 ${step>s?'bg-teal-500':'bg-slate-700'}`} />}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-2xl p-8 shadow-xl">
          {/* Step 1: Industry */}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-bold mb-1">What industry are you in?</h2>
              <p className="text-sm text-slate-400 mb-6">We'll pre-configure the relevant compliance frameworks for your industry.</p>
              <div className="grid grid-cols-1 gap-3">
                {INDUSTRIES.map(ind => (
                  <button key={ind.id} onClick={() => pickIndustry(ind.id)}
                    className="flex items-center gap-4 p-4 rounded-xl border-2 border-slate-100 hover:border-teal-400 hover:bg-teal-50 transition-all text-left">
                    <span className="text-2xl">{ind.emoji}</span>
                    <div>
                      <div className="font-semibold text-slate-800">{ind.label}</div>
                      <div className="text-sm text-slate-400">{ind.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Frameworks */}
          {step === 2 && (
            <div>
              <h2 className="text-xl font-bold mb-1">Select compliance frameworks</h2>
              <p className="text-sm text-slate-400 mb-6">We've recommended frameworks for your industry. You can add or remove any.</p>
              <div className="grid grid-cols-2 gap-3 mb-6">
                {Object.entries(frameworks).map(([key, fw]: any) => {
                  const isSelected = selected.includes(key);
                  const isPrimary = primary === key;
                  return (
                    <div key={key} onClick={() => toggleFw(key)}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${isSelected?'border-teal-400 bg-teal-50':'border-slate-100 hover:border-slate-200'}`}>
                      <div className="flex items-start justify-between mb-1">
                        <div className="w-3 h-3 rounded-full mt-0.5" style={{background:FW_COLORS[key]||'#666'}} />
                        {isSelected && (
                          <button onClick={e=>{e.stopPropagation();setPrimary(key);}}
                            className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${isPrimary?'bg-teal-500 text-white':'bg-slate-100 text-slate-500 hover:bg-teal-100'}`}>
                            {isPrimary?'PRIMARY':'Set primary'}
                          </button>
                        )}
                      </div>
                      <div className="font-semibold text-sm text-slate-800">{fw.short}</div>
                      <div className="text-xs text-slate-400 mt-0.5 line-clamp-2">{fw.description}</div>
                    </div>
                  );
                })}
              </div>
              <div className="flex gap-3">
                <button onClick={()=>setStep(1)} className="btn">← Back</button>
                <button onClick={()=>setStep(3)} disabled={!selected.length||!primary}
                  className="btn btn-primary flex-1 justify-center">Continue →</button>
              </div>
            </div>
          )}

          {/* Step 3: Org name */}
          {step === 3 && (
            <div>
              <h2 className="text-xl font-bold mb-1">Name your organization</h2>
              <p className="text-sm text-slate-400 mb-6">This will appear on reports and audit packages.</p>
              <input className="input text-lg py-3 mb-6" placeholder="Acme Financial Inc."
                value={orgName} onChange={e=>setOrgName(e.target.value)} />
              <div className="bg-slate-50 rounded-xl p-4 mb-6">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Your configuration</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">Industry</span><span className="font-medium capitalize">{industry}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Primary framework</span><span className="font-medium">{primary?.toUpperCase().replace('_',' ')}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">All frameworks</span><span className="font-medium">{selected.length} selected</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Monitoring</span><span className="font-medium text-teal-600">Real-time + Scheduled</span></div>
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={()=>setStep(2)} className="btn">← Back</button>
                <button onClick={submit} disabled={!orgName||loading}
                  className="btn btn-primary flex-1 justify-center">
                  {loading?'Setting up…':'Launch platform →'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
