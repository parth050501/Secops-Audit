'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getTicket, updateTicket, enhanceTicketAI, addTicketComment, uploadTicketEvidence } from '@/lib/api';
import {
  ArrowLeft, CheckCircle, XCircle, Clock, User, ChevronRight,
  AlertTriangle, FileText, Zap, RotateCcw, ShieldOff, MessageSquare, Paperclip, Upload
} from 'lucide-react';

const TRANSITIONS: any = {
  open:      [{ to:'assigned', label:'Assign to me', icon:'User', color:'btn-primary' },
              { to:'suppressed', label:'Suppress', icon:'ShieldOff', color:'btn' }],
  assigned:  [{ to:'in_review', label:'Submit for Review', icon:'ChevronRight', color:'btn-primary' },
              { to:'open',      label:'Unassign', icon:'RotateCcw', color:'btn' }],
  in_review: [{ to:'accepted', label:'Accept & Approve', icon:'CheckCircle', color:'btn-primary' },
              { to:'rejected', label:'Reject', icon:'XCircle', color:'btn-danger' }],
  accepted:  [{ to:'remediated', label:'Mark Remediated', icon:'CheckCircle', color:'btn-primary' }],
  rejected:  [{ to:'open', label:'Re-open', icon:'RotateCcw', color:'btn' }],
};

const ICON_MAP: any = {
  User: User, ChevronRight: ChevronRight, CheckCircle, XCircle, RotateCcw, ShieldOff,
};

const FLOW = ['open','assigned','in_review','accepted','remediated'];

const SEV_COLOR: any = {
  critical: 'text-red-600 bg-red-50 border-red-200',
  high:     'text-orange-600 bg-orange-50 border-orange-200',
  medium:   'text-yellow-600 bg-yellow-50 border-yellow-200',
  low:      'text-green-600 bg-green-50 border-green-200',
};

export default function TicketDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [ticket, setTicket] = useState<any>(null);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [msg, setMsg] = useState('');
  const [showNotes, setShowNotes] = useState(false);
  const [pendingStatus, setPendingStatus] = useState('');
  const [enhancing, setEnhancing] = useState(false);
  const [comment, setComment] = useState('');
  const [postingComment, setPostingComment] = useState(false);
  const [evidenceNote, setEvidenceNote] = useState('');
  const [uploading, setUploading] = useState(false);

  const postComment = async () => {
    const text = comment.trim();
    if (!text) return;
    setPostingComment(true);
    try {
      await addTicketComment(Number(id), text);
      setComment('');
      load();
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Could not add comment');
    } finally { setPostingComment(false); }
  };

  const uploadEvidence = async (file: File) => {
    if (!file) return;
    setUploading(true); setMsg('');
    try {
      await uploadTicketEvidence(Number(id), file, evidenceNote);
      setEvidenceNote('');
      setMsg('Evidence uploaded.');
      load();
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Upload failed');
    } finally { setUploading(false); }
  };

  const load = async () => {
    try {
      const r = await getTicket(Number(id));
      setTicket(r.data);
    } catch { router.push('/tickets'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const enhanceAI = async () => {
    setEnhancing(true); setMsg('');
    try {
      const r = await enhanceTicketAI(Number(id));
      setMsg('AI enhancement applied.');
      load();
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Enhancement failed');
    } finally { setEnhancing(false); }
  };

  const act = async (toStatus: string) => {
    // If rejecting or remediating, prompt for notes
    if ((toStatus === 'rejected' || toStatus === 'remediated') && !showNotes) {
      setPendingStatus(toStatus);
      setShowNotes(true);
      return;
    }
    setActing(true);
    setMsg('');
    try {
      await updateTicket(Number(id), { status: toStatus, notes: notes || undefined });
      setMsg(`Status updated to: ${toStatus.replace('_', ' ')}`);
      setShowNotes(false); setNotes(''); setPendingStatus('');
      load();
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Action failed');
    } finally { setActing(false); }
  };

  if (loading) return (
    <div className="h-screen flex items-center justify-center text-slate-400 text-sm">Loading ticket…</div>
  );
  if (!ticket) return null;

  const transitions = TRANSITIONS[ticket.status] || [];
  const flowIdx = FLOW.indexOf(ticket.status);

  return (
    <div className="h-screen overflow-y-auto bg-slate-50">
      <div className="p-6 max-w-5xl mx-auto">

        {/* Back */}
        <button onClick={() => router.push('/tickets')}
          className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 mb-5 transition-colors">
          <ArrowLeft className="w-4 h-4" /> All tickets
        </button>

        {msg && (
          <div className="mb-4 px-4 py-2.5 bg-teal-50 border border-teal-200 rounded-xl text-sm text-teal-800">
            {msg}
          </div>
        )}

        {/* Header card */}
        <div className="card p-6 mb-4">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <span className="text-xs font-mono font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                  {ticket.ref}
                </span>
                <span className={`badge badge-${ticket.severity}`}>{ticket.severity}</span>
                <span className={`badge badge-${ticket.status}`}>{ticket.status.replace('_',' ')}</span>
                {ticket.framework && (
                  <span className="text-xs font-medium text-slate-500 uppercase bg-slate-100 px-2 py-0.5 rounded">
                    {ticket.framework.replace('_',' ')}
                  </span>
                )}
              </div>
              <h1 className="text-lg font-bold text-slate-900">{ticket.title}</h1>
            </div>

            {/* Action buttons */}
            <div className="flex flex-col items-end gap-2 flex-shrink-0">
            <button onClick={enhanceAI} disabled={enhancing}
              className="btn text-xs bg-gradient-to-r from-violet-50 to-teal-50 border-violet-200 text-violet-700 hover:from-violet-100">
              <Zap className="w-3.5 h-3.5" />
              {enhancing ? 'Enhancing…' : 'Enhance with AI'}
            </button>
            {transitions.length > 0 && (
              <div className="flex gap-2 flex-wrap justify-end">
                {transitions.map((tr: any) => {
                  const Icon = ICON_MAP[tr.icon] || ChevronRight;
                  return (
                    <button key={tr.to} onClick={() => act(tr.to)} disabled={acting}
                      className={`btn ${tr.color} text-sm`}>
                      <Icon className="w-4 h-4" />
                      {acting ? 'Please wait…' : tr.label}
                    </button>
                  );
                })}
              </div>
            )}
            </div>
          </div>

          {/* HITL Progress flow */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1">
            {FLOW.map((step, i) => {
              const done = flowIdx > i;
              const active = flowIdx === i;
              const rejected = ticket.status === 'rejected' && step === 'in_review';
              return (
                <div key={step} className="flex items-center gap-1 flex-shrink-0">
                  <div className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    rejected && step === 'in_review' ? 'bg-red-100 text-red-600' :
                    done   ? 'bg-emerald-100 text-emerald-700' :
                    active ? 'bg-slate-900 text-teal-400' :
                    'bg-slate-100 text-slate-400'
                  }`}>
                    {done && <CheckCircle className="w-3 h-3" />}
                    {rejected && step === 'in_review' && <XCircle className="w-3 h-3" />}
                    <span className="capitalize">{step.replace('_',' ')}</span>
                  </div>
                  {i < FLOW.length - 1 && (
                    <ChevronRight className={`w-3.5 h-3.5 flex-shrink-0 ${done ? 'text-emerald-400' : 'text-slate-200'}`} />
                  )}
                </div>
              );
            })}
            {ticket.status === 'rejected' && (
              <div className="flex items-center gap-1 flex-shrink-0">
                <ChevronRight className="w-3.5 h-3.5 text-slate-200" />
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-red-100 text-red-600">
                  <XCircle className="w-3 h-3" /> Rejected
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Notes prompt */}
        {showNotes && (
          <div className="card p-5 mb-4 border-2 border-teal-200">
            <p className="text-sm font-semibold text-slate-800 mb-2">
              {pendingStatus === 'rejected' ? 'Reason for rejection' : 'Resolution notes'}
              <span className="text-slate-400 font-normal ml-1">(optional)</span>
            </p>
            <textarea
              className="input h-24 resize-none mb-3"
              placeholder={pendingStatus === 'rejected'
                ? 'Explain why this ticket is being rejected…'
                : 'Describe what was done to remediate this finding…'}
              value={notes}
              onChange={e => setNotes(e.target.value)}
            />
            <div className="flex gap-2">
              <button onClick={() => act(pendingStatus)} disabled={acting}
                className={`btn ${pendingStatus === 'rejected' ? 'btn-danger' : 'btn-primary'}`}>
                {acting ? 'Saving…' : `Confirm ${pendingStatus.replace('_',' ')}`}
              </button>
              <button onClick={() => { setShowNotes(false); setPendingStatus(''); }} className="btn">
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-4">

            {/* Description */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-3">
                <FileText className="w-4 h-4 text-slate-400" />
                <h2 className="text-sm font-semibold text-slate-700">Description</h2>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed">{ticket.description || 'No description.'}</p>
            </div>

            {/* AI Recommendation */}
            {(ticket.ai_recommendation || ticket.remediation_steps) && (
              <div className="card p-5 border-teal-100 bg-gradient-to-br from-teal-50/50 to-white">
                <div className="flex items-center gap-2 mb-3">
                  <Zap className="w-4 h-4 text-teal-600" />
                  <h2 className="text-sm font-semibold text-teal-700">AI Recommendation</h2>
                </div>
                {ticket.ai_recommendation && (
                  <p className="text-sm text-slate-700 mb-3 leading-relaxed">{ticket.ai_recommendation}</p>
                )}
                {ticket.remediation_steps && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Remediation Steps</p>
                    <div className="space-y-1.5">
                      {ticket.remediation_steps.split('\n').filter(Boolean).map((step: string, i: number) => (
                        <div key={i} className="flex items-start gap-2.5 text-sm">
                          <div className="w-5 h-5 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                            {i + 1}
                          </div>
                          <span className="text-slate-700">{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Resolution / Rejection notes */}
            {ticket.resolution_notes && (
              <div className="card p-5 bg-emerald-50 border-emerald-200">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  <h2 className="text-sm font-semibold text-emerald-700">Resolution Notes</h2>
                </div>
                <p className="text-sm text-slate-700">{ticket.resolution_notes}</p>
              </div>
            )}
            {ticket.rejection_reason && (
              <div className="card p-5 bg-red-50 border-red-200">
                <div className="flex items-center gap-2 mb-2">
                  <XCircle className="w-4 h-4 text-red-600" />
                  <h2 className="text-sm font-semibold text-red-700">Rejection Reason</h2>
                </div>
                <p className="text-sm text-slate-700">{ticket.rejection_reason}</p>
              </div>
            )}

            {/* Audit trail */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-slate-400" />
                <h2 className="text-sm font-semibold text-slate-700">Audit Trail</h2>
              </div>
              {!ticket.history?.length ? (
                <p className="text-xs text-slate-400">No history yet.</p>
              ) : (
                <div className="space-y-3">
                  {[...ticket.history].reverse().map((h: any, i: number) => (
                    <div key={i} className="flex gap-3">
                      <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500 flex-shrink-0">
                        {h.user?.charAt(0) || 'S'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2 flex-wrap">
                          <span className="text-xs font-semibold text-slate-700">{h.user}</span>
                          <span className="text-xs text-slate-400 font-medium">{h.action}</span>
                          <span className="text-xs text-slate-300">{new Date(h.timestamp).toLocaleString()}</span>
                        </div>
                        {h.notes && <p className="text-xs text-slate-500 mt-0.5">{h.notes}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Work comments */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <MessageSquare className="w-4 h-4 text-slate-400" />
                <h2 className="text-sm font-semibold text-slate-700">Work Comments</h2>
              </div>
              {/* Add comment */}
              <div className="mb-4">
                <textarea
                  className="input h-20 resize-none mb-2"
                  placeholder="Add a comment about work done on this ticket…"
                  value={comment}
                  onChange={e => setComment(e.target.value)}
                />
                <button onClick={postComment} disabled={postingComment || !comment.trim()}
                  className="btn btn-primary text-sm">
                  {postingComment ? 'Posting…' : 'Add comment'}
                </button>
              </div>
              {/* Comment list */}
              {!ticket.comments?.length ? (
                <p className="text-xs text-slate-400">No comments yet.</p>
              ) : (
                <div className="space-y-3">
                  {[...ticket.comments].reverse().map((c: any, i: number) => (
                    <div key={i} className="flex gap-3">
                      <div className="w-7 h-7 rounded-full bg-teal-100 flex items-center justify-center text-xs font-bold text-teal-700 flex-shrink-0">
                        {c.user?.charAt(0) || 'U'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2 flex-wrap">
                          <span className="text-xs font-semibold text-slate-700">{c.user}</span>
                          <span className="text-xs text-slate-300">{new Date(c.timestamp).toLocaleString()}</span>
                        </div>
                        <p className="text-sm text-slate-600 mt-0.5 whitespace-pre-wrap">{c.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Evidence */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Paperclip className="w-4 h-4 text-slate-400" />
                <h2 className="text-sm font-semibold text-slate-700">Evidence</h2>
              </div>
              {/* Upload */}
              <div className="mb-4 p-4 border-2 border-dashed border-slate-200 rounded-xl">
                <input
                  type="text"
                  className="input mb-2 text-sm"
                  placeholder="Optional note about this evidence…"
                  value={evidenceNote}
                  onChange={e => setEvidenceNote(e.target.value)}
                />
                <label className={`btn text-sm cursor-pointer inline-flex ${uploading ? 'opacity-50' : ''}`}>
                  <Upload className="w-4 h-4" />
                  {uploading ? 'Uploading…' : 'Upload evidence file'}
                  <input type="file" className="hidden" disabled={uploading}
                    onChange={e => { const f = e.target.files?.[0]; if (f) uploadEvidence(f); e.currentTarget.value=''; }} />
                </label>
                <p className="text-[11px] text-slate-400 mt-2">PDF, images, Office docs, or text. Max 25 MB.</p>
              </div>
              {/* Evidence list */}
              {!ticket.evidence?.length ? (
                <p className="text-xs text-slate-400">No evidence attached yet.</p>
              ) : (
                <div className="space-y-2">
                  {[...ticket.evidence].reverse().map((ev: any, i: number) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                      <FileText className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-700 truncate">{ev.file_name}</p>
                        <div className="flex items-baseline gap-2 flex-wrap">
                          <span className="text-xs text-slate-400">{ev.user}</span>
                          <span className="text-xs text-slate-300">{new Date(ev.timestamp).toLocaleString()}</span>
                          {ev.file_size && <span className="text-xs text-slate-300">{(ev.file_size/1024).toFixed(0)} KB</span>}
                        </div>
                        {ev.note && <p className="text-xs text-slate-500 mt-1">{ev.note}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="space-y-4">

            {/* Details */}
            <div className="card p-5">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Details</h2>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-xs text-slate-400 mb-0.5">Severity</p>
                  <span className={`badge badge-${ticket.severity}`}>{ticket.severity}</span>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-0.5">Framework</p>
                  <p className="font-medium text-slate-700 uppercase">{ticket.framework?.replace('_',' ') || '—'}</p>
                </div>
                {ticket.control_ids?.length > 0 && (
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Controls</p>
                    <div className="flex flex-wrap gap-1">
                      {ticket.control_ids.map((c: string) => (
                        <span key={c} className="text-[10px] font-mono px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">{c}</span>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <p className="text-xs text-slate-400 mb-0.5">Category</p>
                  <p className="text-slate-700 capitalize">{ticket.category?.replace('_',' ') || '—'}</p>
                </div>
                {ticket.due_date && (
                  <div>
                    <p className="text-xs text-slate-400 mb-0.5">Due date</p>
                    <p className={`text-sm font-medium ${new Date(ticket.due_date) < new Date() ? 'text-red-600' : 'text-slate-700'}`}>
                      {new Date(ticket.due_date).toLocaleDateString()}
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-slate-400 mb-0.5">Created</p>
                  <p className="text-slate-700">{ticket.created_at ? new Date(ticket.created_at).toLocaleString() : '—'}</p>
                </div>
                {ticket.approved_by && (
                  <div>
                    <p className="text-xs text-slate-400 mb-0.5">Approved by</p>
                    <p className="text-slate-700 flex items-center gap-1">
                      <User className="w-3 h-3" /> User #{ticket.approved_by}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* External tickets */}
            {(ticket.jira_key || ticket.servicenow_number) && (
              <div className="card p-5">
                <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">External Tickets</h2>
                {ticket.jira_key && (
                  <div className="flex items-center gap-2 text-sm mb-2">
                    <span className="font-medium text-blue-600">Jira</span>
                    <span className="font-mono text-slate-600">{ticket.jira_key}</span>
                  </div>
                )}
                {ticket.servicenow_number && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium text-green-600">ServiceNow</span>
                    <span className="font-mono text-slate-600">{ticket.servicenow_number}</span>
                  </div>
                )}
              </div>
            )}

            {/* Quick actions if terminal state */}
            {['remediated','suppressed'].includes(ticket.status) && (
              <div className="card p-5 bg-slate-50">
                <div className="flex items-center gap-2 text-sm">
                  {ticket.status === 'remediated'
                    ? <CheckCircle className="w-5 h-5 text-emerald-500" />
                    : <ShieldOff className="w-5 h-5 text-slate-400" />}
                  <span className="font-medium text-slate-700 capitalize">{ticket.status}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {ticket.status === 'remediated'
                    ? 'This finding has been resolved and verified.'
                    : 'This finding has been suppressed from scoring.'}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
