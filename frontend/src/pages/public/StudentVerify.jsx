import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { publicApi } from '../../api/api';
import { CheckCircle2, AlertCircle, Edit3, ArrowRight, KeyRound } from 'lucide-react';

export function StudentVerify() {
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const defaultAction = searchParams.get('action'); // 'confirm' or 'correct'

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [otp, setOtp] = useState('');
  const [otpError, setOtpError] = useState('');

  const [showCorrectionForm, setShowCorrectionForm] = useState(defaultAction === 'correct');
  const [corrections, setCorrections] = useState({
    name: '',
    program: '',
    enrollment_year: '',
    notes: '',
  });

  useEffect(() => {
    async function fetchPayload() {
      try {
        setLoading(true);
        const res = await publicApi.getVerificationPayload(token);
        setData(res);
        if (res.already_verified) {
          setConfirmed(true);
        }
      } catch (err) {
        setError(err.message || 'Verification link is invalid or has expired.');
      } finally {
        setLoading(false);
      }
    }
    fetchPayload();
  }, [token]);

  const validateOtp = () => {
    if (!otp || otp.trim().length !== 6) {
      setOtpError('Please enter the complete 6-digit passcode sent to your email.');
      return false;
    }
    setOtpError('');
    return true;
  };

  const handleConfirm = async () => {
    if (!validateOtp()) return;
    setSubmitting(true);
    setOtpError('');
    try {
      await publicApi.confirmVerification(token, otp.trim());
      setConfirmed(true);
    } catch (err) {
      const msg = err.message || 'Failed to confirm details.';
      if (msg.toLowerCase().includes('otp')) {
        setOtpError(msg);
      } else {
        alert(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleCorrectionSubmit = async (e) => {
    e.preventDefault();
    if (!validateOtp()) return;
    setSubmitting(true);
    setOtpError('');
    try {
      await publicApi.submitCorrection(token, corrections, otp.trim());
      setConfirmed(true);
    } catch (err) {
      const msg = err.message || 'Failed to submit correction proposal.';
      if (msg.toLowerCase().includes('otp')) {
        setOtpError(msg);
      } else {
        alert(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="text-xs text-slate-500 font-medium">Validating verification security token...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border border-slate-200 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-[#272727]">Verification Link Expired or Invalid</h2>
          <p className="text-xs text-slate-500">{error}</p>
          <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
            Prototype built for SIH26263. Not an official Government of India service.
          </div>
        </div>
      </div>
    );
  }

  if (confirmed) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border border-slate-200 text-center space-y-4">
          <CheckCircle2 className="h-12 w-12 text-[#1b756b] mx-auto" />
          <h2 className="text-xl font-bold text-[#272727]">Verification Response Recorded</h2>
          <p className="text-xs text-slate-600">
            Thank you. Your confirmation has been permanently recorded to the platform's tamper-evident audit ledger.
          </p>
          <div className="p-3 bg-slate-50 rounded-xl text-slate-500 text-[11px] font-mono">
            Status: Processed & Logged
          </div>
          <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
            Prototype built for SIH26263. Not an official Government of India service.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      {/* Brand Top Header */}
      <header className="bg-white border-b border-slate-200 py-4 px-6 shadow-sm">
        <div className="max-w-md mx-auto flex items-center space-x-3">
          <div className="h-8 px-2.5 rounded-lg bg-[#1b756b] flex items-center justify-center text-white font-bold text-xs tracking-wide">
            VISHWAS
          </div>
          <div>
            <h1 className="font-bold text-sm text-[#272727]">Vishwas • Student Record Verification</h1>
            <span className="block text-[11px] text-[#1b756b]">Self-Confirmation Portal</span>
          </div>
        </div>
      </header>

      <div className="flex-1 max-w-md w-full mx-auto p-4 flex items-center">
        <div className="w-full bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-5">
          <div>
            <span className="text-[10px] font-semibold tracking-wider text-[#1b756b] uppercase bg-[#d7f9e4] px-2 py-0.5 rounded-full border border-teal-200">
              Student Action Required
            </span>
            <h2 className="text-lg font-bold text-[#272727] mt-2">Confirm Your Enrollment Details</h2>
            <p className="text-xs text-slate-500 mt-1">
              Please inspect the academic enrollment details submitted by your institution:
            </p>
          </div>

          {/* Student Record Card */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-2.5 text-xs">
            <div className="flex justify-between border-b border-slate-200/60 pb-2">
              <span className="text-slate-500">Student Name:</span>
              <span className="font-semibold text-[#272727]">{data?.student_name}</span>
            </div>
            <div className="flex justify-between border-b border-slate-200/60 pb-2">
              <span className="text-slate-500">Institution:</span>
              <span className="font-semibold text-[#272727] text-right">{data?.institute_name}</span>
            </div>
            <div className="flex justify-between border-b border-slate-200/60 pb-2">
              <span className="text-slate-500">Enrolled Programme:</span>
              <span className="font-semibold text-[#272727] text-right">{data?.program}</span>
            </div>
            <div className="flex justify-between border-b border-slate-200/60 pb-2">
              <span className="text-slate-500">Enrolment Year:</span>
              <span className="font-semibold text-[#272727]">{data?.enrollment_year}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Masked APAAR ID:</span>
              <span className="font-mono font-bold text-[#1b756b]">{data?.apaar_id_masked}</span>
            </div>
          </div>

          {/* 6-Digit Verification OTP Input */}
          <div className="bg-[#f0fdf4] border border-teal-200 rounded-xl p-4 space-y-2">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-[#1b756b]">
              <KeyRound className="h-4 w-4" />
              <span>Enter 6-Digit Email Passcode</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-tight">
              Please enter the 6-digit one-time passcode sent in your verification email:
            </p>
            <input
              type="text"
              maxLength={6}
              placeholder="e.g. 583921"
              value={otp}
              onChange={(e) => {
                setOtp(e.target.value.replace(/\D/g, ''));
                if (otpError) setOtpError('');
              }}
              className="w-full text-center tracking-[6px] font-mono text-lg font-bold py-2 px-3 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-[#1b756b] bg-white text-[#272727]"
            />
            {otpError && (
              <p className="text-[11px] text-rose-600 font-semibold">{otpError}</p>
            )}
          </div>

          {!showCorrectionForm ? (
            <div className="space-y-2.5">
              <button
                type="button"
                onClick={handleConfirm}
                disabled={submitting}
                className="w-full bg-[#1b756b] hover:bg-[#145952] text-white py-2.5 px-4 rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>{submitting ? 'Confirming...' : 'Yes, my details are correct'}</span>
              </button>

              <button
                type="button"
                onClick={() => setShowCorrectionForm(true)}
                className="w-full bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 py-2.5 px-4 rounded-xl text-xs font-semibold shadow-sm transition flex items-center justify-center space-x-2"
              >
                <Edit3 className="h-4 w-4 text-slate-500" />
                <span>No, I need to correct something</span>
              </button>
            </div>
          ) : (
            <form onSubmit={handleCorrectionSubmit} className="space-y-3 pt-2 border-t border-slate-200">
              <h3 className="text-xs font-bold text-[#272727]">Propose Correction to Institution</h3>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Proposed Name</label>
                <input
                  type="text"
                  placeholder={data?.student_name}
                  value={corrections.name}
                  onChange={(e) => setCorrections({ ...corrections, name: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Proposed Programme</label>
                <input
                  type="text"
                  placeholder={data?.program}
                  value={corrections.program}
                  onChange={(e) => setCorrections({ ...corrections, program: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Reason / Notes</label>
                <textarea
                  rows="2"
                  placeholder="Explain the correction..."
                  value={corrections.notes}
                  onChange={(e) => setCorrections({ ...corrections, notes: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <div className="flex space-x-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowCorrectionForm(false)}
                  className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 bg-[#1b756b] hover:bg-[#145952] text-white py-2 rounded-lg text-xs font-semibold disabled:opacity-50"
                >
                  {submitting ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
            </form>
          )}

          <div className="text-[11px] text-slate-400 text-center">
            • Single-use security token • No password required
          </div>
        </div>
      </div>

      <footer className="text-center py-4 text-[11px] text-slate-500 border-t border-slate-200 bg-white">
        Prototype built for SIH26263. Not an official Government of India service.
      </footer>
    </div>
  );
}
