import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ResumePage } from './pages/ResumePage';
import { JobsPage } from './pages/JobsPage';
import { MatchesPage } from './pages/MatchesPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { getLatestResume } from './lib/api';

export const App: React.FC = () => {
  const [activeResumeId, setActiveResumeId] = useState<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem('autoapply_resume_id');
    if (saved) {
      setActiveResumeId(saved);
    } else {
      // Auto-discover the latest uploaded resume
      getLatestResume()
        .then((resume) => {
          if (resume && resume.id) {
            setActiveResumeId(resume.id);
            localStorage.setItem('autoapply_resume_id', resume.id);
          }
        })
        .catch(() => {
          // No resumes uploaded yet, perfectly normal
        });
    }
  }, []);

  const handleResumeUploaded = (id: string) => {
    setActiveResumeId(id);
    localStorage.setItem('autoapply_resume_id', id);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout activeResumeId={activeResumeId} />}>
          <Route index element={<Navigate to="/resume" replace />} />
          <Route
            path="resume"
            element={<ResumePage onResumeUploaded={handleResumeUploaded} />}
          />
          <Route path="jobs" element={<JobsPage />} />
          <Route
            path="matches"
            element={<MatchesPage resumeId={activeResumeId} />}
          />
          <Route
            path="applications"
            element={<ApplicationsPage resumeId={activeResumeId} />}
          />
          <Route path="*" element={<Navigate to="/resume" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
