import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { FileText, Briefcase, Sparkles, Send, Bot, CheckCircle2, AlertCircle } from 'lucide-react';

interface LayoutProps {
  activeResumeId: string | null;
}

export const Layout: React.FC<LayoutProps> = ({ activeResumeId }) => {
  const location = useLocation();

  const navItems = [
    { to: '/resume', label: 'Resume', icon: FileText },
    { to: '/jobs', label: 'Jobs', icon: Briefcase },
    { to: '/matches', label: 'Matches', icon: Sparkles },
    { to: '/applications', label: 'Applications', icon: Send },
  ];

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/70 backdrop-blur-md flex flex-col shrink-0">
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-slate-100 tracking-tight flex items-center gap-1.5">
              AutoApply
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                v0.4
              </span>
            </h1>
            <p className="text-xs text-slate-400">Job Automation Tool</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1.5 flex-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.to;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-500 text-slate-950 font-semibold shadow-lg shadow-emerald-500/20'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-slate-950' : 'text-slate-400'}`} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Active Resume Indicator Widget */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/40">
          <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/60 text-xs">
            <div className="flex items-center gap-2 mb-1 text-slate-300 font-medium">
              {activeResumeId ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span className="truncate">Active Resume Loaded</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span>No Active Resume</span>
                </>
              )}
            </div>
            {activeResumeId ? (
              <p className="text-[11px] text-slate-500 font-mono truncate">ID: {activeResumeId}</p>
            ) : (
              <p className="text-[11px] text-slate-400">Upload a resume to enable match scoring & auto-apply.</p>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main Content Area ────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 border-b border-slate-800 bg-slate-900/30 backdrop-blur-md px-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Section</span>
            <span className="text-slate-600">/</span>
            <span className="text-sm font-medium text-slate-200 capitalize">
              {location.pathname.replace('/', '') || 'Dashboard'}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              FastAPI Backend Connected
            </span>
          </div>
        </header>

        {/* Dynamic Page Outlet */}
        <main className="flex-1 p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
