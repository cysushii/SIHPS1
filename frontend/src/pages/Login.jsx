import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Header, Footer } from '../components/Layout';
import { Lock, Mail, ArrowRight, ShieldCheck } from 'lucide-react';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await login(email.trim(), password);
      if (data.role === 'institute_admin') {
        navigate('/institute/dashboard');
      } else if (data.role === 'aicte_admin') {
        navigate('/aicte/overview');
      } else {
        navigate('/verify-document');
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50">
      <Header />

      <main className="flex-1 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
          <div className="text-center mb-6">
            <div className="inline-flex p-3 bg-[#d7f9e4] rounded-xl text-[#1b756b] mb-3">
              <ShieldCheck className="h-8 w-8" />
            </div>
            <h2 className="text-2xl font-bold text-[#272727]">Portal Sign In</h2>
            <p className="text-xs text-slate-500 mt-1">
              Sign in with your administrator credentials
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-rose-50 text-rose-700 text-xs rounded-lg border border-rose-200">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Registered Email Address
              </label>
              <div className="relative">
                <Mail className="h-4 w-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  placeholder="admin@aicte.gov.in"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#1b756b] focus:border-transparent outline-none transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="h-4 w-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#1b756b] focus:border-transparent outline-none transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-[#1b756b] hover:bg-[#145952] text-white py-2.5 rounded-lg text-sm font-semibold shadow-sm transition disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In'}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-slate-100 text-[11px] text-slate-500 text-center">
            Accounts are provisioned by the AICTE Regulatory Desk or via CLI management.
          </div>

          {/* Static Preview Quick Demo Access */}
          <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-200 text-center">
            <span className="block text-[11px] font-semibold text-slate-600 mb-2">
              Preview Mode — Click to Explore Dashboards:
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  const demoInstituteUser = {
                    token: 'demo-preview-token',
                    role: 'institute_admin',
                    institute_id: 1,
                    institute_name: 'L M Thapar School Of Management',
                    email: 'principal@example.com',
                    full_name: 'Institute Administrator',
                  };
                  localStorage.setItem('token', demoInstituteUser.token);
                  localStorage.setItem('role', demoInstituteUser.role);
                  localStorage.setItem('institute_id', String(demoInstituteUser.institute_id));
                  localStorage.setItem('institute_name', demoInstituteUser.institute_name);
                  localStorage.setItem('email', demoInstituteUser.email);
                  localStorage.setItem('full_name', demoInstituteUser.full_name);
                  window.location.href = `${import.meta.env.BASE_URL}institute/dashboard`;
                }}
                className="flex-1 py-1.5 px-2 bg-white hover:bg-teal-50 hover:text-[#1b756b] border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 transition shadow-xs"
              >
                🏫 Institute Portal
              </button>
              <button
                type="button"
                onClick={() => {
                  const demoAicteUser = {
                    token: 'demo-preview-token',
                    role: 'aicte_admin',
                    institute_id: null,
                    institute_name: '',
                    email: 'admin@example.com',
                    full_name: 'AICTE Administrator',
                  };
                  localStorage.setItem('token', demoAicteUser.token);
                  localStorage.setItem('role', demoAicteUser.role);
                  localStorage.removeItem('institute_id');
                  localStorage.removeItem('institute_name');
                  localStorage.setItem('email', demoAicteUser.email);
                  localStorage.setItem('full_name', demoAicteUser.full_name);
                  window.location.href = `${import.meta.env.BASE_URL}aicte/overview`;
                }}
                className="flex-1 py-1.5 px-2 bg-white hover:bg-teal-50 hover:text-[#1b756b] border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 transition shadow-xs"
              >
                🏛️ AICTE Portal
              </button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
