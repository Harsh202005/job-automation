import React, { useState, useEffect } from 'react';
import { uploadResume, getResume, ParsedResume } from '../lib/api';
import { UploadCloud, FileText, CheckCircle, AlertTriangle, Briefcase, GraduationCap, Phone, Mail, User, Loader2 } from 'lucide-react';

interface ResumePageProps {
  onResumeUploaded: (resumeId: string) => void;
}

export const ResumePage: React.FC<ResumePageProps> = ({ onResumeUploaded }) => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<ParsedResume | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Load existing resume if saved in localStorage
  useEffect(() => {
    const savedId = localStorage.getItem('autoapply_resume_id');
    if (savedId) {
      setInitialLoading(true);
      getResume(savedId)
        .then((data) => {
          setParsedData(data);
        })
        .catch((err) => {
          console.warn('Could not fetch saved resume:', err);
          localStorage.removeItem('autoapply_resume_id');
        })
        .finally(() => setInitialLoading(false));
    }
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

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a resume file to upload.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await uploadResume(file);
      setParsedData(res);
      localStorage.setItem('autoapply_resume_id', res.id);
      onResumeUploaded(res.id);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to parse resume. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <div>
        <h2 className="text-2xl font-bold text-slate-100 tracking-tight">Resume Parser</h2>
        <p className="text-slate-400 text-sm mt-1">
          Upload your candidate resume in PDF or DOCX format. Parsed skills and experiences will be used for automated job matching.
        </p>
      </div>

      {/* ── Dropzone & Upload Action ─────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center transition-all cursor-pointer ${
            isDragging
              ? 'border-emerald-500 bg-emerald-500/5'
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
            {file ? file.name : 'Click to browse or drag and drop your resume file'}
          </p>
          <p className="text-slate-500 text-xs mt-1">Accepts PDF, DOCX (up to 10MB)</p>
        </div>

        {error && (
          <div className="mt-4 p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            {file && (
              <span className="flex items-center gap-1.5 text-emerald-400">
                <FileText className="w-3.5 h-3.5" />
                Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </span>
            )}
          </div>
          <button
            onClick={handleUpload}
            disabled={loading || !file}
            className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:pointer-events-none text-slate-950 font-semibold text-sm rounded-xl transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Parsing Resume...
              </>
            ) : (
              'Parse & Save Resume'
            )}
          </button>
        </div>
      </div>

      {/* ── Parsed Resume Display ────────────────────────────────────────── */}
      {initialLoading && (
        <div className="flex items-center justify-center py-12 text-slate-400 text-sm gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-emerald-400" />
          Loading parsed resume details...
        </div>
      )}

      {parsedData && !initialLoading && (
        <div className="space-y-6 animate-fadeIn">
          {/* Warning Banner */}
          {parsedData.parse_warnings && parsedData.parse_warnings.length > 0 && (
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl text-amber-300 text-xs">
              <div className="flex items-center gap-2 font-semibold mb-1">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Parse Warnings
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-amber-200/80">
                {parsedData.parse_warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Candidate Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
              <div>
                <div className="flex items-center gap-2">
                  <User className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-xl font-bold text-slate-100">{parsedData.full_name || 'Candidate Name Not Found'}</h3>
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
                </div>
              </div>
              <div className="px-3.5 py-1.5 bg-slate-800 rounded-xl border border-slate-700 text-xs text-slate-300 flex items-center gap-1.5 self-start">
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
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wide">Work Experience</h3>
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
