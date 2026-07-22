'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { login } from '@/lib/api';
import { Shield } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true);
    try {
      const r = await login(email, password);
      localStorage.setItem('token', r.data.token);
      localStorage.setItem('user', JSON.stringify(r.data.user));
      router.push('/dashboard');
    } catch (err: any) { setError(err.response?.data?.detail || 'Login failed'); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-10 h-10 bg-teal-500 rounded-xl flex items-center justify-center">
            <Shield className="w-6 h-6 text-slate-900" />
          </div>
          <div>
            <div className="text-white font-bold text-lg">GRCBridge</div>
            <div className="text-slate-400 text-xs">Governance & Compliance</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-8 shadow-xl">
          <h1 className="text-lg font-semibold mb-1">Sign in</h1>
          <p className="text-sm text-slate-400 mb-6">Human-in-the-Loop Governance Platform</p>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Email</label>
              <input className="input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required suppressHydrationWarning />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Password</label>
              <input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} required suppressHydrationWarning />
            </div>
            {error && <p className="text-xs text-red-600">{error}</p>}
            <button type="submit" disabled={loading} className="w-full py-2.5 bg-slate-900 text-teal-400 font-semibold rounded-lg hover:bg-slate-800 disabled:opacity-50 transition-colors">
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
          {process.env.NEXT_PUBLIC_SHOW_DEMO === '1' && (
          <div className="mt-4 pt-4 border-t border-slate-100 space-y-1">
            <p className="text-xs text-slate-400 font-medium">Demo accounts:</p>
            {[['admin@secops.ai','Admin'],['engineer@secops.ai','Engineer'],['auditor@secops.ai','Auditor']].map(([e,r])=>(
              <button key={e} onClick={()=>{setEmail(e);setPassword('password');}}
                className="block text-xs text-teal-600 hover:underline">{r}: {e}</button>
            ))}
          </div>
          )}
        </div>
      </div>
    </div>
  );
}
