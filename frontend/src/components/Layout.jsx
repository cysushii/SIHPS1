import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, LogOut, UserCheck } from 'lucide-react';

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-[#1a3a5c] text-white border-b border-[#234974] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <ShieldCheck className="h-8 w-8 text-[#0d9488]" />
          <div>
            <Link to="/" className="font-bold text-lg tracking-wide hover:text-gray-100 transition">
              AICTE Student Data Verification Platform
            </Link>
            <span className="block text-xs text-teal-300 font-medium tracking-wider uppercase">
              SIH26263 • APAAR ID Verification Slice
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <Link
            to="/verify-document"
            className="text-xs bg-slate-800 hover:bg-slate-700 text-teal-300 px-3 py-1.5 rounded border border-teal-500/30 font-medium transition"
          >
            Public Certificate Verifier
          </Link>

          {user ? (
            <div className="flex items-center space-x-3 border-l border-slate-600 pl-4 text-xs">
              <div className="text-right">
                <span className="block font-semibold text-gray-200">{user.username}</span>
                <span className="inline-block px-1.5 py-0.5 rounded bg-teal-800/80 text-teal-200 font-mono text-[10px]">
                  {user.role} {user.institute_id ? `(#${user.institute_id})` : ''}
                </span>
              </div>
              <button
                onClick={handleLogout}
                title="Logout"
                className="p-1.5 bg-rose-900/60 hover:bg-rose-800 text-rose-200 rounded transition"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="text-xs bg-[#0d9488] hover:bg-[#0f766e] text-white px-3 py-1.5 rounded font-semibold transition"
            >
              Sign In
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="bg-slate-900 text-slate-400 border-t border-slate-800 py-4 px-6 text-xs text-center">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
        <div>
          <span className="font-semibold text-slate-300">DEMO BUILD:</span> All student records and approval letters are synthetic for SIH evaluation.
        </div>
        <div className="text-slate-500 font-mono text-[11px]">
          All India Council for Technical Education (Demo) • Built for SIH26263
        </div>
      </div>
    </footer>
  );
}

export function StatusChip({ status }) {
  const map = {
    verified: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    approved: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    pending: 'bg-amber-100 text-amber-800 border-amber-300',
    pushed: 'bg-blue-100 text-blue-800 border-blue-300',
    under_review: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    draft: 'bg-slate-100 text-slate-700 border-slate-300',
    unresponsive: 'bg-purple-100 text-purple-800 border-purple-300',
    rejected: 'bg-rose-100 text-rose-800 border-rose-300',
    open: 'bg-amber-100 text-amber-800 border-amber-300',
    reviewed: 'bg-slate-100 text-slate-700 border-slate-300',
    confirmed: 'bg-rose-100 text-rose-800 border-rose-300',
    needs_review: 'bg-amber-100 text-amber-800 border-amber-300',
    critical: 'bg-red-200 text-red-900 border-red-400 font-bold',
    sent: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    skipped: 'bg-amber-50 text-amber-700 border-amber-200',
    failed: 'bg-rose-100 text-rose-800 border-rose-300',
  };

  const style = map[status?.toLowerCase()] || 'bg-gray-100 text-gray-800 border-gray-300';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${style}`}>
      {status || 'Unknown'}
    </span>
  );
}

