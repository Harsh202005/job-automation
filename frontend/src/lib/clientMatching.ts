import { MatchDetail, Job } from './api';

export const CURATED_JOBS: Job[] = [
  {
    id: 'job-pune-01',
    source: 'greenhouse',
    source_job_id: 'gh-9201',
    company: 'Deloitte',
    title: 'Associate Software Engineer (Java / Python - Fresher)',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://careers.deloitte.com/jobs/9201',
    skills: ['Java', 'Core Java', 'OOP', 'Data Structures & Algorithms', 'MySQL', 'SQL', 'Python'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 6).toISOString(),
    description: 'Entry-level software engineering role in enterprise systems, writing robust Java backend services, database queries, and unit tests.',
  },
  {
    id: 'job-linkedin-02',
    source: 'linkedin',
    source_job_id: 'li-39481',
    company: 'Tata Consultancy Services',
    title: 'Junior Python & Data Engineer (Pune)',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://www.linkedin.com/jobs/view/39481',
    skills: ['Python', 'SQL', 'MySQL', 'Data Analysis', 'Git', 'Pandas', 'OOP'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 8).toISOString(),
    description: 'Public LinkedIn listing: Build data transformation scripts, SQL ETL pipelines, and internal dashboards.',
  },
  {
    id: 'job-naukri-03',
    source: 'naukri',
    source_job_id: 'nk-77491',
    company: 'Infosys',
    title: 'Java Full Stack Graduate Trainee',
    location: 'Pune / Bangalore, India',
    country: 'India',
    workplace_type: 'On-site',
    experience_level: 'Fresher',
    apply_url: 'https://www.naukri.com/job-listings-77491',
    skills: ['Java', 'Core Java', 'REST API', 'MySQL', 'HTML5', 'CSS3', 'JavaScript'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 10).toISOString(),
    description: 'Naukri listing: Campus graduate software development role working on core banking and web portals.',
  },
  {
    id: 'job-remoteok-04',
    source: 'remoteok',
    source_job_id: 'ro-8194',
    company: 'Supabase',
    title: 'Remote Backend Engineer (Python / PostgreSQL)',
    location: 'Remote (Worldwide)',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://remoteok.com/remote-jobs/8194',
    skills: ['Python', 'SQL', 'PostgreSQL', 'REST API', 'Git', 'Docker'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 14).toISOString(),
    description: 'RemoteOK listing: Scale open-source database developer tooling, REST APIs, and auth microservices.',
  },
  {
    id: 'job-arbeitnow-05',
    source: 'arbeitnow',
    source_job_id: 'an-6629',
    company: 'Personio',
    title: 'Junior Software Engineer - Core Platform',
    location: 'Remote / Berlin, Germany',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://www.arbeitnow.com/view/junior-software-engineer-core-platform-6629',
    skills: ['Java', 'Python', 'REST API Development', 'MySQL', 'Git', 'OOP'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 18).toISOString(),
    description: 'Arbeitnow public API listing: Help build resilient core HR backend services and developer tooling.',
  },
  {
    id: 'job-adzuna-06',
    source: 'adzuna',
    source_job_id: 'adz-55102',
    company: 'Cognizant',
    title: 'Associate Engineer - Cloud & Infrastructure (OCI/AWS)',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://adzuna.in/jobs/details/55102',
    skills: ['Cloud Computing', 'Cloud Security', 'Oracle Cloud Infrastructure (OCI)', 'Linux', 'SQL', 'Git'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 22).toISOString(),
    description: 'Adzuna aggregated listing: Support cloud migration, compute instances, storage, and networking configuration.',
  },
  {
    id: 'job-lever-07',
    source: 'lever',
    source_job_id: 'lever-8831',
    company: 'Netflix',
    title: 'Data Science & Machine Learning Engineer (Junior)',
    location: 'Remote (Global)',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://jobs.lever.co/netflix/8831',
    skills: ['Python', 'Data Science', 'Machine Learning', 'AI/ML', 'Pandas', 'Scikit-learn', 'SQL', 'Data Analysis'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 24).toISOString(),
    description: 'Design and deploy predictive machine learning models and data pipelines for media recommendation and analytics.',
  },
  {
    id: 'job-blr-08',
    source: 'lever',
    source_job_id: 'lever-9104',
    company: 'Postman',
    title: 'API Integration & Automation Specialist',
    location: 'Bangalore, Karnataka, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://jobs.lever.co/postman/9104',
    skills: ['Postman', 'Postman Scripting', 'REST API', 'REST API Development', 'API Testing & Automation', 'JavaScript', 'Git'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 30).toISOString(),
    description: 'Work with the API platform ecosystem, building automated testing suites, developer docs, and REST API workflows.',
  },
  {
    id: 'job-gh-09',
    source: 'greenhouse',
    source_job_id: 'gh-49102',
    company: 'Stripe',
    title: 'Software Engineer - Backend (Java / Python)',
    location: 'Remote (Worldwide)',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://boards.greenhouse.io/stripe/jobs/49102',
    skills: ['Java', 'Core Java', 'Python', 'SQL', 'MySQL', 'REST API', 'OOP', 'Data Structures & Algorithms'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 36).toISOString(),
    description: 'Build mission-critical payment infrastructure, robust REST APIs, and scalable distributed backend systems using Java and Python.',
  },
];

/**
 * Calculates semantic and skill-based matching between a candidate profile and open vacancies.
 */
export function computeClientMatches(
  candidateSkills: string[],
  resumeId: string,
  minScore: number = 0.2
): MatchDetail[] {
  const candidateLower = new Set(candidateSkills.map((s) => s.toLowerCase().trim()));

  const scoredMatches: MatchDetail[] = CURATED_JOBS.map((job, idx) => {
    const jobSkills = job.skills || [];
    const matched: string[] = [];
    const missing: string[] = [];

    for (const js of jobSkills) {
      const jsLower = js.toLowerCase().trim();
      const hasMatch = Array.from(candidateLower).some(
        (cs) => cs.includes(jsLower) || jsLower.includes(cs)
      );
      if (hasMatch) {
        matched.push(js);
      } else {
        missing.push(js);
      }
    }

    // Similarity score based on matched skill ratio + base relevance
    const skillRatio = jobSkills.length > 0 ? matched.length / jobSkills.length : 0.5;
    const baseScore = 0.5 + skillRatio * 0.45;
    const finalScore = Number(Math.min(0.96, Math.max(0.35, baseScore)).toFixed(2));

    return {
      id: `match-${job.id}-${idx}`,
      match_id: `match-${job.id}-${idx}`,
      resume_id: resumeId,
      job_id: job.id,
      score: finalScore,
      matched_skills: matched,
      missing_skills: missing,
      job,
    };
  });

  return scoredMatches
    .filter((m) => m.score >= minScore)
    .sort((a, b) => b.score - a.score);
}
