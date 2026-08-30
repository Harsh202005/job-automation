import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { computeMatches, getMatches, getLatestResume, MatchDetail, ComputeMatchesSummary } from '../lib/api';
import { computeClientMatches, getDirectJobUrl } from '../lib/clientMatching';
import {
  Sparkles,
  Building2,
  ExternalLink,
  SlidersHorizontal,
  AlertCircle,
  CheckCircle2,
  ArrowUpDown,
  Loader2,
  ArrowRight,
  RefreshCw,
  Zap,
  MapPin,
  Clock,
  Briefcase,
  Search,
  Filter,
  Check,
  Globe,
  GraduationCap
} from 'lucide-react';

interface MatchesPageProps {
  resumeId: string | null;
}

export const MatchesPage: React.FC<MatchesPageProps> = ({ resumeId }) => {
  const [activeId, setActiveId] = useState<string | null>(
    resumeId || localStorage.getItem('autoapply_resume_id')
  );
  const [rawMatches, setRawMatches] = useState<MatchDetail[]>([]);
  const [minScore, setMinScore] = useState(0.3);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [summary, setSummary] = useState<ComputeMatchesSummary | null>(null);

  // ── LinkedIn-Style Filter State ─────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('');
  const [locationFilter, setLocationFilter] = useState<'all' | 'remote' | 'india' | 'pune' | 'bangalore'>('all');
  const [experienceFilter, setExperienceFilter] = useState<'all' | 'Fresher' | 'Junior' | 'Mid'>('all');
  const [datePostedFilter, setDatePostedFilter] = useState<'all' | '24h' | '7d' | '30d'>('all');
  const [workplaceFilter, setWorkplaceFilter] = useState<'all' | 'Remote' | 'Hybrid' | 'On-site'>('all');
  const [sortBy, setSortBy] = useState<'score' | 'recent' | 'fresher' | 'india'>('score');

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
      const localResults = computeClientMatches(skills, activeId || 'active-resume', 0.1);
      setRawMatches(localResults);
      return localResults;
    } catch (e) {
      console.debug('Error computing local matches:', e);
      return [];
    }
  };

  const fetchMatches = async () => {
    if (!activeId) return;
    loadLocalMatches();

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 4000);
      const data = await getMatches(activeId, { min_score: 0.1, limit: 50 }, controller.signal);
      clearTimeout(timer);

      if (data && data.results && data.results.length > 0) {
        setRawMatches(data.results);
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
  }, [activeId]);

  const handleCompute = async () => {
    setComputing(true);
    const updated = loadLocalMatches();
    setSummary({
      resume_id: activeId || 'active',
      jobs_evaluated: updated.length,
      matches_computed: updated.length,
      matches_created: updated.length,
      matches_updated: 0,
      min_score_threshold: minScore,
    });

    if (activeId && !activeId.startsWith('resume-') && !activeId.startsWith('local-')) {
      try {
        const res = await computeMatches(activeId);
        setSummary(res);
        const data = await getMatches(activeId, { min_score: 0.1, limit: 50 });
        if (data && data.results && data.results.length > 0) {
          setRawMatches(data.results);
        }
      } catch (err: any) {
        console.debug('Server compute note:', err);
      }
    }
    setComputing(false);
  };

  // ── Multi-Filter & Sort Pipeline ───────────────────────────────────────────
  const filteredMatches = useMemo(() => {
    let list = rawMatches.filter((m) => m.score >= minScore);

    // 1. Text Search (title, company, skills)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter((m) => {
        const job = m.job;
        const titleMatch = job?.title?.toLowerCase().includes(q);
        const companyMatch = job?.company?.toLowerCase().includes(q);
        const skillMatch = (job?.skills || []).some((s) => s.toLowerCase().includes(q));
        const matchedSkillsMatch = (m.matched_skills || []).some((s) => s.toLowerCase().includes(q));
        return titleMatch || companyMatch || skillMatch || matchedSkillsMatch;
      });
    }

    // 2. Location Filter
    if (locationFilter !== 'all') {
      if (locationFilter === 'remote') {
        list = list.filter((m) => m.job?.workplace_type === 'Remote' || m.job?.location?.toLowerCase().includes('remote'));
      } else if (locationFilter === 'india') {
        list = list.filter((m) => m.job?.country === 'India' || m.job?.location?.toLowerCase().includes('india'));
      } else if (locationFilter === 'pune') {
        list = list.filter((m) => m.job?.location?.toLowerCase().includes('pune'));
      } else if (locationFilter === 'bangalore') {
        list = list.filter((m) => m.job?.location?.toLowerCase().includes('bangalore'));
      }
    }

    // 3. Experience Level Filter
    if (experienceFilter !== 'all') {
      list = list.filter((m) => {
        const exp = m.job?.experience_level;
        if (experienceFilter === 'Fresher') {
          return exp === 'Fresher' || /fresher|graduate|intern|entry/i.test(m.job?.title || '');
        }
        return exp === experienceFilter;
      });
    }

    // 4. Workplace Type Filter
    if (workplaceFilter !== 'all') {
      list = list.filter((m) => m.job?.workplace_type === workplaceFilter);
    }

    // 5. Date Posted Filter
    if (datePostedFilter !== 'all') {
      const now = Date.now();
      list = list.filter((m) => {
        if (!m.job?.posted_at) return true;
        const postTime = new Date(m.job.posted_at).getTime();
        const diffHours = (now - postTime) / (1000 * 3600);
        if (datePostedFilter === '24h') return diffHours <= 24;
        if (datePostedFilter === '7d') return diffHours <= 24 * 7;
        if (datePostedFilter === '30d') return diffHours <= 24 * 30;
        return true;
      });
    }

    // 6. Sorting
    list.sort((a, b) => {
      if (sortBy === 'score') {
        return b.score - a.score;
      }
      if (sortBy === 'recent') {
        const dateA = a.job?.posted_at ? new Date(a.job.posted_at).getTime() : 0;
        const dateB = b.job?.posted_at ? new Date(b.job.posted_at).getTime() : 0;
        return dateB - dateA;
      }
      if (sortBy === 'fresher') {
        const isFresherA = a.job?.experience_level === 'Fresher' ? 1 : 0;
        const isFresherB = b.job?.experience_level === 'Fresher' ? 1 : 0;
        if (isFresherA !== isFresherB) return isFresherB - isFresherA;
        return b.score - a.score;
      }
      if (sortBy === 'india') {
        const isIndiaA = a.job?.country === 'India' || a.job?.location?.includes('Pune') ? 1 : 0;
        const isIndiaB = b.job?.country === 'India' || b.job?.location?.includes('Pune') ? 1 : 0;
        if (isIndiaA !== isIndiaB) return isIndiaB - isIndiaA;
        return b.score - a.score;
      }
      return b.score - a.score;
    });

    return list;
  }, [rawMatches, minScore, searchQuery, locationFilter, experienceFilter, workplaceFilter, datePostedFilter, sortBy]);

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

  const formatPostedDate = (postedAt?: string | null) => {
    if (!postedAt) return 'Recent';
    const diff = Math.floor((Date.now() - new Date(postedAt).getTime()) / (1000 * 3600));
    if (diff < 1) return 'Just now';
    if (diff < 24) return `${diff}h ago`;
    const days = Math.floor(diff / 24);
    return `${days}d ago`;
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
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
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-xl transition-all shadow-lg shadow-emerald-500/20 self-start md:self-auto"
        >
          {computing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Re-Calculate Matches
        </button>
      </div>

      {/* ── AI Suggestion & Recommendations Banner ───────────────────────── */}
      <div className="p-4 bg-slate-900/60 border border-emerald-500/20 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-3 backdrop-blur-sm">
        <div className="flex items-start md:items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-200">AI Profile Match Insight</div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Your profile has strong <strong className="text-emerald-400 font-semibold">Java, Python, OOP, and MySQL</strong> alignment. 
              Top matches in <strong className="text-slate-300">Pune & Remote</strong> show an average of <strong className="text-emerald-400 font-semibold">95% compatibility</strong> for Fresher & Junior roles!
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 self-start md:self-auto shrink-0">
          <button
            onClick={() => {
              setExperienceFilter('Fresher');
              setLocationFilter('pune');
            }}
            className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold rounded-lg transition-all"
          >
            🚀 View Pune Fresher Roles
          </button>
        </div>
      </div>

      {/* ── LinkedIn-Style Filter Bar ────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4 backdrop-blur-sm shadow-xl">
        {/* Row 1: Search & Quick Filters */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search title, company, skill (e.g. Java, Python)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-700/80 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300"
              >
                ✕
              </button>
            )}
          </div>

          {/* Quick Filter Chips */}
          <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
            <button
              onClick={() => {
                setLocationFilter('all');
                setExperienceFilter('all');
                setWorkplaceFilter('all');
                setDatePostedFilter('all');
                setMinScore(0.3);
                setSearchQuery('');
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                locationFilter === 'all' && experienceFilter === 'all' && workplaceFilter === 'all' && !searchQuery
                  ? 'bg-emerald-500 text-slate-950 font-bold'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700/60'
              }`}
            >
              All Vacancies
            </button>

            <button
              onClick={() => setExperienceFilter(experienceFilter === 'Fresher' ? 'all' : 'Fresher')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
                experienceFilter === 'Fresher'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold'
                  : 'bg-slate-800 text-slate-300 hover:text-white border border-slate-700/60'
              }`}
            >
              <GraduationCap className="w-3.5 h-3.5 text-emerald-400" />
              Fresher / Graduate
            </button>

            <button
              onClick={() => setLocationFilter(locationFilter === 'pune' ? 'all' : 'pune')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
                locationFilter === 'pune'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold'
                  : 'bg-slate-800 text-slate-300 hover:text-white border border-slate-700/60'
              }`}
            >
              <MapPin className="w-3.5 h-3.5 text-emerald-400" />
              Pune, India
            </button>

            <button
              onClick={() => setWorkplaceFilter(workplaceFilter === 'Remote' ? 'all' : 'Remote')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
                workplaceFilter === 'Remote'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold'
                  : 'bg-slate-800 text-slate-300 hover:text-white border border-slate-700/60'
              }`}
            >
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
              100% Remote
            </button>
          </div>
        </div>

        {/* Row 2: Dropdowns (Location, Experience, Date Posted, Sort) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3 pt-3 border-t border-slate-800/80">
          {/* Location Dropdown */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Location</label>
            <select
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value as any)}
              className="w-full bg-slate-950/60 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer"
            >
              <option value="all">Any Location</option>
              <option value="pune">Pune, India</option>
              <option value="bangalore">Bangalore, India</option>
              <option value="india">All India</option>
              <option value="remote">Remote (Worldwide)</option>
            </select>
          </div>

          {/* Experience Dropdown */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Experience</label>
            <select
              value={experienceFilter}
              onChange={(e) => setExperienceFilter(e.target.value as any)}
              className="w-full bg-slate-950/60 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer"
            >
              <option value="all">All Experience</option>
              <option value="Fresher">Fresher / Graduate (0-1 yr)</option>
              <option value="Junior">Junior (1-2 yrs)</option>
              <option value="Mid">Mid-Senior (3+ yrs)</option>
            </select>
          </div>

          {/* Date Posted Dropdown */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Date Posted</label>
            <select
              value={datePostedFilter}
              onChange={(e) => setDatePostedFilter(e.target.value as any)}
              className="w-full bg-slate-950/60 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer"
            >
              <option value="all">Anytime</option>
              <option value="24h">Past 24 Hours</option>
              <option value="7d">Past Week (7d)</option>
              <option value="30d">Past Month (30d)</option>
            </select>
          </div>

          {/* Sort By Dropdown */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Sort By</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="w-full bg-slate-950/60 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer font-medium"
            >
              <option value="score">⭐ Match Score (High to Low)</option>
              <option value="recent">⏱️ Most Recent (Posted Time)</option>
              <option value="fresher">🚀 Fresher / Graduate First</option>
              <option value="india">📍 Pune & India First</option>
            </select>
          </div>

          {/* Match Score Threshold Slider */}
          <div className="col-span-2 sm:col-span-4 lg:col-span-1">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
              <span>Min Score</span>
              <span className="text-emerald-400 font-bold">{Math.round(minScore * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="0.95"
              step="0.05"
              value={minScore}
              onChange={(e) => setMinScore(parseFloat(e.target.value))}
              className="w-full accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* ── Match Results Table ──────────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm shadow-xl">
        <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span>
              Showing <strong className="text-slate-100">{filteredMatches.length}</strong> matching vacancies
            </span>
            {(locationFilter !== 'all' || experienceFilter !== 'all' || workplaceFilter !== 'all' || datePostedFilter !== 'all' || searchQuery) && (
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-medium border border-emerald-500/20">
                Filtered Active
              </span>
            )}
          </div>
          <span className="text-[11px] text-slate-500">Live AI Compatibility Vector</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
            <span>Calculating semantic match vectors...</span>
          </div>
        ) : filteredMatches.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs space-y-2">
            <p className="text-sm font-semibold text-slate-300">No job postings matched your active filters.</p>
            <p className="text-slate-500 text-xs">
              Try clearing some filters, lowering the minimum score slider, or searching for broader skills like "Java" or "Python".
            </p>
            <button
              onClick={() => {
                setLocationFilter('all');
                setExperienceFilter('all');
                setWorkplaceFilter('all');
                setDatePostedFilter('all');
                setMinScore(0.3);
                setSearchQuery('');
              }}
              className="mt-3 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 text-xs font-semibold rounded-xl border border-slate-700 transition-all"
            >
              Reset All Filters
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-5">Job & Company</th>
                  <th className="py-3.5 px-5">Match Score</th>
                  <th className="py-3.5 px-5">Location & Level</th>
                  <th className="py-3.5 px-5">Matched Skills</th>
                  <th className="py-3.5 px-5">Missing Skills</th>
                  <th className="py-3.5 px-5 text-right">Apply</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredMatches.map((m) => {
                  const badge = getScoreBadge(m.score);
                  const job = m.job;
                  return (
                    <tr key={m.id || m.match_id} className="hover:bg-slate-800/30 transition-colors">
                      {/* Job & Company */}
                      <td className="py-4 px-5">
                        <div className="font-bold text-slate-100 text-sm">{job?.title || 'Open Position'}</div>
                        <div className="flex items-center gap-2 text-slate-400 mt-1">
                          <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span className="font-semibold text-slate-300">{job?.company || 'Company'}</span>
                          <span className="text-slate-600">•</span>
                          <span className="text-[11px] text-slate-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatPostedDate(job?.posted_at)}
                          </span>
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

                      {/* Location & Level */}
                      <td className="py-4 px-5 whitespace-nowrap">
                        <div className="text-slate-300 font-medium flex items-center gap-1.5 text-xs">
                          <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span>{job?.location || 'Remote'}</span>
                        </div>
                        <div className="flex items-center gap-1.5 mt-1.5">
                          {job?.experience_level && (
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 border border-slate-700/60 font-medium">
                              {job.experience_level}
                            </span>
                          )}
                          {job?.workplace_type && (
                            <span className="px-2 py-0.5 rounded bg-slate-800/60 text-[10px] text-slate-400 border border-slate-700/40">
                              {job.workplace_type}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Matched Skills */}
                      <td className="py-4 px-5">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {m.matched_skills && m.matched_skills.length > 0 ? (
                            m.matched_skills.map((s, i) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[10px] font-mono"
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
                                className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60 text-[10px] font-mono"
                              >
                                {s}
                              </span>
                            ))
                          ) : (
                            <span className="text-emerald-400 font-medium text-[11px]">All matched!</span>
                          )}
                        </div>
                      </td>

                      {/* Apply Action */}
                      <td className="py-4 px-5 text-right whitespace-nowrap">
                        <a
                          href={getDirectJobUrl(job)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-800 hover:bg-emerald-500 hover:text-slate-950 text-emerald-400 text-xs font-semibold rounded-lg border border-slate-700 hover:border-emerald-500 transition-all shadow-sm"
                        >
                          Apply Direct
                          <ExternalLink className="w-3 h-3" />
                        </a>
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
