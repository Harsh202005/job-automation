import React, { useState, useEffect } from 'react';
import { getJobs, ingestJobs, ingestScraperJobs, Job, IngestSummary, ScraperIngestSummary } from '../lib/api';
import {
  DownloadCloud,
  Search,
  ExternalLink,
  MapPin,
  Calendar,
  Building2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Globe,
  Bot,
  Filter,
  Sparkles
} from 'lucide-react';

export const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [companyFilter, setCompanyFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [ingestSummary, setIngestSummary] = useState<IngestSummary | null>(null);
  const [scraperSummary, setScraperSummary] = useState<ScraperIngestSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const PAGE_SIZE = 20;

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJobs({
        company: companyFilter.trim() || undefined,
        source: sourceFilter !== 'all' ? sourceFilter : undefined,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      });
      setJobs(data.results);
      setTotal(data.total);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to fetch jobs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [page, companyFilter, sourceFilter]);

  const handleIngest = async () => {
    setIngesting(true);
    setIngestSummary(null);
    setError(null);
    try {
      const summary = await ingestJobs();
      setIngestSummary(summary);
      fetchJobs();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to ingest jobs from ATS & Job APIs.');
    } finally {
      setIngesting(false);
    }
  };

  const handleScrape = async () => {
    setScraping(true);
    setScraperSummary(null);
    setError(null);
    try {
      const summary = await ingestScraperJobs();
      setScraperSummary(summary);
      fetchJobs();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to scrape jobs from LinkedIn & Naukri.');
    } finally {
      setScraping(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

  const getSourceBadge = (source: string) => {
    const src = (source || '').toLowerCase();
    switch (src) {
      case 'greenhouse':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'lever':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
      case 'arbeitnow':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
      case 'remoteok':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'adzuna':
        return 'bg-teal-500/10 text-teal-400 border-teal-500/20';
      case 'linkedin':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'naukri':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      default:
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    }
  };

  const sourcesList = [
    { id: 'all', label: 'All Sources' },
    { id: 'greenhouse', label: 'Greenhouse' },
    { id: 'lever', label: 'Lever' },
    { id: 'adzuna', label: 'Adzuna' },
    { id: 'arbeitnow', label: 'Arbeitnow' },
    { id: 'remoteok', label: 'RemoteOK' },
    { id: 'linkedin', label: 'LinkedIn (Scraper)' },
    { id: 'naukri', label: 'Naukri (Scraper)' },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* ── Page Header & Action Triggers ─────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Aggregated Job Postings</h2>
          <p className="text-slate-400 text-sm mt-1">
            Vacancies collected via official ATS APIs (Greenhouse, Lever, Adzuna, Arbeitnow, RemoteOK) and best-effort scrapers (LinkedIn, Naukri).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Main API Ingestion */}
          <button
            onClick={handleIngest}
            disabled={ingesting || scraping}
            className="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:pointer-events-none text-slate-950 font-bold text-xs rounded-xl transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2"
          >
            {ingesting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Ingesting Job APIs...
              </>
            ) : (
              <>
                <DownloadCloud className="w-4 h-4" />
                Ingest Free Job APIs
              </>
            )}
          </button>

          {/* LinkedIn / Naukri Scrapers */}
          <button
            onClick={handleScrape}
            disabled={ingesting || scraping}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-sky-500/30 hover:border-sky-500/50 disabled:opacity-50 disabled:pointer-events-none font-bold text-xs rounded-xl transition-all shadow-md flex items-center gap-2"
          >
            {scraping ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                Scraping LinkedIn & Naukri...
              </>
            ) : (
              <>
                <Bot className="w-4 h-4 text-sky-400" />
                Scrape LinkedIn / Naukri
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Ingest Summary Banner ────────────────────────────────────────── */}
      {ingestSummary && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-300 text-xs flex items-center justify-between gap-4 animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Job APIs Ingestion Complete:</strong> Fetched {ingestSummary.fetched} jobs ({ingestSummary.new} new, {ingestSummary.updated} updated).
            </span>
          </div>
          <button
            onClick={() => setIngestSummary(null)}
            className="text-emerald-400 hover:text-emerald-200 text-xs font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Scraper Summary Banner ───────────────────────────────────────── */}
      {scraperSummary && (
        <div className="p-4 bg-sky-500/10 border border-sky-500/20 rounded-2xl text-sky-300 text-xs flex items-center justify-between gap-4 animate-fadeIn">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-sky-400 shrink-0" />
            <span>
              <strong>Scraper Run Complete:</strong> Scraped {scraperSummary.fetched} listings ({scraperSummary.new} new, {scraperSummary.updated} updated) for "{scraperSummary.query || 'software engineer'}" in "{scraperSummary.location || 'pune'}".
            </span>
          </div>
          <button
            onClick={() => setScraperSummary(null)}
            className="text-sky-400 hover:text-sky-200 text-xs font-semibold"
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

      {/* ── Filters & Source Tabs ────────────────────────────────────────── */}
      <div className="space-y-3 bg-slate-900/60 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm shadow-xl">
        {/* Search */}
        <div className="flex items-center gap-3 bg-slate-950/60 border border-slate-800 rounded-xl px-3.5 py-2">
          <Search className="w-4 h-4 text-slate-500 shrink-0" />
          <input
            type="text"
            placeholder="Search by company name..."
            value={companyFilter}
            onChange={(e) => {
              setCompanyFilter(e.target.value);
              setPage(1);
            }}
            className="bg-transparent border-none outline-none text-xs text-slate-200 placeholder-slate-500 w-full"
          />
        </div>

        {/* Source Tags */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mr-2 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Sources:
          </span>
          {sourcesList.map((src) => (
            <button
              key={src.id}
              onClick={() => {
                setSourceFilter(src.id);
                setPage(1);
              }}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                sourceFilter === src.id
                  ? 'bg-emerald-500 text-slate-950 font-bold'
                  : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 border border-slate-700/60'
              }`}
            >
              {src.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Jobs Table ───────────────────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 text-[11px] uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-6 font-semibold">Job Title</th>
                <th className="py-3.5 px-6 font-semibold">Company</th>
                <th className="py-3.5 px-6 font-semibold">Location</th>
                <th className="py-3.5 px-6 font-semibold">Source</th>
                <th className="py-3.5 px-6 font-semibold">Posted</th>
                <th className="py-3.5 px-6 font-semibold text-right">Apply Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-400" />
                    Loading job listings...
                  </td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    No job postings found for the selected filter. Click <strong>"Ingest Free Job APIs"</strong> or <strong>"Scrape LinkedIn / Naukri"</strong> above.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-4 px-6 font-bold text-slate-100 text-sm">
                      {job.title}
                    </td>
                    <td className="py-4 px-6 text-slate-300">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        <span className="font-semibold">{job.company}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-slate-400 text-xs">
                      {job.location ? (
                        <div className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
                          <span className="truncate max-w-[180px]">{job.location}</span>
                        </div>
                      ) : (
                        <span className="text-slate-600">Remote / Unspecified</span>
                      )}
                    </td>
                    <td className="py-4 px-6">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${getSourceBadge(job.source)}`}>
                        {job.source}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-slate-500 text-xs">
                      {job.posted_at ? (
                        <div className="flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-slate-600 shrink-0" />
                          {new Date(job.posted_at).toLocaleDateString()}
                        </div>
                      ) : (
                        <span className="text-slate-600">Recent</span>
                      )}
                    </td>
                    <td className="py-4 px-6 text-right">
                      <a
                        href={job.apply_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 font-semibold px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all"
                      >
                        Apply
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination ─────────────────────────────────────────────────── */}
        <div className="py-3.5 px-6 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 bg-slate-950/40">
          <span>
            Showing {jobs.length > 0 ? (page - 1) * PAGE_SIZE + 1 : 0} to {Math.min(page * PAGE_SIZE, total)} of {total} jobs
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
              className="p-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold text-slate-300 px-2">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="p-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 disabled:opacity-30 disabled:pointer-events-none transition-all"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
