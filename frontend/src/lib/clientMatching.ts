import { MatchDetail, Job, ParsedResume } from './api';

export const CURATED_JOBS: Job[] = [
  {
    id: 'job-gh-01',
    source: 'greenhouse',
    source_job_id: 'gh-49102',
    company: 'Stripe',
    title: 'Software Engineer - Backend (Java / Python)',
    location: 'Remote, US / Global',
    apply_url: 'https://boards.greenhouse.io/stripe/jobs/49102',
    skills: ['Java', 'Core Java', 'Python', 'SQL', 'MySQL', 'REST API', 'OOP', 'Data Structures & Algorithms'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 4).toISOString(),
    description: 'Build mission-critical payment infrastructure, robust REST APIs, and scalable distributed backend systems using Java and Python.',
  },
  {
    id: 'job-lever-02',
    source: 'lever',
    source_job_id: 'lever-8831',
    company: 'Netflix',
    title: 'Data Science & Machine Learning Engineer',
    location: 'Los Gatos, CA / Remote',
    apply_url: 'https://jobs.lever.co/netflix/8831',
    skills: ['Python', 'Data Science', 'Machine Learning', 'AI/ML', 'Pandas', 'Scikit-learn', 'SQL', 'Data Analysis'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 12).toISOString(),
    description: 'Design and deploy predictive machine learning models and data pipelines for media recommendation and analytics.',
  },
  {
    id: 'job-gh-03',
    source: 'greenhouse',
    source_job_id: 'gh-7721',
    company: 'Notion',
    title: 'Full Stack Web Developer (React / JavaScript / PHP)',
    location: 'San Francisco, CA / Remote',
    apply_url: 'https://boards.greenhouse.io/notion/jobs/7721',
    skills: ['JavaScript', 'HTML5', 'CSS3', 'React', 'PHP', 'WordPress', 'Plugin Integration', 'REST API'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 20).toISOString(),
    description: 'Develop rich interactive web features, performant user interfaces, and custom integrations across our platform.',
  },
  {
    id: 'job-lever-04',
    source: 'lever',
    source_job_id: 'lever-9104',
    company: 'Postman',
    title: 'API Integration & Automation Specialist',
    location: 'Bangalore, India / Remote',
    apply_url: 'https://jobs.lever.co/postman/9104',
    skills: ['Postman', 'Postman Scripting', 'REST API', 'REST API Development', 'API Testing & Automation', 'JavaScript', 'Git'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 24).toISOString(),
    description: 'Work with the API platform ecosystem, building automated testing suites, developer docs, and REST API workflows.',
  },
  {
    id: 'job-gh-05',
    source: 'greenhouse',
    source_job_id: 'gh-3319',
    company: 'Airbnb',
    title: 'Cloud Systems & Infrastructure Engineer',
    location: 'Remote',
    apply_url: 'https://boards.greenhouse.io/airbnb/jobs/3319',
    skills: ['Cloud Computing', 'Cloud Security', 'Oracle Cloud Infrastructure (OCI)', 'Docker', 'Linux', 'Git', 'GitHub', 'Python'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 30).toISOString(),
    description: 'Scale cloud infrastructure, containerized deployments, and ensure enterprise-grade security and reliability.',
  },
  {
    id: 'job-lever-06',
    source: 'lever',
    source_job_id: 'lever-6542',
    company: 'Linear',
    title: 'Junior Software Engineer - Backend',
    location: 'Remote (Worldwide)',
    apply_url: 'https://jobs.lever.co/linear/6542',
    skills: ['Java', 'Python', 'MySQL', 'OOP', 'Data Structures & Algorithms', 'REST API', 'Git', 'GitHub'],
    posted_at: new Date(Date.now() - 3600 * 1000 * 48).toISOString(),
    description: 'Develop high-performance backend microservices and maintain core data APIs with modern developer tooling.',
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
