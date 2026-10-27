import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/api';
import { Header, Footer } from '../components/Layout';
import { ShieldCheck, School, Building2, UserCheck, KeyRound } from 'lucide-react';

export function Login() {
  const [username, setUsername] = useState('demo_admin');
  const [role, setRole] = useState('institute_admin');
  const [instituteId, setInstituteId] = useState(1);
  const [institutesList, setInstitutesList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    async function loadInstitutes() {
      try {
        const res = await authApi.getInstitutesList();
        if (res && res.institutes) {
          setInstitutesList(res.institutes);
        }
      } catch (err) {
        console.error('Failed to load institute list:', err);
      }
    }
    loadInstitutes();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(username, role, role === 'institute_admin' ? Number(instituteId) : null);
      if (role === 'institute_admin') {
        navigate('/institute/dashboard');
      } else if (role === 'aicte_admin') {
        navigate('/aicte/overview');
      } else {
        navigate('/verify-document');
      }
    } catch (err) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleInstituteSelect = (id) => {
    setInstituteId(id);
    const found = institutesList.find((i) => i.id === Number(id));
    if (found) {
      setUsername(`admin_${found.name.toLowerCase().replace(/[^a-z0-9]/g, '_').slice(0, 15)}`);
    }
  };

  const setPreset = (userRole, userInstituteId, userLabel) => {
    setRole(userRole);
    setInstituteId(userInstituteId || 1);
    setUsername(userLabel);
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50">
      <Header />
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg border border-slate-200 p-8">
          <div className="text-center mb-6">
            <div className="inline-flex p-3 bg-teal-50 rounded-full border border-teal-200 mb-3 text-[#0d9488]">
              <ShieldCheck className="h-8 w-8" />
            </div>
            <h2 className="text-2xl font-bold text-[#1a3a5c]">Sign In</h2>
            <p className="text-xs text-slate-500 mt-1">
              Select a pre-configured demo persona or enter credentials
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded border border-red-200">
              {error}
            </div>
          )}

          {/* Quick Persona Switcher for Hackathon Judges */}
          <div className="mb-6 bg-slate-50 p-3 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-2">
              Demo Personas (1-Click)
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setPreset('institute_admin', 1, 'institute_iit_delhi')}
                className={`p-2 rounded text-left border transition text-xs ${
                  role === 'institute_admin' && instituteId === 1
                    ? 'border-[#0d9488] bg-teal-50 text-[#1a3a5c] font-semibold'
                    : 'border-slate-200 hover:bg-white text-slate-600'
                }`}
              >
                <School className="h-4 w-4 mb-1 text-[#0d9488]" />
                <div className="font-medium text-[11px]">Institute #1</div>
                <div className="text-[10px] text-slate-400">Regular EOA</div>
              </button>

              <button
                type="button"
                onClick={() => setPreset('institute_admin', 2, 'institute_velagapudi')}
                className={`p-2 rounded text-left border transition text-xs ${
                  role === 'institute_admin' && instituteId === 2
                    ? 'border-[#0d9488] bg-teal-50 text-[#1a3a5c] font-semibold'
                    : 'border-slate-200 hover:bg-white text-slate-600'
                }`}
              >
                <School className="h-4 w-4 mb-1 text-indigo-600" />
                <div className="font-medium text-[11px]">Institute #2</div>
                <div className="text-[10px] text-slate-400">Extended EOA</div>
              </button>

              <button
                type="button"
                onClick={() => setPreset('aicte_admin', null, 'aicte_central_admin')}
                className={`p-2 rounded text-left border transition text-xs ${
                  role === 'aicte_admin'
                    ? 'border-[#0d9488] bg-teal-50 text-[#1a3a5c] font-semibold'
                    : 'border-slate-200 hover:bg-white text-slate-600'
                }`}
              >
                <Building2 className="h-4 w-4 mb-1 text-[#1a3a5c]" />
                <div className="font-medium text-[11px]">AICTE Admin</div>
                <div className="text-[10px] text-slate-400">Regulator HQ</div>
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Username / Identifier
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0d9488] focus:border-transparent outline-none transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0d9488] focus:border-transparent outline-none transition bg-white"
              >
                <option value="institute_admin">Institute Admin</option>
                <option value="aicte_admin">AICTE Admin</option>
                <option value="verifier">Public Verifier</option>
              </select>
            </div>

            {role === 'institute_admin' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  Select Registered Institution
                </label>
                {institutesList.length > 0 ? (
                  <select
                    value={instituteId}
                    onChange={(e) => handleInstituteSelect(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0d9488] bg-white outline-none"
                  >
                    {institutesList.map((inst) => (
                      <option key={inst.id} value={inst.id}>
                        #{inst.id} — {inst.name} ({inst.state}) [{inst.aicte_code}]
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    min="1"
                    required
                    value={instituteId}
                    onChange={(e) => setInstituteId(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0d9488] focus:border-transparent outline-none transition"
                  />
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-[#1a3a5c] hover:bg-[#122942] text-white py-2.5 rounded-lg text-sm font-semibold shadow transition disabled:opacity-50"
            >
              {loading ? 'Authenticating...' : 'Sign In to Portal'}
            </button>
          </form>
        </div>
      </div>
      <Footer />
    </div>
  );
}

