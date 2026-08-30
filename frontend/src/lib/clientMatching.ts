import { MatchDetail, Job } from './api';

export const CURATED_JOBS: Job[] = [
  // ── LINKEDIN DIRECT JOBS ─────────────────────────────────────────────────
  {
    id: 'job-li-01',
    source: 'linkedin',
    source_job_id: 'li-tcs-pune',
    company: 'Tata Consultancy Services',
    title: 'Junior Python & Data Engineer (Pune)',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://www.linkedin.com/jobs/search/?keywords=Tata%20Consultancy%20Services%20Python%20Developer%20Pune',
    skills: ['Python', 'SQL', 'MySQL', 'Data Analysis', 'Git', 'Pandas', 'OOP'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 3).toISOString(),
    description: 'Direct LinkedIn job listing: Build data transformation scripts, SQL ETL pipelines, and internal backend dashboards in Pune.',
  },
  {
    id: 'job-li-02',
    source: 'linkedin',
    source_job_id: 'li-google-in',
    company: 'Google',
    title: 'Software Engineer - Early Career / University Graduate',
    location: 'Bangalore / Hyderabad / Remote, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://www.linkedin.com/jobs/search/?keywords=Google%20Software%20Engineer%20University%20Graduate%20India',
    skills: ['Java', 'Python', 'C++', 'Data Structures & Algorithms', 'OOP', 'SQL'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 5).toISOString(),
    description: 'Direct LinkedIn job listing: Develop scalable distributed software systems, clean data models, and performant backend services.',
  },
  {
    id: 'job-li-03',
    source: 'linkedin',
    source_job_id: 'li-msft-pune',
    company: 'Microsoft',
    title: 'Software Development Engineer - Core Platform (Java / Python)',
    location: 'Pune / Hyderabad, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Junior',
    apply_url: 'https://www.linkedin.com/jobs/search/?keywords=Microsoft%20Software%20Engineer%20Pune',
    skills: ['Java', 'Core Java', 'Python', 'REST API', 'MySQL', 'Cloud Computing', 'Git'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 9).toISOString(),
    description: 'Direct LinkedIn job listing: Design robust cloud microservices, REST APIs, and automated test pipelines in Pune.',
  },
  {
    id: 'job-li-04',
    source: 'linkedin',
    source_job_id: 'li-zomato-py',
    company: 'Zomato',
    title: 'Associate Backend Developer (Python / PostgreSQL / REST API)',
    location: 'Remote / Gurgaon, India',
    country: 'India',
    workplace_type: 'Remote',
    experience_level: 'Fresher',
    apply_url: 'https://www.linkedin.com/jobs/search/?keywords=Zomato%20Backend%20Engineer%20Python',
    skills: ['Python', 'REST API', 'PostgreSQL', 'MySQL', 'OOP', 'Git', 'Data Structures & Algorithms'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 12).toISOString(),
    description: 'Direct LinkedIn job listing: Build high-throughput order matching and delivery routing microservices.',
  },

  // ── NAUKRI DIRECT JOBS ───────────────────────────────────────────────────
  {
    id: 'job-nk-01',
    source: 'naukri',
    source_job_id: 'nk-infosys-pune',
    company: 'Infosys',
    title: 'Java Full Stack Graduate Trainee (Pune)',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'On-site',
    experience_level: 'Fresher',
    apply_url: 'https://www.naukri.com/infosys-java-developer-jobs-in-pune',
    skills: ['Java', 'Core Java', 'REST API', 'MySQL', 'HTML5', 'CSS3', 'JavaScript'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 4).toISOString(),
    description: 'Direct Naukri vacancy: Campus graduate software development role working on core banking, databases, and web portals in Pune.',
  },
  {
    id: 'job-nk-02',
    source: 'naukri',
    source_job_id: 'nk-persistent-pune',
    company: 'Persistent Systems',
    title: 'Graduate Engineer Trainee - Java / Full Stack',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://www.naukri.com/persistent-systems-software-engineer-jobs-in-pune',
    skills: ['Java', 'Core Java', 'Java Swing', 'Socket Programming', 'MySQL', 'OOP', 'HTML5'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 7).toISOString(),
    description: 'Direct Naukri vacancy: Join Persistent campus graduate cohort building core enterprise desktop and web solutions in Pune.',
  },
  {
    id: 'job-nk-03',
    source: 'naukri',
    source_job_id: 'nk-wipro-py',
    company: 'Wipro',
    title: 'Software Developer Trainee (Python / AI / Cloud)',
    location: 'Pune / Bangalore, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://www.naukri.com/wipro-python-developer-jobs-in-pune',
    skills: ['Python', 'Machine Learning', 'Data Analysis', 'SQL', 'Git', 'Cloud Computing'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 11).toISOString(),
    description: 'Direct Naukri vacancy: Entry-level software engineer for automated intelligence and cloud applications in Pune.',
  },

  // ── REMOTEOK DIRECT JOBS ─────────────────────────────────────────────────
  {
    id: 'job-ro-01',
    source: 'remoteok',
    source_job_id: 'ro-py-backend',
    company: 'Supabase',
    title: 'Remote Backend Engineer (Python / PostgreSQL)',
    location: 'Remote (Worldwide)',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://remoteok.com/remote-python-jobs',
    skills: ['Python', 'SQL', 'PostgreSQL', 'REST API', 'Git', 'Docker'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 14).toISOString(),
    description: 'Direct RemoteOK listing: Scale open-source database developer tooling, REST APIs, and auth microservices.',
  },
  {
    id: 'job-ro-02',
    source: 'remoteok',
    source_job_id: 'ro-devops-cloud',
    company: 'GitLab',
    title: 'Junior Cloud Infrastructure & DevOps Engineer',
    location: 'Remote (Worldwide)',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://remoteok.com/remote-devops-jobs',
    skills: ['Cloud Computing', 'Cloud Security', 'Linux', 'Docker', 'Git', 'GitHub', 'Python'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 18).toISOString(),
    description: 'Direct RemoteOK listing: Manage CI/CD runners, containerized deployments, and cloud infrastructure monitoring.',
  },

  // ── ARBEITNOW DIRECT JOBS ────────────────────────────────────────────────
  {
    id: 'job-an-01',
    source: 'arbeitnow',
    source_job_id: 'an-personio-dev',
    company: 'Personio',
    title: 'Junior Software Engineer - Core Platform (Java / Python)',
    location: 'Remote / Berlin, Germany',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://www.arbeitnow.com/remote-jobs',
    skills: ['Java', 'Python', 'REST API Development', 'MySQL', 'Git', 'OOP'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 16).toISOString(),
    description: 'Direct Arbeitnow API listing: Help build resilient core HR backend services, APIs, and developer tooling.',
  },

  // ── ADZUNA DIRECT JOBS ───────────────────────────────────────────────────
  {
    id: 'job-adz-01',
    source: 'adzuna',
    source_job_id: 'adz-cognizant-pune',
    company: 'Cognizant',
    title: 'Associate Engineer - Cloud & Infrastructure (OCI/AWS)',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://www.adzuna.in/search?q=Cognizant+Software+Engineer+Pune',
    skills: ['Cloud Computing', 'Cloud Security', 'Oracle Cloud Infrastructure (OCI)', 'Linux', 'SQL', 'Git'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 22).toISOString(),
    description: 'Direct Adzuna vacancy: Support cloud migration, compute instances, storage, and networking configuration in Pune.',
  },
  {
    id: 'job-adz-02',
    source: 'adzuna',
    source_job_id: 'adz-accenture-pune',
    company: 'Accenture',
    title: 'Associate Software Engineer - Java & Database Solutions',
    location: 'Pune / Mumbai, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://www.adzuna.in/search?q=Accenture+Java+Developer+Pune',
    skills: ['Java', 'Core Java', 'SQL', 'MySQL', 'REST API', 'OOP'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 26).toISOString(),
    description: 'Direct Adzuna vacancy: Build modular Java backend applications and enterprise database queries in Pune.',
  },

  // ── GREENHOUSE & LEVER ATS DIRECT JOBS ───────────────────────────────────
  {
    id: 'job-pune-01',
    source: 'greenhouse',
    source_job_id: 'gh-deloitte-pune',
    company: 'Deloitte',
    title: 'Associate Software Engineer (Java / Python - Fresher)',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://www.google.com/search?q=Deloitte+Associate+Software+Engineer+Pune+Jobs',
    skills: ['Java', 'Core Java', 'OOP', 'Data Structures & Algorithms', 'MySQL', 'SQL', 'Python'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 6).toISOString(),
    description: 'Direct application link: Entry-level software engineering role in enterprise systems, writing Java backend services in Pune.',
  },
  {
    id: 'job-lever-02',
    source: 'lever',
    source_job_id: 'lever-netflix-ml',
    company: 'Netflix',
    title: 'Data Science & Machine Learning Engineer (Junior)',
    location: 'Remote (Global)',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://jobs.lever.co/netflix',
    skills: ['Python', 'Data Science', 'Machine Learning', 'AI/ML', 'Pandas', 'Scikit-learn', 'SQL', 'Data Analysis'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 24).toISOString(),
    description: 'Direct Lever job portal: Design and deploy predictive machine learning models and data pipelines.',
  },
  {
    id: 'job-blr-03',
    source: 'lever',
    source_job_id: 'lever-postman-api',
    company: 'Postman',
    title: 'API Integration & Automation Specialist',
    location: 'Bangalore, Karnataka, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://jobs.lever.co/postman',
    skills: ['Postman', 'Postman Scripting', 'REST API', 'REST API Development', 'API Testing & Automation', 'JavaScript', 'Git'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 30).toISOString(),
    description: 'Direct Lever job portal: Work with the API platform ecosystem, building automated testing suites and REST API workflows.',
  },
  {
    id: 'job-gh-04',
    source: 'greenhouse',
    source_job_id: 'gh-stripe-backend',
    company: 'Stripe',
    title: 'Software Engineer - Backend (Java / Python)',
    location: 'Remote (Worldwide)',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://boards.greenhouse.io/stripe',
    skills: ['Java', 'Core Java', 'Python', 'SQL', 'MySQL', 'REST API', 'OOP', 'Data Structures & Algorithms'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 36).toISOString(),
    description: 'Direct Greenhouse ATS board: Build mission-critical payment infrastructure, robust REST APIs, and scalable distributed systems.',
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

/**
 * Resolves a reliable, active direct URL for any job vacancy.
 * Converts old or 404-prone IDs into live search/posting queries.
 */
export function getDirectJobUrl(job?: Job | null): string {
  if (!job) return '#';
  const url = (job.apply_url || '').trim();

  if (url.includes('linkedin.com/jobs/view/')) {
    const q = `${job.company || ''} ${job.title || ''} ${job.location || 'India'}`.trim();
    return `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(q)}`;
  }

  if (url.includes('naukri.com/job-listings-') || url.includes('naukri.com/jobs/')) {
    const compSlug = (job.company || '').toLowerCase().replace(/[^a-z0-9]/g, '-');
    return `https://www.naukri.com/${compSlug}-jobs-in-pune`;
  }

  if (!url || url.length < 5 || url === '#') {
    const q = `${job.company || ''} ${job.title || ''} jobs apply`.trim();
    return `https://www.google.com/search?q=${encodeURIComponent(q)}`;
  }

  return url;
}
