import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { computeMatches, getMatches, MatchDetail, ComputeMatchesSummary } from '../lib/api';
import { Sparkles, Building2, ExternalLink, SlidersHorizontal, AlertCircle, CheckCircle2, ArrowUpDown, Loader2, ArrowRight } from 'lucide-react';

interface MatchesPageProps {
  resumeId: string | null;
}

export const MatchesPage: React.FC<MatchesPageProps> = ({ resumeId }) => {
  const [matches, setMatches] = useState<MatchDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [minScore, setMinScore] = useState(0.4);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [summary, setSummary] = useState<ComputeMatchesSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(false);

  const fetchMatches = async () => {
    if (!resumeId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getMatches(resumeId, {
        min_score: minScore,
        limit: 50,
      });
      setMatches(data.results);
      setTotal(data.total);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to fetch match scores.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatches();
  }, [resumeId, minScore]);

  const handleCompute = async () => {
    if (!resumeId) return;
    setComputing(true);
    setError(null);
    setSummary(null);
    try {
      const res = await computeMatches(resumeId);
      setSummary(res);
      fetchMatches();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to compute matches.');
    } finally {
      setComputing(false);
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
          To calculate semantic matches and skill gaps against job postings, you must first upload and parse your resume.
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

  const getScoreBadge = (score: number) => {
    const pct = Math.round(score * 100);
    if (pct >= 70) {
      return {
        bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        label: `${pct}% Match`,
      };
    }
    if (pct >= 40) {
      return {
        bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        label: `${pct}% Match`,
      };
    }
    return {
      bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
      label: `${pct}% Match`,
    };
  };

  const sortedMatches = [...matches].sort((a, b) => (sortAsc ? a.score - b.score : b.score - a.score));

  return (
    <div className="space-y-6">
      {/* ── Header & Compute Action ──────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Semantic Matching Engine</h2>
          <p className="text-slate-400 text-sm mt-1">
            Scores open vacancies against your active resume using local <code className="text-emerald-400 font-mono">all-MiniLM-L6-v2</code> embeddings.
          </p>
        </div>

        <button
          onClick={handleCompute}
          disabled={computing}
          className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:pointer-events-none text-slate-950 font-semibold text-sm rounded-xl transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2 self-start sm:self-auto"
        >
          {computing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Computing Embeddings...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Compute Matches
            </>
          )}
        </button>
      </div>

      {/* ── Compute Summary Toast ────────────────────────────────────────── */}
      {summary && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-300 text-xs flex items-center justify-between gap-4 animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Matching Complete:</strong> Evaluated {summary.total_jobs} open jobs. Computed {summary.matches_computed} matches. Top score: <strong>{(summary.top_score * 100).toFixed(1)}%</strong>.
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

      {/* ── Filters (Min Score Slider + Sorting) ─────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 backdrop-blur-sm">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <SlidersHorizontal className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="text-xs font-medium text-slate-300 whitespace-nowrap">
            Min Score: <span className="font-bold text-emerald-400">{Math.round(minScore * 100)}%</span>
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </div>

        <button
          onClick={() => setSortAsc(!sortAsc)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800 text-xs text-slate-300 transition-all self-start sm:self-auto"
        >
          <ArrowUpDown className="w-3.5 h-3.5 text-slate-500" />
          Sort by Score: <span className="font-semibold text-emerald-400">{sortAsc ? 'Ascending' : 'Descending'}</span>
        </button>
      </div>

      {/* ── Matches Table ────────────────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-6 font-semibold">Job & Company</th>
                <th className="py-3.5 px-6 font-semibold">Match Score</th>
                <th className="py-3.5 px-6 font-semibold">Matched Skills</th>
                <th className="py-3.5 px-6 font-semibold">Missing Skills</th>
                <th className="py-3.5 px-6 font-semibold text-right">Apply</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-400" />
                    Fetching matched vacancies...
                  </td>
                </tr>
              ) : sortedMatches.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500">
                    No matches found above {Math.round(minScore * 100)}% threshold. Click <strong>"Compute Matches"</strong> above or lower the minimum score slider.
                  </td>
                </tr>
              ) : (
                sortedMatches.map((m) => {
                  const badge = getScoreBadge(m.score);
                  const job = m.job;
                  return (
                    <tr key={m.id} className="hover:bg-slate-800/30 transition-colors">
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
                        <span className={`px-3 py-1 rounded-full text-xs font-bold border ${badge.bg}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        {m.matched_skills && m.matched_skills.length > 0 ? (
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {m.matched_skills.slice(0, 4).map((skill, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                              >
                                {skill}
                              </span>
                            ))}
                            {m.matched_skills.length > 4 && (
                              <span className="text-[10px] text-slate-500 self-center">
                                +{m.matched_skills.length - 4} more
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-4 px-6">
                        {m.missing_skills && m.missing_skills.length > 0 ? (
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {m.missing_skills.slice(0, 3).map((skill, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20"
                              >
                                {skill}
                              </span>
                            ))}
                            {m.missing_skills.length > 3 && (
                              <span className="text-[10px] text-slate-500 self-center">
                                +{m.missing_skills.length - 3}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-emerald-400/80 font-medium">None (Full Coverage)</span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-right">
                        {job?.apply_url ? (
                          <a
                            href={job.apply_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 font-medium px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all"
                          >
                            Apply
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-xs text-slate-600">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        <div className="py-3 px-6 border-t border-slate-800 text-xs text-slate-400 bg-slate-950/40">
          Showing {sortedMatches.length} matches (Score ≥ {Math.round(minScore * 100)}%)
        </div>
      </div>
    </div>
  );
};
