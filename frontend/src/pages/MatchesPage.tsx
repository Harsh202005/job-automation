import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { computeMatches, getMatches, getLatestResume, MatchDetail, ComputeMatchesSummary } from '../lib/api';
import { computeClientMatches } from '../lib/clientMatching';
import { Sparkles, Building2, ExternalLink, SlidersHorizontal, AlertCircle, CheckCircle2, ArrowUpDown, Loader2, ArrowRight, RefreshCw, Zap } from 'lucide-react';

interface MatchesPageProps {
  resumeId: string | null;
}

export const MatchesPage: React.FC<MatchesPageProps> = ({ resumeId }) => {
  const [activeId, setActiveId] = useState<string | null>(
    resumeId || localStorage.getItem('autoapply_resume_id')
  );
  const [matches, setMatches] = useState<MatchDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [minScore, setMinScore] = useState(0.3);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [summary, setSummary] = useState<ComputeMatchesSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    if (resumeId) {
      setActiveId(resumeId);
    } else {
      const saved = localStorage.getItem('autoapply_resume_id');
      if (saved) {
        setActiveId(saved);
      } else {
        getLatestResume()
          .then((r) => {
            if (r?.id) {
              setActiveId(r.id);
              localStorage.setItem('autoapply_resume_id', r.id);
            }
          })
          .catch(() => {});
      }
    }
  }, [resumeId]);

  const loadLocalMatches = () => {
    try {
      const saved = localStorage.getItem('autoapply_parsed_resume');
      let skills: string[] = [];
      if (saved) {
        const parsed = JSON.parse(saved);
        skills = parsed.skills || [];
      }
      const localResults = computeClientMatches(skills, activeId || 'active-resume', minScore);
      setMatches(localResults);
      setTotal(localResults.length);
      return localResults;
    } catch (e) {
      console.debug('Error computing local matches:', e);
      return [];
    }
  };

  const fetchMatches = async () => {
    if (!activeId) return;
    
    // 1. Instantly compute and display matches locally (< 5ms)
    loadLocalMatches();
    setError(null);

    // 2. Poll server in background without blocking
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 4000); // 4s server timeout safeguard
      const data = await getMatches(activeId, {
        min_score: minScore,
        limit: 50,
      }, controller.signal);
      clearTimeout(timer);

      if (data && data.results && data.results.length > 0) {
        setMatches(data.results);
        setTotal(data.total);
      }
    } catch (err: any) {
      console.debug('Server match sync note (using instant local matches):', err);
    }
  };

  useEffect(() => {
    if (activeId) {
      fetchMatches();
    } else {
      loadLocalMatches();
    }
  }, [activeId, minScore]);

  const handleCompute = async () => {
    setComputing(true);
    setError(null);

    // Instant local recalculation
    const updated = loadLocalMatches();
    setSummary({
      resume_id: activeId || 'active',
      jobs_evaluated: 6,
      matches_created: updated.length,
      matches_updated: 0,
      min_score_threshold: minScore,
    });

    if (activeId && !activeId.startsWith('resume-') && !activeId.startsWith('local-')) {
      try {
        const res = await computeMatches(activeId);
        setSummary(res);
        const data = await getMatches(activeId, {
          min_score: minScore,
          limit: 50,
        });
        if (data && data.results && data.results.length > 0) {
          setMatches(data.results);
          setTotal(data.total);
        }
      } catch (err: any) {
        console.debug('Server compute note:', err);
      }
    }

    setComputing(false);
  };

  const sortedMatches = [...matches].sort((a, b) => {
    return sortAsc ? a.score - b.score : b.score - a.score;
  });

  const getScoreBadge = (score: number) => {
    const pct = Math.round(score * 100);
    if (pct >= 70) {
      return {
        bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        bar: 'bg-emerald-500',
        label: `${pct}% Match`,
      };
    }
    if (pct >= 40) {
      return {
        bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        bar: 'bg-amber-500',
        label: `${pct}% Match`,
      };
    }
    return {
      bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
      bar: 'bg-rose-500',
      label: `${pct}% Match`,
    };
  };

  // Guard: No active resume and no local parsed resume
  if (!activeId && !localStorage.getItem('autoapply_parsed_resume')) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center max-w-xl mx-auto my-12 backdrop-blur-sm shadow-xl">
        <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="w-7 h-7" />
        </div>
        <h3 className="text-xl font-bold text-slate-100">Upload a Resume First</h3>
        <p className="text-slate-400 text-sm mt-2">
          To calculate semantic matches and skill gaps against job postings, simply upload your candidate resume.
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

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Semantic Matching Engine</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <Zap className="w-3 h-3" /> Sub-Second Scoring
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Scores open vacancies against your active resume using vector similarity and skill gap analysis.
          </p>
        </div>

        <button
          onClick={handleCompute}
          disabled={computing}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-xl transition-all shadow-lg shadow-emerald-500/20 self-start sm:self-auto"
        >
          {computing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Re-Calculate Matches
        </button>
      </div>

      {/* ── Filter & Threshold Controls ──────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 backdrop-blur-sm shadow-xl">
        <div className="flex items-center gap-4 w-full sm:w-auto">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-medium shrink-0">
            <SlidersHorizontal className="w-4 h-4 text-emerald-400" />
            <span>Min Score:</span>
            <span className="font-bold text-emerald-400 w-8">{Math.round(minScore * 100)}%</span>
          </div>
          <input
            type="range"
            min="0.1"
            max="0.9"
            step="0.05"
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="w-full sm:w-48 accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end text-xs text-slate-400">
          <span>
            Showing <strong className="text-slate-200">{sortedMatches.length}</strong> ranked vacancies
          </span>
          <button
            onClick={() => setSortAsc(!sortAsc)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition-colors border border-slate-700/60"
          >
            <ArrowUpDown className="w-3.5 h-3.5 text-emerald-400" />
            Sort by Score: <span className="text-emerald-400">{sortAsc ? 'Ascending' : 'Descending'}</span>
          </button>
        </div>
      </div>

      {/* ── Match Results Table ──────────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
            <span>Calculating semantic match vectors...</span>
          </div>
        ) : sortedMatches.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <p>No job postings match the selected minimum score threshold ({Math.round(minScore * 100)}%).</p>
            <p className="mt-1 text-slate-500">Try lowering the threshold slider above.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3.5 px-5">Job & Company</th>
                  <th className="py-3.5 px-5">Match Score</th>
                  <th className="py-3.5 px-5">Matched Skills</th>
                  <th className="py-3.5 px-5">Missing Skills</th>
                  <th className="py-3.5 px-5 text-right">Apply</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {sortedMatches.map((m) => {
                  const badge = getScoreBadge(m.score);
                  const job = m.job;
                  return (
                    <tr key={m.id || m.match_id} className="hover:bg-slate-800/30 transition-colors">
                      {/* Job & Company */}
                      <td className="py-4 px-5">
                        <div className="font-bold text-slate-100 text-sm">{job?.title || 'Open Position'}</div>
                        <div className="flex items-center gap-2 text-slate-400 mt-0.5">
                          <Building2 className="w-3.5 h-3.5 text-slate-500" />
                          <span className="font-medium text-slate-300">{job?.company || 'Company'}</span>
                          {job?.location && <span>• {job.location}</span>}
                        </div>
                      </td>

                      {/* Score */}
                      <td className="py-4 px-5 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${badge.bg}`}>
                            {badge.label}
                          </span>
                        </div>
                        <div className="w-24 bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${badge.bar}`}
                            style={{ width: `${Math.round(m.score * 100)}%` }}
                          />
                        </div>
                      </td>

                      {/* Matched Skills */}
                      <td className="py-4 px-5">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {m.matched_skills && m.matched_skills.length > 0 ? (
                            m.matched_skills.map((s, i) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-mono"
                              >
                                {s}
                              </span>
                            ))
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </div>
                      </td>

                      {/* Missing Skills */}
                      <td className="py-4 px-5">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {m.missing_skills && m.missing_skills.length > 0 ? (
                            m.missing_skills.map((s, i) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60 text-[11px] font-mono"
                              >
                                {s}
                              </span>
                            ))
                          ) : (
                            <span className="text-emerald-400 font-medium">All matched!</span>
                          )}
                        </div>
                      </td>

                      {/* Apply Action */}
                      <td className="py-4 px-5 text-right whitespace-nowrap">
                        {job?.apply_url ? (
                          <a
                            href={job.apply_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-emerald-500 hover:text-slate-950 text-emerald-400 text-xs font-semibold rounded-lg border border-slate-700 hover:border-emerald-500 transition-all shadow-sm"
                          >
                            Apply
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-slate-600 text-xs">No link</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
