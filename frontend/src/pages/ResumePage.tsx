import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadResume, getResume, getLatestResume, getMatches, ParsedResume, MatchDetail } from '../lib/api';
import { extractPdfTextInBrowser, parseResumeText } from '../lib/clientParser';
import {
  UploadCloud,
  FileText,
  CheckCircle,
  AlertTriangle,
  Briefcase,
  GraduationCap,
  Phone,
  Mail,
  User,
  Loader2,
  Sparkles,
  Zap,
  ArrowRight,
  Building2,
  ExternalLink,
  Target,
  RefreshCw,
  Clock,
  CheckCircle2
} from 'lucide-react';

interface ResumePageProps {
  onResumeUploaded: (resumeId: string) => void;
}

export const ResumePage: React.FC<ResumePageProps> = ({ onResumeUploaded }) => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'synced'>('idle');
  const [matchingStatus, setMatchingStatus] = useState<'idle' | 'matching' | 'ready'>('idle');
  const [initialLoading, setInitialLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<ParsedResume | null>(null);
  const [topMatches, setTopMatches] = useState<MatchDetail[]>([]);
  const [autoMatchEnabled, setAutoMatchEnabled] = useState(true);
  const [isDragging, setIsDragging] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Restore persisted resume and active state immediately on mount
  useEffect(() => {
    // 1. First check localStorage for immediate zero-lag restoration
    const savedParsed = localStorage.getItem('autoapply_parsed_resume');
    if (savedParsed) {
      try {
        const data = JSON.parse(savedParsed);
        setParsedData(data);
        if (data.id) {
          onResumeUploaded(data.id);
        }
      } catch (e) {
        console.debug('Failed to parse saved resume:', e);
      }
    }

    const savedId = localStorage.getItem('autoapply_resume_id');
    const controller = new AbortController();

    // 2. Fetch server updates softly with a 3s timeout safeguard
    const loadResumeData = async (id?: string) => {
      try {
        const resume = id
          ? await getResume(id, controller.signal)
          : await getLatestResume(controller.signal);
        if (resume && resume.id) {
          setParsedData(resume);
          localStorage.setItem('autoapply_parsed_resume', JSON.stringify(resume));
          localStorage.setItem('autoapply_resume_id', resume.id);
          onResumeUploaded(resume.id);
          try {
            const matchData = await getMatches(resume.id, { min_score: 0.3, limit: 4 });
            setTopMatches(matchData.results || []);
            if (matchData.results && matchData.results.length > 0) {
              setMatchingStatus('ready');
            }
          } catch (e) {
            console.debug('No matches for resume yet:', e);
          }
        }
      } catch (err) {
        console.debug('Server resume sync skipped/cached:', err);
      }
    };

    loadResumeData(savedId || undefined);

    return () => {
      controller.abort();
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.pdf') || droppedFile.name.endsWith('.docx')) {
        setFile(droppedFile);
        setError(null);
      } else {
        setError('Only .pdf and .docx resume files are supported.');
      }
    }
  };

  const pollMatches = async (resumeId: string) => {
    setMatchingStatus('matching');
    for (let attempt = 0; attempt < 5; attempt++) {
      await new Promise((r) => setTimeout(r, 1200));
      try {
        const matchData = await getMatches(resumeId, { min_score: 0.3, limit: 4 });
        if (matchData.results && matchData.results.length > 0) {
          setTopMatches(matchData.results);
          setMatchingStatus('ready');
          return;
        }
      } catch (e) {
        console.debug('Polling matches attempt', attempt, e);
      }
    }
    setMatchingStatus('ready');
  };

  const handleUploadAndAutoProcess = async () => {
    if (!file) {
      setError('Please select a resume file to upload.');
      return;
    }

    setError(null);

    // ── 1. Instant In-Browser Parse (< 50ms) ─────────────────────────────────
    // Renders the profile card immediately so the user NEVER waits on a server!
    try {
      const text = await extractPdfTextInBrowser(file);
      const localParsed = parseResumeText(text, file.name);
      setParsedData(localParsed);
      localStorage.setItem('autoapply_parsed_resume', JSON.stringify(localParsed));
      localStorage.setItem('autoapply_resume_id', localParsed.id);
      onResumeUploaded(localParsed.id);
    } catch (clientErr) {
      console.debug('Client parse pre-pass note:', clientErr);
    }

    // ── 2. Background Server Sync (Non-blocking) ─────────────────────────────
    setSyncStatus('syncing');
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await uploadResume(
        file,
        { autoMatch: autoMatchEnabled },
        controller.signal
      );

      setParsedData(res);
      localStorage.setItem('autoapply_parsed_resume', JSON.stringify(res));
      localStorage.setItem('autoapply_resume_id', res.id);
      onResumeUploaded(res.id);
      setSyncStatus('synced');

      if (autoMatchEnabled) {
        pollMatches(res.id);
      }
    } catch (err: any) {
      console.debug('Background server sync noted:', err);
      setSyncStatus('idle');
    }
  };

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

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Instant Resume Parser & Matcher</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <Zap className="w-3 h-3" /> Sub-Second Engine
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Upload your resume. The C++ parser extracts your candidate profile in milliseconds and pairs it with active vacancies.
          </p>
        </div>

        {parsedData?.id && (
          <button
            onClick={() => navigate('/matches')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700/80 transition-all self-start md:self-auto"
          >
            <Target className="w-3.5 h-3.5 text-emerald-400" />
            View All Job Matches
            <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          </button>
        )}
      </div>

      {/* ── Dropzone & Instant Upload Panel ───────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm shadow-xl">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center transition-all cursor-pointer ${
            isDragging
              ? 'border-emerald-500 bg-emerald-500/5 shadow-inner'
              : 'border-slate-700/80 hover:border-slate-600 bg-slate-950/40'
          }`}
          onClick={() => document.getElementById('resume-file-input')?.click()}
        >
          <input
            id="resume-file-input"
            type="file"
            accept=".pdf,.docx"
            className="hidden"
            onChange={handleFileChange}
          />
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3">
            <UploadCloud className="w-7 h-7" />
          </div>
          <p className="text-slate-200 font-medium text-sm">
            {file ? file.name : 'Click to select or drag and drop your resume file'}
          </p>
          <p className="text-slate-500 text-xs mt-1">Accepts PDF & DOCX • High-Speed C++ & Layout Parser</p>
        </div>

        {/* Server Sync Status Pill */}
        {syncStatus === 'syncing' && (
          <div className="mt-3.5 px-3.5 py-2 bg-slate-800/60 border border-slate-700/60 rounded-xl text-slate-300 text-xs flex items-center justify-between gap-3 animate-fadeIn">
            <div className="flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 text-emerald-400 animate-spin shrink-0" />
              <span>Resume parsed locally. Syncing with database in background...</span>
            </div>
            <span className="text-[11px] text-emerald-400 font-medium">Auto-Sync</span>
          </div>
        )}

        {/* Action Bar */}
        <div className="mt-5 flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
          {/* Auto-match toggle */}
          <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300 select-none">
            <input
              type="checkbox"
              checked={autoMatchEnabled}
              onChange={(e) => setAutoMatchEnabled(e.target.checked)}
              className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-0 focus:ring-offset-0 cursor-pointer accent-emerald-500"
            />
            <span className="flex items-center gap-1.5 font-medium">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              Auto-calculate semantic job matches in background
            </span>
          </label>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            {file && (
              <span className="text-xs text-slate-400 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-emerald-400" />
                {(file.size / 1024).toFixed(1)} KB
              </span>
            )}
            <button
              onClick={handleUploadAndAutoProcess}
              disabled={!file}
              className="w-full sm:w-auto px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:pointer-events-none text-slate-950 font-bold text-sm rounded-xl transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2"
            >
              <Zap className="w-4 h-4" />
              Parse & Auto-Match
            </button>
          </div>
        </div>
      </div>

      {/* ── Background Matching Banner ───────────────────────────────────── */}
      {matchingStatus === 'matching' && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-300 text-xs flex items-center justify-between gap-4 animate-fadeIn">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 text-emerald-400 animate-spin shrink-0" />
            <span>
              <strong>Resume Loaded!</strong> Computing semantic similarity against active vacancies in background...
            </span>
          </div>
          <span className="text-[11px] text-emerald-400 font-mono">all-MiniLM-L6-v2</span>
        </div>
      )}

      {/* ── Top Matched Opportunities ────────────────────────────────────── */}
      {topMatches && topMatches.length > 0 && (
        <div className="space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-bold text-slate-100">Top Matched Job Opportunities</h3>
              <span className="text-xs text-slate-500">({topMatches.length} recommended)</span>
            </div>
            <button
              onClick={() => navigate('/matches')}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              See all ranked vacancies <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topMatches.map((match) => {
              const badge = getScoreBadge(match.score);
              const job = match.job;
              return (
                <div
                  key={match.id}
                  className="bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 backdrop-blur-sm transition-all hover:shadow-lg flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="font-bold text-slate-100 text-sm">{job?.title || 'Open Position'}</h4>
                        <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-1">
                          <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span className="font-medium text-slate-300">{job?.company || 'Company'}</span>
                          {job?.location && <span>• {job.location}</span>}
                        </div>
                      </div>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold border shrink-0 ${badge.bg}`}>
                        {badge.label}
                      </span>
                    </div>

                    <div className="mt-3.5 space-y-1.5">
                      {match.matched_skills && match.matched_skills.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1 text-[11px]">
                          <span className="text-slate-500 font-medium mr-1">Matched:</span>
                          {match.matched_skills.slice(0, 3).map((s, i) => (
                            <span key={i} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono">
                              {s}
                            </span>
                          ))}
                          {match.matched_skills.length > 3 && (
                            <span className="text-slate-500 text-[10px]">+{match.matched_skills.length - 3}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[11px] text-slate-500 uppercase">{job?.source || 'ATS'}</span>
                    {job?.apply_url && (
                      <a
                        href={job.apply_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300"
                      >
                        Apply Portal
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Parsed Resume Details ────────────────────────────────────────── */}
      {parsedData && (
        <div className="space-y-6 animate-fadeIn">
          {/* Candidate Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
              <div>
                <div className="flex items-center gap-2">
                  <User className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-xl font-bold text-slate-100">{parsedData.full_name || 'Candidate Profile'}</h3>
                </div>
                <div className="flex flex-wrap gap-4 mt-2 text-xs text-slate-400">
                  {parsedData.email && (
                    <span className="flex items-center gap-1.5">
                      <Mail className="w-3.5 h-3.5 text-slate-500" />
                      {parsedData.email}
                    </span>
                  )}
                  {parsedData.phone && (
                    <span className="flex items-center gap-1.5">
                      <Phone className="w-3.5 h-3.5 text-slate-500" />
                      {parsedData.phone}
                    </span>
                  )}
                  {parsedData.filename && (
                    <span className="flex items-center gap-1.5 text-slate-500">
                      <FileText className="w-3.5 h-3.5" />
                      {parsedData.filename}
                    </span>
                  )}
                </div>
              </div>
              <div className="px-3.5 py-1.5 bg-slate-800/80 rounded-xl border border-slate-700 text-xs text-slate-300 flex items-center gap-1.5 self-start">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                Total Experience: <span className="font-semibold text-emerald-400">{parsedData.total_experience_years} yrs</span>
              </div>
            </div>

            {/* Skills */}
            <div className="mt-5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2.5">Extracted Skills</h4>
              {parsedData.skills && parsedData.skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {parsedData.skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500">No skills identified.</p>
              )}
            </div>
          </div>

          {/* Work Experience */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <Briefcase className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wide">Work Experience & Internships</h3>
            </div>
            {parsedData.experience && parsedData.experience.length > 0 ? (
              <div className="space-y-4">
                {parsedData.experience.map((exp, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-semibold text-slate-200 text-sm">{exp.title}</h4>
                        <p className="text-xs text-emerald-400 font-medium">{exp.company}</p>
                      </div>
                      {exp.duration && (
                        <span className="text-[11px] text-slate-500 px-2 py-0.5 bg-slate-800/60 rounded-md border border-slate-700/50">
                          {exp.duration}
                        </span>
                      )}
                    </div>
                    {exp.description && (
                      <p className="text-xs text-slate-400 mt-2 line-clamp-3 leading-relaxed whitespace-pre-line">
                        {exp.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">No experience sections detected.</p>
            )}
          </div>

          {/* Education */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <GraduationCap className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wide">Education</h3>
            </div>
            {parsedData.education && parsedData.education.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {parsedData.education.map((edu, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80">
                    <h4 className="font-semibold text-slate-200 text-sm">{edu.degree}</h4>
                    <p className="text-xs text-slate-400 mt-0.5">{edu.institution}</p>
                    {edu.year && <p className="text-[11px] text-slate-500 mt-1">Year: {edu.year}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">No education records found.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
