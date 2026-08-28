import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getApplications, runApplyBatch, ApplicationItem, ApplyBatchSummary, getApplicationScreenshotUrl } from '../lib/api';
import { Send, Building2, Eye, Filter, AlertCircle, CheckCircle2, Clock, XCircle, Loader2, ArrowRight, X, ExternalLink } from 'lucide-react';

interface ApplicationsPageProps {
  resumeId: string | null;
}

export const ApplicationsPage: React.FC<ApplicationsPageProps> = ({ resumeId }) => {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [minScore, setMinScore] = useState<number>(0.5);
  const [batchLimit, setBatchLimit] = useState<number>(5);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [summary, setSummary] = useState<ApplyBatchSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedScreenshotUrl, setSelectedScreenshotUrl] = useState<string | null>(null);

  const fetchApplications = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getApplications({
        status: statusFilter === 'all' ? undefined : statusFilter,
        resume_id: resumeId || undefined,
        limit: 50,
      });
      setApplications(data.results);
      setTotal(data.total);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to fetch application records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [resumeId, statusFilter]);

  const handleRunBatch = async () => {
    if (!resumeId) return;
    setApplying(true);
    setError(null);
    setSummary(null);
    try {
      const res = await runApplyBatch(resumeId, {
        min_score: minScore,
        limit: batchLimit,
      });
      setSummary(res);
      fetchApplications();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to run apply batch automation.');
    } finally {
      setApplying(false);
    }
  };

  // Guard: No active resume
  if (!resumeId) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center max-w-xl mx-auto my-12 backdrop-blur-sm">
        <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="w-7 h-7" />
        </div>
        <h3 className="text-xl font-bold text-slate-100">Upload a Resume First</h3>
        <p className="text-slate-400 text-sm mt-2">
          To run automated applications and generate pre-submit screenshots, you must first upload a candidate resume.
        </p>
        <Link
          to="/resume"
          className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-sm rounded-xl transition-all shadow-lg shadow-emerald-500/20"
        >
          Go to Resume Upload
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'submitted':
        return {
          icon: CheckCircle2,
          class: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          label: 'Submitted',
        };
      case 'pending_review':
        return {
          icon: Clock,
          class: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          label: 'Pending Review',
        };
      case 'failed':
        return {
          icon: XCircle,
          class: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
          label: 'Failed',
        };
      default:
        return {
          icon: AlertCircle,
          class: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
          label: status,
        };
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Apply Automation</h2>
          <p className="text-slate-400 text-sm mt-1">
            Autonomous submission on Greenhouse/Lever ATS & safe fill-and-pause screenshotting on portals.
          </p>
        </div>
      </div>

      {/* ── Batch Apply Control Panel ────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wide mb-4">Run Apply Batch</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">
              Min Match Score: <span className="text-emerald-400 font-bold">{Math.round(minScore * 100)}%</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={minScore}
              onChange={(e) => setMinScore(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">Batch Limit (Jobs)</label>
            <select
              value={batchLimit}
              onChange={(e) => setBatchLimit(parseInt(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value={3}>3 Applications</option>
              <option value={5}>5 Applications</option>
              <option value={10}>10 Applications</option>
              <option value={20}>20 Applications</option>
            </select>
          </div>

          <button
            onClick={handleRunBatch}
            disabled={applying}
            className="w-full px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:pointer-events-none text-slate-950 font-semibold text-sm rounded-xl transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2"
          >
            {applying ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Automating Applications...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Run Apply Batch
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Apply Summary Toast ──────────────────────────────────────────── */}
      {summary && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-300 text-xs flex items-center justify-between gap-4 animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Batch Finished:</strong> Processed {summary.attempted} applications (
              <span className="text-emerald-400 font-bold">{summary.submitted} submitted</span>,{' '}
              <span className="text-amber-400 font-bold">{summary.pending_review} pending review</span>,{' '}
              <span className="text-rose-400 font-bold">{summary.failed} failed</span>).
            </span>
          </div>
          <button
            onClick={() => setSummary(null)}
            className="text-emerald-400 hover:text-emerald-200 text-xs font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Status Filter Dropdown ───────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Filter className="w-3.5 h-3.5" />
          <span>Filter Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
          >
            <option value="all">All Statuses ({total})</option>
            <option value="submitted">Submitted</option>
            <option value="pending_review">Pending Review</option>
            <option value="failed">Failed</option>
            <option value="skipped">Skipped</option>
          </select>
        </div>
      </div>

      {/* ── Applications Table ───────────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-6 font-semibold">Job & Company</th>
                <th className="py-3.5 px-6 font-semibold">Status</th>
                <th className="py-3.5 px-6 font-semibold">Application Details</th>
                <th className="py-3.5 px-6 font-semibold">Date</th>
                <th className="py-3.5 px-6 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-400" />
                    Loading applications...
                  </td>
                </tr>
              ) : applications.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500">
                    No application records found. Click <strong>"Run Apply Batch"</strong> above to automate top matches.
                  </td>
                </tr>
              ) : (
                applications.map((app) => {
                  const badge = getStatusBadge(app.status);
                  const Icon = badge.icon;
                  const job = app.job;
                  return (
                    <tr key={app.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-4 px-6">
                        <div className="font-semibold text-slate-100">{job?.title || 'Unknown Job'}</div>
                        <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-0.5">
                          <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          {job?.company || 'Unknown Company'}
                          {job?.source && (
                            <span className="text-[10px] text-slate-500 uppercase">({job.source})</span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${badge.class}`}>
                          <Icon className="w-3.5 h-3.5" />
                          {badge.label}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-xs text-slate-400 max-w-xs truncate">
                        {app.error_message ? (
                          <span title={app.error_message} className="text-slate-300">
                            {app.error_message}
                          </span>
                        ) : app.status === 'submitted' ? (
                          <span className="text-emerald-400/80 font-medium">Successfully submitted to ATS</span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-slate-500 text-xs">
                        {new Date(app.created_at).toLocaleDateString()}{' '}
                        <span className="text-slate-600">{new Date(app.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </td>
                      <td className="py-4 px-6 text-right space-x-2">
                        {app.has_screenshot && (
                          <button
                            onClick={() => setSelectedScreenshotUrl(getApplicationScreenshotUrl(app.id))}
                            className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 font-medium px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 transition-all"
                          >
                            <Eye className="w-3 h-3" />
                            View Screenshot
                          </button>
                        )}
                        {job?.apply_url && (
                          <a
                            href={job.apply_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 font-medium px-2 py-1 rounded-lg bg-slate-800/80 border border-slate-700 hover:bg-slate-700 transition-all"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Screenshot Lightbox Modal ────────────────────────────────────── */}
      {selectedScreenshotUrl && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl animate-fadeIn">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-amber-400" />
                <h4 className="font-semibold text-sm text-slate-200">Pre-Submit Review Screenshot</h4>
              </div>
              <button
                onClick={() => setSelectedScreenshotUrl(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 bg-slate-950/40 flex items-center justify-center">
              <img
                src={selectedScreenshotUrl}
                alt="Application Pre-Submit Review"
                className="rounded-xl border border-slate-800 max-w-full h-auto shadow-lg"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
