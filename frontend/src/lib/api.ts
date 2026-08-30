import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.BACKEND_URL ||
  'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds (1 min) request timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      error.customMessage =
        'Request timed out after 1 minute. The backend server on Render free-tier might still be waking up. Please retry in a few moments.';
    }
    return Promise.reject(error);
  }
);

// ── TypeScript Interfaces ───────────────────────────────────────────────────

export interface ExperienceItem {
  title: string;
  company: string;
  duration?: string;
  description?: string;
}

export interface EducationItem {
  degree: string;
  institution: string;
  year?: string;
}

export interface ProjectItem {
  title: string;
  skills?: string[];
  link?: string;
  duration?: string;
  description?: string;
}

export interface CertificationItem {
  name: string;
  issuer?: string;
  skills?: string[];
  description?: string;
}

export interface ParsedResume {
  id: string;
  filename: string;
  full_name: string;
  email: string;
  phone: string;
  linkedin?: string;
  github?: string;
  summary?: string;
  skills: string[];
  experience: ExperienceItem[];
  education: EducationItem[];
  projects?: ProjectItem[];
  certifications?: CertificationItem[];
  total_experience_years: number;
  parse_warnings: string[];
}

export interface Job {
  id: string;
  source: string;
  source_job_id: string;
  company: string;
  title: string;
  location?: string | null;
  description?: string;
  apply_url: string;
  skills?: string[];
  experience_level?: 'Fresher' | 'Junior' | 'Mid' | 'Senior';
  workplace_type?: 'Remote' | 'On-site' | 'Hybrid';
  country?: string;
  posted_at?: string | null;
  fetched_at?: string;
}

export interface IngestSummary {
  fetched: number;
  new: number;
  updated: number;
  errors: number | string[];
}

export interface MatchDetail {
  id: string;
  match_id?: string;
  resume_id?: string;
  job_id: string;
  score: number;
  matched_skills: string[];
  missing_skills: string[];
  computed_at?: string | null;
  job?: Job | null;
}

export interface ComputeMatchesSummary {
  resume_id?: string;
  total_jobs?: number;
  jobs_evaluated?: number;
  matches_computed?: number;
  matches_created?: number;
  matches_updated?: number;
  min_score_threshold?: number;
  top_score?: number;
  errors?: string[];
}

export interface UploadResumeResponse extends ParsedResume {
  auto_matched?: boolean;
  matching_summary?: ComputeMatchesSummary | null;
  top_matches?: MatchDetail[];
}

export interface ApplicationJobInfo {
  id: string;
  company: string;
  title: string;
  location?: string | null;
  source: string;
  apply_url: string;
}

export interface ApplicationItem {
  id: string;
  resume_id: string;
  job_id: string;
  status: 'pending_review' | 'submitted' | 'failed' | 'skipped';
  submitted_at?: string | null;
  created_at: string;
  has_screenshot: boolean;
  error_message?: string | null;
  job?: ApplicationJobInfo | null;
}

export interface ApplyBatchSummary {
  attempted: number;
  submitted: number;
  pending_review: number;
  failed: number;
  applications: {
    application_id: string;
    job_id: string;
    company: string;
    title: string;
    source: string;
    status: string;
    error_message?: string | null;
    has_screenshot: boolean;
  }[];
}

export interface PipelineRunResponse {
  id: string;
  resume_id: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  ingest_summary?: IngestSummary | null;
  matching_summary?: ComputeMatchesSummary | null;
  apply_summary?: ApplyBatchSummary | null;
  error_log?: string[] | null;
}

// ── API Functions ───────────────────────────────────────────────────────────

// Resume API
export async function uploadResume(
  file: File,
  options: { autoMatch?: boolean; topMatchesLimit?: number } = { autoMatch: true, topMatchesLimit: 6 },
  signal?: AbortSignal
): Promise<UploadResumeResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await apiClient.post<UploadResumeResponse>('/api/resume/upload', formData, {
    params: {
      auto_match: options.autoMatch ?? true,
      top_matches_limit: options.topMatchesLimit ?? 6,
    },
    headers: { 'Content-Type': 'multipart/form-data' },
    signal,
  });
  return res.data;
}

export async function getResume(resumeId: string, signal?: AbortSignal): Promise<ParsedResume> {
  const res = await apiClient.get<ParsedResume>(`/api/resume/${resumeId}`, { signal });
  return res.data;
}

export async function getLatestResume(signal?: AbortSignal): Promise<ParsedResume> {
  const res = await apiClient.get<ParsedResume>('/api/resume/latest', { signal });
  return res.data;
}

// Jobs API
export async function ingestJobs(): Promise<IngestSummary> {
  const res = await apiClient.post<IngestSummary>('/api/jobs/ingest');
  return res.data;
}

export async function getJobs(params?: {
  company?: string;
  source?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; limit: number; offset: number; results: Job[] }> {
  const res = await apiClient.get('/api/jobs', { params });
  return res.data;
}

// Matches API
export async function computeMatches(resumeId: string): Promise<ComputeMatchesSummary> {
  const res = await apiClient.post<ComputeMatchesSummary>(`/api/matches/compute/${resumeId}`);
  return res.data;
}

export async function getMatches(
  resumeId: string,
  params?: { min_score?: number; limit?: number; offset?: number },
  signal?: AbortSignal
): Promise<{ total: number; resume_id: string; limit: number; offset: number; results: MatchDetail[] }> {
  const res = await apiClient.get(`/api/matches/${resumeId}`, { params, signal });
  return res.data;
}

// Applications API
export async function runApplyBatch(
  resumeId: string,
  params?: { min_score?: number; limit?: number }
): Promise<ApplyBatchSummary> {
  const res = await apiClient.post<ApplyBatchSummary>(`/api/applications/run/${resumeId}`, null, {
    params,
  });
  return res.data;
}

export async function getApplications(params?: {
  status?: string;
  resume_id?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; limit: number; offset: number; results: ApplicationItem[] }> {
  const res = await apiClient.get('/api/applications', { params });
  return res.data;
}

export function getApplicationScreenshotUrl(applicationId: string): string {
  return `${API_BASE_URL}/api/applications/${applicationId}/screenshot`;
}

// Pipeline Autonomous Trigger
export async function triggerFullPipeline(
  resumeId: string,
  params?: { min_score?: number; limit?: number }
): Promise<PipelineRunResponse> {
  const res = await apiClient.post<PipelineRunResponse>(`/api/pipeline/run/${resumeId}`, null, {
    params,
  });
  return res.data;
}
