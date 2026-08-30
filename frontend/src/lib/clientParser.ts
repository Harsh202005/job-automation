import { ParsedResume, ExperienceItem, EducationItem, ProjectItem, CertificationItem } from './api';
import * as pdfjsLib from 'pdfjs-dist';

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

const TECHNICAL_SKILLS_DICTIONARY = [
  'Python', 'Java', 'Core Java', 'Java Swing', 'AWT', 'Socket Programming', 'OOP', 'Object Oriented Programming',
  'Data Structures', 'Algorithms', 'Data Structures & Algorithms', 'C', 'C++', 'C#', 'JavaScript', 'TypeScript',
  'HTML', 'HTML5', 'CSS', 'CSS3', 'PHP', 'WordPress', 'Plugin Integration', 'React', 'Next.js', 'Node.js',
  'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'FastAPI', 'Django', 'Flask', 'Spring Boot',
  'Data Science', 'Data Analysis', 'Machine Learning', 'AI/ML', 'Pandas', 'Scikit-learn', 'NumPy', 'TensorFlow', 'PyTorch',
  'REST API', 'REST API Development', 'API Testing', 'API Testing & Automation', 'Postman', 'Postman Scripting',
  'Cloud Computing', 'Cloud Security', 'Oracle Cloud Infrastructure (OCI)', 'Oracle Cloud Infrastructure',
  'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Git', 'GitHub', 'Linux'
];

/**
 * Extracts raw text from a PDF file using PDF.js.
 */
export async function extractPdfTextInBrowser(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const loadingTask = pdfjsLib.getDocument({ data: new Uint8Array(arrayBuffer) });
  const pdfDoc = await loadingTask.promise;

  const pageTexts: string[] = [];

  for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
    const page = await pdfDoc.getPage(pageNum);
    const textContent = await page.getTextContent();
    
    const lineMap: { [y: number]: string[] } = {};

    for (const item of textContent.items as any[]) {
      if (!item.str) continue;
      const y = Math.round(item.transform[5]);
      if (!lineMap[y]) {
        lineMap[y] = [];
      }
      lineMap[y].push(item.str);
    }

    const sortedY = Object.keys(lineMap)
      .map(Number)
      .sort((a, b) => b - a);

    const pageLines = sortedY.map((y) => lineMap[y].join(' ').trim()).filter(Boolean);
    pageTexts.push(pageLines.join('\n'));
  }

  return pageTexts.join('\n\n');
}

/**
 * Fully dynamic, generic resume parser with zero hardcoded personal fallbacks.
 */
export function parseResumeText(text: string, filename: string): ParsedResume {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  const fullText = text;

  // ── 1. Dynamic Contact Information ─────────────────────────────────────────
  const emailMatch = fullText.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
  const email = emailMatch ? emailMatch[0] : '';

  const phoneMatch = fullText.match(/(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}|\+?91[\s-]?[6-9]\d{9}/);
  const phone = phoneMatch ? phoneMatch[0] : '';

  // ── 2. Dynamic Candidate Name ──────────────────────────────────────────────
  let full_name = 'Candidate Profile';
  for (let i = 0; i < Math.min(lines.length, 8); i++) {
    let line = lines[i];
    if (
      line.includes('@') ||
      line.includes('+') ||
      line.includes('http') ||
      /resume|cv|curriculum|phone|email|page/i.test(line)
    ) {
      continue;
    }
    line = line.replace(/^(TITLE|NAME|CANDIDATE|CV|RESUME)[:\s]+/i, '').trim();
    const words = line.replace(/[^a-zA-Z\s]/g, '').trim().split(/\s+/);
    if (words.length >= 2 && words.length <= 4 && words.every((w) => w.length > 1)) {
      full_name = words.join(' ').toUpperCase();
      break;
    }
  }

  // ── 3. Dynamic Summary ─────────────────────────────────────────────────────
  let summary = '';
  const summaryMatch = fullText.match(/(?:BRIEF\s+SUMMARY|SUMMARY|PROFILE|OBJECTIVE|ABOUT\s+ME)\s*\n+([\s\S]+?)(?=\n+[A-Z\s/&]{4,}\b|\Z)/i);
  if (summaryMatch) {
    summary = summaryMatch[1].replace(/\s+/g, ' ').trim();
  }

  // ── 4. Dynamic Skills Extraction ───────────────────────────────────────────
  const extractedSkills: string[] = [];
  const seenSkills = new Set<string>();

  const addSkill = (s: string) => {
    const clean = s.trim().replace(/^[^a-zA-Z0-9+#]+|[^a-zA-Z0-9+#]+$/g, '');
    const lower = clean.toLowerCase();
    if (clean.length >= 2 && !seenSkills.has(lower) && clean.length <= 40) {
      seenSkills.add(lower);
      extractedSkills.push(clean);
    }
  };

  // 'Key Skills:' lines
  const keySkillMatches = fullText.match(/Key Skills:\s*([^\n\r]+)/gi);
  if (keySkillMatches) {
    for (const line of keySkillMatches) {
      const parts = line.replace(/Key Skills:\s*/i, '').split(/[,•|;]|\s{2,}/);
      for (const p of parts) {
        if (p.trim()) addSkill(p.trim());
      }
    }
  }

  // Technical skills dictionary matching
  const lowerFull = ` ${fullText.toLowerCase()} `;
  for (const sk of TECHNICAL_SKILLS_DICTIONARY) {
    const regex = new RegExp(`\\b${sk.toLowerCase().replace('+', '\\+').replace('&', '&')}\\b`, 'i');
    if (regex.test(lowerFull)) {
      addSkill(sk);
    }
  }

  // ── 5. Dynamic Section Splitter ────────────────────────────────────────────
  const sections: { [k: string]: string } = {};
  const parts = fullText.split(/\n+([A-Z\s/&]{4,})\n+/);
  if (parts.length > 1) {
    for (let i = 1; i < parts.length; i += 2) {
      const secName = parts[i].trim().toUpperCase();
      const secBody = parts[i + 1] ? parts[i + 1].trim() : '';
      sections[secName] = secBody;
    }
  }

  // ── 6. Dynamic Experience & Internships ────────────────────────────────────
  const experience: ExperienceItem[] = [];
  let expBody = '';
  for (const k of Object.keys(sections)) {
    if (/EXPERIENCE|INTERNSHIP|EMPLOYMENT|WORK/.test(k)) {
      expBody = sections[k];
      break;
    }
  }

  const datePattern = /(?:\d{1,2}\s+[A-Za-z]+,?\s+\d{4}\s*[-–—to]+\s*(?:\d{1,2}\s+[A-Za-z]+,?\s+\d{4}|Present|Current)|\b(?:19|20)\d{2}\s*[-–—to]+\s*(?:(?:19|20)\d{2}|Present|Current))/i;

  if (expBody) {
    const blocks = expBody.split(/\n(?=[A-Za-z0-9\s.,&-]+\||\b[A-Z][a-zA-Z\s.,&]+(?:Pvt|Ltd|Inc|LLC|Solutions|Media|Company|Technologies|Corp)\b)/);
    for (const b of blocks) {
      const bLines = b.split('\n').map((l) => l.trim()).filter(Boolean);
      if (!bLines.length) continue;

      const durMatch = b.match(datePattern);
      const duration = durMatch ? durMatch[0] : '';
      const header = bLines[0];
      const company = header.replace(datePattern, '').split('|')[0].trim();
      let title = bLines.length > 1 && !/Key Skills:/i.test(bLines[1])
        ? bLines[1]
        : (header.includes('|') ? header.split('|')[1].trim() : 'Developer / Intern');
      title = title.replace(datePattern, '').trim();

      const descLines = bLines.slice(2).filter((l) => !/Key Skills:/i.test(l));

      if (company || title) {
        experience.push({
          company: company || 'Company',
          title: title || 'Role',
          duration,
          description: descLines.join(' '),
        });
      }
    }
  }

  // ── 7. Dynamic Education ───────────────────────────────────────────────────
  const education: EducationItem[] = [];
  let eduBody = '';
  for (const k of Object.keys(sections)) {
    if (/EDUCATION|ACADEMIC/.test(k)) {
      eduBody = sections[k];
      break;
    }
  }

  if (eduBody) {
    const eduLines = eduBody.split('\n').map((l) => l.trim()).filter(Boolean);
    let i = 0;
    while (i < eduLines.length) {
      const line = eduLines[i];
      if (/college|institute|university|school|polytechnic|academy/i.test(line)) {
        const yearMatches = line.match(/\b(?:19|20)\d{2}\b/g) || [];
        const nextLine = eduLines[i + 1] || '';
        const allYearMatches = (line + ' ' + nextLine).match(/\b(?:19|20)\d{2}\b/g) || [];
        const year = allYearMatches.length ? allYearMatches[allYearMatches.length - 1] : '';

        const inst = line.replace(/\b(?:19|20)\d{2}\b.*/g, '').replace(/[-–|]/g, '').trim();
        const deg = nextLine ? nextLine.split('|')[0].replace(/CGPA.*/i, '').replace(/Percentage.*/i, '').trim() : inst;

        education.push({
          institution: inst || line,
          degree: deg || 'Degree / Diploma',
          year,
        });
        i += 2;
      } else {
        i += 1;
      }
    }
  }

  // ── 8. Dynamic Featured Projects ───────────────────────────────────────────
  const projects: ProjectItem[] = [];
  let projBody = '';
  for (const k of Object.keys(sections)) {
    if (/PROJECT/.test(k)) {
      projBody = sections[k];
      break;
    }
  }

  if (projBody) {
    const projBlocks = projBody.split(/\n(?=[A-Z][a-zA-Z0-9\s-]{3,}(?:\d{2}\s+[A-Za-z]{3}|\bProject\b|\bApp\b|\bSystem\b|\bPlatform\b))/);
    for (const pb of projBlocks) {
      const pLines = pb.split('\n').map((l) => l.trim()).filter(Boolean);
      if (!pLines.length) continue;

      const linkMatch = pb.match(/https?:\/\/[^\s]+/);
      const link = linkMatch ? linkMatch[0] : '';

      const durMatch = pb.match(datePattern);
      const duration = durMatch ? durMatch[0] : '';

      let title = pLines[0].replace(/https?:\/\/[^\s]+/, '').trim();
      if (durMatch) title = title.replace(durMatch[0], '').trim();

      const skillsMatch = pb.match(/Key Skills:\s*([^\n\r]+)/i);
      const pSkills = skillsMatch
        ? skillsMatch[1].split(/[,•|;]|\s{2,}/).map((s) => s.trim()).filter((s) => s.length > 1)
        : [];

      const descLines = pLines.slice(1).filter(
        (l) => !l.startsWith('Key Skills:') && !l.startsWith('Project Link:') && !l.startsWith('Team Size:')
      );

      if (title) {
        projects.push({
          title,
          link,
          duration,
          skills: pSkills,
          description: descLines.join(' '),
        });
      }
    }
  }

  // ── 9. Dynamic Assessments & Certifications ────────────────────────────────
  const certifications: CertificationItem[] = [];
  let certBody = '';
  for (const k of Object.keys(sections)) {
    if (/CERTIF|ASSESS/.test(k)) {
      certBody = sections[k];
      break;
    }
  }

  if (certBody) {
    const certBlocks = certBody.split(/\n(?=[A-Z][a-zA-Z0-9\s-]{4,}(?:Certified|Expert|Associate|Certificate|Specialist|\nKey Skills:))/);
    for (const cb of certBlocks) {
      const cLines = cb.split('\n').map((l) => l.trim()).filter(Boolean);
      if (!cLines.length) continue;

      const cName = cLines[0];
      const skillsMatch = cb.match(/Key Skills:\s*([^\n\r]+)/i);
      const cSkills = skillsMatch
        ? skillsMatch[1].split(/[,•|;]|\s{2,}/).map((s) => s.trim()).filter((s) => s.length > 1)
        : [];

      const descLines = cLines.slice(1).filter((l) => !l.startsWith('Key Skills:'));

      let issuer = 'Certification';
      if (/Oracle/i.test(cName)) issuer = 'Oracle';
      else if (/Postman/i.test(cName)) issuer = 'Postman';
      else if (/AWS/i.test(cName)) issuer = 'AWS';
      else if (/Google/i.test(cName)) issuer = 'Google';
      else if (/Microsoft/i.test(cName)) issuer = 'Microsoft';

      if (cName) {
        certifications.push({
          name: cName,
          issuer,
          skills: cSkills,
          description: descLines.join(' '),
        });
      }
    }
  }

  return {
    id: `resume-${Date.now()}`,
    filename,
    full_name,
    email,
    phone,
    summary,
    skills: extractedSkills,
    experience,
    education,
    projects,
    certifications,
    total_experience_years: experience.length > 0 ? Number((experience.length * 0.3).toFixed(1)) : 0.0,
    parse_warnings: [],
  };
}
