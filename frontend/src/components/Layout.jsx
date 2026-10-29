import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getRoleLabel } from '../utils/formatters';
import { LogOut, CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react';

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleFontSize = (size) => {
    document.documentElement.classList.remove('font-size-sm', 'font-size-md', 'font-size-lg');
    document.documentElement.classList.add(`font-size-${size}`);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-slate-200">
      {/* Slim Teal Utility Bar */}
      <div className="bg-[#1b756b] text-white text-xs px-4 py-1.5 flex justify-between items-center max-w-7xl mx-auto">
        <div className="flex items-center space-x-3">
          <span className="font-medium tracking-wide">Vishwas • National Student Data Verification Platform</span>
          <span className="hidden sm:inline text-teal-200">|</span>
          <span className="hidden sm:inline text-[11px] text-teal-100">Helpline: support@sih26263.edu</span>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1 font-mono text-[11px]">
            <span className="text-teal-200 mr-1">Text Size:</span>
            <button
              onClick={() => handleFontSize('sm')}
              className="px-1.5 py-0.5 rounded bg-teal-800/60 hover:bg-teal-700 transition"
              title="Smaller font"
            >
              A-
            </button>
            <button
              onClick={() => handleFontSize('md')}
              className="px-1.5 py-0.5 rounded bg-teal-800/60 hover:bg-teal-700 transition"
              title="Default font"
            >
              A
            </button>
            <button
              onClick={() => handleFontSize('lg')}
              className="px-1.5 py-0.5 rounded bg-teal-800/60 hover:bg-teal-700 transition"
              title="Larger font"
            >
              A+
            </button>
          </div>
          <Link to="/help" className="hover:text-teal-200 flex items-center space-x-1">
            <HelpCircle className="h-3.5 w-3.5" />
            <span>Help</span>
          </Link>
        </div>
      </div>

      {/* Main Brand & Nav Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {/* Neutral modern placeholder brandmark */}
          <div className="h-10 px-3 rounded-lg bg-[#1b756b] flex items-center justify-center text-white font-bold text-base shadow-sm tracking-wide">
            VISHWAS
          </div>
          <div>
            <Link to="/" className="font-bold text-lg text-[#272727] tracking-tight hover:text-[#1b756b] transition">
              Vishwas • Student Data Verification Platform
            </Link>
            <span className="block text-[11px] text-[#1b756b] font-medium tracking-wide">
              APAAR ID Integration for Technical Institutions
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <Link
            to="/verify-document"
            className="text-xs bg-[#f0fdf5] hover:bg-[#d7f9e4] text-[#1b756b] px-3 py-1.5 rounded-lg border border-[#1b756b]/30 font-semibold transition"
          >
            Public Certificate Verifier
          </Link>

          {user ? (
            <div className="flex items-center space-x-3 border-l border-slate-200 pl-4 text-xs">
              <div className="text-right">
                <span className="block font-semibold text-[#272727]">{user.full_name || user.email}</span>
                <span className="inline-block px-1.5 py-0.2 rounded bg-purple-50 text-[#8177f1] font-medium text-[10px]">
                  {getRoleLabel(user.role)} {user.institute_name ? `• ${user.institute_name}` : ''}
                </span>
              </div>
              <button
                onClick={handleLogout}
                title="Sign out"
                className="p-1.5 bg-slate-100 hover:bg-rose-50 hover:text-rose-600 text-slate-600 rounded-lg transition"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="text-xs bg-[#1b756b] hover:bg-[#145952] text-white px-3.5 py-1.5 rounded-lg font-semibold shadow-sm transition"
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
    <footer className="bg-white text-slate-500 border-t border-slate-200 py-5 px-6 text-xs text-center mt-auto">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="text-slate-600 font-medium">
          Prototype built for SIH26263. Not an official Government of India service.
        </div>
        <div className="text-slate-400 text-[11px]">
          Vishwas • APAAR ID-Based Student Data Verification Platform
        </div>
      </div>
    </footer>
  );
}

export function StatusChip({ status, label }) {
  const map = {
    verified: 'bg-emerald-50 text-emerald-800 border-emerald-300',
    approved: 'bg-emerald-50 text-emerald-800 border-emerald-300',
    cleared: 'bg-emerald-50 text-emerald-800 border-emerald-300',
    sent: 'bg-emerald-50 text-emerald-800 border-emerald-300',
    sent_test_mode: 'bg-amber-50 text-amber-800 border-amber-300',
    pending: 'bg-amber-50 text-amber-800 border-amber-300',
    pushed: 'bg-blue-50 text-blue-800 border-blue-300',
    awaiting_review: 'bg-indigo-50 text-indigo-800 border-indigo-300',
    under_review: 'bg-indigo-50 text-indigo-800 border-indigo-300',
    draft: 'bg-slate-100 text-slate-700 border-slate-300',
    correction_requested: 'bg-amber-50 text-amber-800 border-amber-300',
    unresponsive: 'bg-purple-50 text-purple-800 border-purple-300',
    needs_review: 'bg-amber-50 text-amber-800 border-amber-300',
    blocked: 'bg-rose-50 text-rose-800 border-rose-300 font-semibold',
    rejected: 'bg-rose-50 text-rose-800 border-rose-300',
    failed: 'bg-rose-50 text-rose-800 border-rose-300',
    critical: 'bg-red-100 text-red-900 border-red-400 font-bold',
    returned: 'bg-amber-50 text-amber-800 border-amber-300',
  };

  const style = map[status?.toLowerCase()] || 'bg-slate-100 text-slate-800 border-slate-300';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${style}`}>
      {label || status || 'Unknown'}
    </span>
  );
}

export function EmailServiceChip({ statusData }) {
  if (!statusData) return null;

  const isConnected = statusData.status === 'Connected';
  const isError = statusData.status === 'Error';

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <div
        className={`inline-flex items-center px-2.5 py-1 rounded-md border font-medium ${
          isConnected
            ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
            : isError
            ? 'bg-rose-50 text-rose-800 border-rose-300'
            : 'bg-slate-100 text-slate-700 border-slate-300'
        }`}
      >
        <span
          className={`h-2 w-2 rounded-full mr-1.5 ${
            isConnected ? 'bg-emerald-500' : isError ? 'bg-rose-500' : 'bg-slate-400'
          }`}
        />
        <span>Email Service: {statusData.status}</span>
        {isConnected && <span className="text-[10px] text-emerald-600 ml-1">({statusData.provider})</span>}
      </div>

      {statusData.test_mode && (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-amber-50 text-amber-800 border border-amber-300 font-medium">
          Test Mode: All emails routed to {statusData.test_redirect_masked}
        </span>
      )}
    </div>
  );
}
