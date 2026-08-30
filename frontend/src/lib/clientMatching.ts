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
    posted_at: new Date(Date.now() - 3600 * 1000 * 6).toISOString(), // 6 hours ago
    description: 'Entry-level software engineering role in enterprise systems, writing robust Java backend services, database queries, and unit tests.',
  },
  {
    id: 'job-lever-02',
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
    posted_at: new Date(Date.now() - 3600 * 1000 * 12).toISOString(), // 12 hours ago
    description: 'Design and deploy predictive machine learning models and data pipelines for media recommendation and analytics.',
  },
  {
    id: 'job-blr-03',
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
    posted_at: new Date(Date.now() - 3600 * 1000 * 18).toISOString(), // 18 hours ago
    description: 'Work with the API platform ecosystem, building automated testing suites, developer docs, and REST API workflows.',
  },
  {
    id: 'job-gh-04',
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
    posted_at: new Date(Date.now() - 3600 * 1000 * 26).toISOString(), // 1 day ago
    description: 'Build mission-critical payment infrastructure, robust REST APIs, and scalable distributed backend systems using Java and Python.',
  },
  {
    id: 'job-mumbai-05',
    source: 'greenhouse',
    source_job_id: 'gh-6102',
    company: 'Oracle',
    title: 'Cloud Infrastructure Associate (OCI Foundations)',
    location: 'Mumbai, Maharashtra, India',
    country: 'India',
    workplace_type: 'Hybrid',
    experience_level: 'Fresher',
    apply_url: 'https://oracle.com/careers/6102',
    skills: ['Cloud Computing', 'Cloud Security', 'Oracle Cloud Infrastructure (OCI)', 'Linux', 'SQL', 'Git', 'GitHub'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 36).toISOString(), // 1.5 days ago
    description: 'Assist in managing cloud compute instances, virtual cloud networks (VCN), identity access management, and database storage on OCI.',
  },
  {
    id: 'job-lever-06',
    source: 'lever',
    source_job_id: 'lever-6542',
    company: 'Linear',
    title: 'Junior Software Engineer - Backend',
    location: 'Remote (Worldwide)',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://jobs.lever.co/linear/6542',
    skills: ['Java', 'Python', 'MySQL', 'OOP', 'Data Structures & Algorithms', 'REST API', 'Git', 'GitHub'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 48).toISOString(), // 2 days ago
    description: 'Develop high-performance backend microservices and maintain core data APIs with modern developer tooling.',
  },
  {
    id: 'job-gh-07',
    source: 'greenhouse',
    source_job_id: 'gh-7721',
    company: 'Notion',
    title: 'Full Stack Web Developer (React / JavaScript / PHP)',
    location: 'Remote / San Francisco, CA',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Junior',
    apply_url: 'https://boards.greenhouse.io/notion/jobs/7721',
    skills: ['JavaScript', 'HTML5', 'CSS3', 'React', 'PHP', 'WordPress', 'Plugin Integration', 'REST API'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 72).toISOString(), // 3 days ago
    description: 'Develop rich interactive web features, performant user interfaces, and custom integrations across our platform.',
  },
  {
    id: 'job-pune-08',
    source: 'greenhouse',
    source_job_id: 'gh-8840',
    company: 'Persistent Systems',
    title: 'Graduate Engineer Trainee - Java / Full Stack',
    location: 'Pune, Maharashtra, India',
    country: 'India',
    workplace_type: 'On-site',
    experience_level: 'Fresher',
    apply_url: 'https://persistentsystems.com/careers/8840',
    skills: ['Java', 'Core Java', 'Java Swing', 'Socket Programming', 'MySQL', 'OOP', 'HTML5', 'CSS'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 96).toISOString(), // 4 days ago
    description: 'Join our software engineering campus graduate cohort building core enterprise desktop and web solutions using Java and SQL.',
  },
  {
    id: 'job-gh-09',
    source: 'greenhouse',
    source_job_id: 'gh-3319',
    company: 'Airbnb',
    title: 'Cloud Systems & Infrastructure Engineer',
    location: 'Remote',
    country: 'Remote',
    workplace_type: 'Remote',
    experience_level: 'Mid',
    apply_url: 'https://boards.greenhouse.io/airbnb/jobs/3319',
    skills: ['Cloud Computing', 'Cloud Security', 'Oracle Cloud Infrastructure (OCI)', 'Docker', 'Linux', 'Git', 'GitHub', 'Python'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 120).toISOString(), // 5 days ago
    description: 'Scale cloud infrastructure, containerized deployments, and ensure enterprise-grade security and reliability.',
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
