'use client';
import { useEffect, useState } from 'react';
import { getTickets } from '@/lib/api';
import { ChevronRight, Clock } from 'lucide-react';

const STATUS_ORDER = ['open','assigned','in_review','accepted','rejected','remediated','suppressed'];

export default function TicketsPage() {
  const [tickets, setTickets] = useState<any[]>([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => { getTickets().then(r => setTickets(r.data)).catch(e => console.warn("tickets load failed", e)); }, []);

  const filtered = filter === 'all' ? tickets : tickets.filter(t => t.status === filter);
  const counts: any = {};
  tickets.forEach(t => { counts[t.status] = (counts[t.status]||0)+1; });

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-bold">Tickets</h1>
          <p className="text-sm text-slate-400">{tickets.length} total · {counts['open']||0} open</p>
        </div>

        {/* Status filter */}
        <div className="flex gap-2 flex-wrap mb-5">
          <button onClick={() => setFilter('all')}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium ${filter==='all'?'bg-slate-900 text-white':'bg-white border border-slate-200 text-slate-600'}`}>
            All ({tickets.length})
          </button>
          {STATUS_ORDER.filter(s => counts[s]).map(s => (
            <button key={s} onClick={() => setFilter(s)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium capitalize ${filter===s?'bg-slate-900 text-white':'bg-white border border-slate-200 text-slate-600'}`}>
              {s.replace('_',' ')} ({counts[s]||0})
            </button>
          ))}
        </div>

        <div className="card divide-y divide-slate-50">
          {!filtered.length && (
            <div className="px-5 py-10 text-center text-sm text-slate-400">
              No tickets. Create one from a governance event.
            </div>
          )}
          {filtered.map(t => (
            <a key={t.id} href={`/tickets/${t.id}`} className="px-5 py-4 flex items-center gap-3 hover:bg-slate-50 block">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-slate-400 flex-shrink-0">{t.ref}</span>
                  <span className={`badge badge-${t.severity} flex-shrink-0`}>{t.severity}</span>
                  <span className={`badge badge-${t.status} flex-shrink-0`}>{t.status.replace('_',' ')}</span>
                  {t.framework && <span className="text-xs text-slate-400 uppercase">{t.framework.replace('_',' ')}</span>}
                </div>
                <p className="text-sm font-medium text-slate-800 truncate">{t.title}</p>
                {t.control_ids?.length > 0 && (
                  <p className="text-xs text-slate-400 mt-0.5">Controls: {t.control_ids.join(', ')}</p>
                )}
              </div>
              {t.due_date && (
                <div className="flex items-center gap-1 text-xs text-slate-400 flex-shrink-0">
                  <Clock className="w-3 h-3" />
                  {new Date(t.due_date).toLocaleDateString()}
                </div>
              )}
              <ChevronRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
