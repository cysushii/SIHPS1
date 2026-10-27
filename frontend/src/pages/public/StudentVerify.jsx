import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { publicApi } from '../../api/api';
import { ShieldCheck, CheckCircle2, AlertCircle, Edit3, ArrowRight } from 'lucide-react';

export function StudentVerify() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Correction Mode
  const [showCorrectionForm, setShowCorrectionForm] = useState(false);
  const [corrections, setCorrections] = useState({
    name: '',
    program: '',
    enrollment_year: '',
    notes: '',
  });

  useEffect(() => {
    async function fetchTokenDetails() {
      try {
        setLoading(true);
        const res = await publicApi.getTokenDetails(token);
        setData(res);
      } catch (err) {
        setError(err.message || 'Invalid or expired verification link.');
      } finally {
        setLoading(false);
      }
    }
    fetchTokenDetails();
  }, [token]);

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      await publicApi.confirmToken(token);
      setConfirmed(true);
    } catch (err) {
      alert(err.message || 'Failed to confirm record.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCorrectionSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await publicApi.correctToken(token, corrections);
      setConfirmed(true);
    } catch (err) {
      alert(err.message || 'Failed to submit corrections.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="text-center text-xs text-slate-500">Loading student record details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white p-8 rounded-xl shadow-md border border-slate-200 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-slate-800">Verification Link Unavailable</h2>
          <p className="text-xs text-slate-500">{error}</p>
          <Link
            to="/login"
            className="inline-block text-xs font-semibold text-teal-600 hover:text-teal-800"
          >
            Go to Platform Login
          </Link>
        </div>
      </div>
    );
  }

  if (confirmed) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white p-8 rounded-xl shadow-md border border-slate-200 text-center space-y-4">
          <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto" />
          <h2 className="text-xl font-bold text-[#1a3a5c]">Record Successfully Verified!</h2>
          <p className="text-xs text-slate-600">
            Thank you for confirming your academic enrollment data. Your response has been securely logged to the immutable audit trail.
          </p>
          <div className="p-3 bg-slate-50 rounded text-slate-500 text-[11px] font-mono">
            Status: Confirmed / Logged
          </div>
        </div>
      </div>
    );
  }

  const { student } = data;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      {/* Official banner */}
      <header className="bg-[#1a3a5c] text-white py-4 px-6 shadow-sm">
        <div className="max-w-md mx-auto flex items-center space-x-2">
          <ShieldCheck className="h-6 w-6 text-[#0d9488]" />
          <div>
            <h1 className="font-bold text-sm tracking-wide">AICTE National Student Registry</h1>
            <span className="block text-[10px] text-teal-300">Self-Verification Portal (DEMO)</span>
          </div>
        </div>
      </header>

      <div className="flex-1 max-w-md w-full mx-auto p-4 flex items-center">
        <div className="w-full bg-white rounded-xl shadow-md border border-slate-200 p-6 space-y-6">
          <div>
            <span className="text-[10px] font-semibold tracking-wider text-teal-600 uppercase bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
              Action Required
            </span>
            <h2 className="text-lg font-bold text-[#1a3a5c] mt-2">Confirm Your Student Details</h2>
            <p className="text-xs text-slate-500 mt-1">
              Please inspect the academic details submitted by your institution below.
            </p>
          </div>

          {/* Student Record Card */}
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 space-y-3 text-xs">
            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">Student Name:</span>
              <span className="font-semibold text-slate-800">{student?.name}</span>
            </div>
            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">Masked APAAR ID:</span>
              <span className="font-mono font-bold text-teal-700">{student?.apaar_id_masked}</span>
            </div>
            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">Institution:</span>
              <span className="font-semibold text-slate-800 text-right">{student?.institute}</span>
            </div>
            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">Programme:</span>
              <span className="font-semibold text-slate-800 text-right">{student?.program}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Enrollment Year:</span>
              <span className="font-semibold text-slate-800">{student?.enrollment_year}</span>
            </div>
          </div>

          {!showCorrectionForm ? (
            <div className="space-y-3">
              <button
                type="button"
                onClick={handleConfirm}
                disabled={submitting}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2.5 px-4 rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 flex items-center justify-center space-x-1.5"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>{submitting ? 'Confirming...' : 'Yes, My Details Are Correct'}</span>
              </button>

              <button
                type="button"
                onClick={() => setShowCorrectionForm(true)}
                className="w-full bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 py-2.5 px-4 rounded-lg text-xs font-semibold shadow-sm transition flex items-center justify-center space-x-1.5"
              >
                <Edit3 className="h-4 w-4 text-slate-500" />
                <span>No, Request a Correction</span>
              </button>
            </div>
          ) : (
            <form onSubmit={handleCorrectionSubmit} className="space-y-3 pt-2 border-t border-slate-200">
              <h3 className="text-xs font-bold text-slate-800">Submit Corrections to Institution</h3>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Correct Name</label>
                <input
                  type="text"
                  placeholder={student?.name}
                  value={corrections.name}
                  onChange={(e) => setCorrections({ ...corrections, name: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded focus:ring-2 focus:ring-[#0d9488] outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Correct Programme</label>
                <input
                  type="text"
                  placeholder={student?.program}
                  value={corrections.program}
                  onChange={(e) => setCorrections({ ...corrections, program: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded focus:ring-2 focus:ring-[#0d9488] outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Notes / Discrepancy details</label>
                <textarea
                  rows="2"
                  placeholder="Explain the error..."
                  value={corrections.notes}
                  onChange={(e) => setCorrections({ ...corrections, notes: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded focus:ring-2 focus:ring-[#0d9488] outline-none"
                />
              </div>

              <div className="flex space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCorrectionForm(false)}
                  className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 rounded text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 bg-[#1a3a5c] hover:bg-[#122942] text-white py-2 rounded text-xs font-semibold disabled:opacity-50"
                >
                  {submitting ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      <footer className="text-center py-4 text-[11px] text-slate-400">
        Demo build for SIH26263 • No actual student data altered
      </footer>
    </div>
  );
}
