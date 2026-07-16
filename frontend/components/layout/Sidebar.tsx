'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
<<<<<<< HEAD
import { Shield, LayoutDashboard, Plug, AlertTriangle, Ticket, FileCheck, Settings, LogOut, Radio, ClipboardList, ShieldCheck, Building2, FolderCheck, Users, Server, BadgeCheck, Cpu, ChevronLeft, ChevronRight, CalendarClock, Library, Boxes } from 'lucide-react';
=======
import { Shield, LayoutDashboard, Plug, AlertTriangle, Ticket, FileCheck, Settings, LogOut, Radio, ClipboardList, ShieldCheck, Building2, FolderCheck, Users, Server, BadgeCheck, Cpu, ChevronLeft, ChevronRight, CalendarClock, Library } from 'lucide-react';
>>>>>>> 8f526db18a4461ff76d81f7ca772f6b9a9d74df7
import clsx from 'clsx';

const FW_COLORS: any = {
  pci_dss:'#1a56db', hipaa:'#057a55', sox:'#9f580a',
  iso27001:'#5521b5', nist_csf:'#1f2937', hitrust:'#c81e1e',
};

const nav = [
  { label:'Dashboard',    href:'/dashboard',   icon: LayoutDashboard },
  { label:'Connectors',   href:'/connectors',  icon: Plug },
  { label:'Collectors',   href:'/collectors',  icon: Server },
<<<<<<< HEAD
  { label:'Inventory',    href:'/inventory',   icon: Boxes },
=======
  { label:'Agents',       href:'/agents',      icon: Cpu },
>>>>>>> 8f526db18a4461ff76d81f7ca772f6b9a9d74df7
  { label:'Scheduler',    href:'/scheduler',   icon: CalendarClock },
  { label:'Governance',   href:'/governance',  icon: AlertTriangle },
  { label:'Compliance',   href:'/compliance',  icon: BadgeCheck },
  { label:'Frameworks',   href:'/frameworks',  icon: Library },
  { label:'Policies',     href:'/policies',    icon: ClipboardList },
  { label:'SOC 2',        href:'/soc2',        icon: ShieldCheck },
  { label:'Evidence',     href:'/evidence',    icon: FolderCheck },
  { label:'Tickets',      href:'/tickets',     icon: Ticket },
  { label:'Auditor View', href:'/auditor',     icon: FileCheck },
  { label:'Team',         href:'/users',       icon: Users },
  { label:'Settings',     href:'/settings',    icon: Settings, roles:['admin'] },
];

export default function Sidebar({ tenant, liveCount }: { tenant: any; liveCount: number }) {
  const path = usePathname();
  const router = useRouter();
  const fw = tenant?.active_framework || 'pci_dss';
  const fwColor = FW_COLORS[fw] || '#1f2937';

  const [user, setUser] = useState<any>({});
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => {
    try { setUser(JSON.parse(localStorage.getItem('user') || '{}')); } catch {}
  }, []);

  return (
    <aside className={clsx(
      'flex-shrink-0 bg-slate-900 flex flex-col h-screen sticky top-0 transition-all duration-200',
      collapsed ? 'w-16' : 'w-56'
    )}>
      {/* Logo + collapse toggle */}
      <div className="px-4 py-5 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-teal-500 rounded-lg flex items-center justify-center flex-shrink-0">
            <Shield className="w-4 h-4 text-slate-900" />
          </div>
          {!collapsed && (
            <div>
              <div className="text-white text-sm font-bold">GRCBridge</div>
              <div className="text-slate-500 text-[10px]">Governance Platform</div>
            </div>
          )}
        </div>
        <button onClick={() => setCollapsed(c => !c)}
          className="text-slate-500 hover:text-slate-300 flex-shrink-0"
          title={collapsed ? 'Expand' : 'Collapse'}>
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Framework badge */}
      {tenant && !collapsed && (
        <div className="px-4 py-3 border-b border-white/10">
          <p className="text-[10px] text-slate-500 mb-1 uppercase tracking-wider">Active Framework</p>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{background: fwColor}} />
            <span className="text-xs font-semibold text-white truncate">
              {tenant.active_framework?.toUpperCase().replace('_',' ')}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5 capitalize">{tenant.industry}</p>
        </div>
      )}

      {/* Live indicator */}
      {liveCount > 0 && (
        <div className="mx-3 mt-3 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2">
          <Radio className="w-3.5 h-3.5 text-red-400 animate-pulse" />
          <span className="text-xs text-red-300 font-medium">{liveCount} live event{liveCount>1?'s':''}</span>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-0.5 overflow-y-auto">
        {nav.filter((item: any) => !item.roles || item.roles.includes(user?.role)).map(({ label, href, icon: Icon }) => (
          <Link key={href} href={href} title={collapsed ? label : undefined} className={clsx(
            'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
            collapsed && 'justify-center',
            path.startsWith(href)
              ? 'bg-white/10 text-teal-400 font-medium'
              : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
          )}>
            <Icon className="w-4 h-4 flex-shrink-0" />
            {!collapsed && label}
          </Link>
        ))}
      </nav>

      {/* User */}
      <div className="px-3 py-3 border-t border-white/10">
        <div className={clsx('flex items-center gap-2 mb-2', collapsed && 'justify-center')}>
          <div className="w-7 h-7 rounded-full bg-teal-500 flex items-center justify-center text-xs font-bold text-slate-900 flex-shrink-0">
            {user?.name?.charAt(0) || 'U'}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-white text-xs font-medium truncate">{user?.name}</div>
              <div className="text-slate-500 text-[10px] capitalize">{user?.role}</div>
            </div>
          )}
        </div>
        <button onClick={() => { localStorage.clear(); router.push('/login'); }}
          title={collapsed ? 'Sign out' : undefined}
          className={clsx('flex items-center gap-1.5 text-slate-500 hover:text-slate-300 text-xs transition-colors', collapsed && 'justify-center w-full')}>
          <LogOut className="w-3.5 h-3.5" /> {!collapsed && 'Sign out'}
        </button>
      </div>
    </aside>
  );
}
