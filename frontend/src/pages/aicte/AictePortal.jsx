import React, { useState, useEffect } from 'react';
import { Header, Footer, StatusChip, EmailServiceChip } from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { aicteApi, getAuthToken } from '../../api/api';
import { formatTitleCase, getStatusLabel, getCheckLabel, CHECK_LABELS } from '../../utils/formatters';
import {
  ShieldCheck,
  Award,
  Layers,
  FileCheck2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  Lock,
  Play,
  UserPlus,
  Send,
  Eye,
  Check,
  X,
  FileText
} from 'lucide-react';

export function AictePortal() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('batches'); // 'batches' | 'onboard' | 'security'
  const [batches, setBatches] = useState([]);
  const [loadingBatches, setLoadingBatches] = useState(true);
  const [actionMessage, setActionMessage] = useState(null);
  const [emailStatus, setEmailStatus] = useState(null);

  // Verification Run Live State (Section 3)
  const [activeRunBatch, setActiveRunBatch] = useState(null);
  const [runStarted, setRunStarted] = useState(false);
  const [runSummary, setRunSummary] = useState(null);
  const [streamedStudents, setStreamedStudents] = useState([]);
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [selectedStudentDetail, setSelectedStudentDetail] = useState(null);
  const [filterVerdict, setFilterVerdict] = useState('all'); // all, cleared, needs_review, blocked
  const [searchQuery, setSearchQuery] = useState('');

  // Reviewer Decision Modal / Action State
  const [decisionStudent, setDecisionStudent] = useState(null);
  const [decisionChoice, setDecisionChoice] = useState('accepted');
  const [decisionNote, setDecisionNote] = useState('');
  const [submittingDecision, setSubmittingDecision] = useState(false);

  // Approval Gate & Batch Rejection
  const [approving, setApproving] = useState(false);
  const [rejectModalBatch, setRejectModalBatch] = useState(null);
  const [rejectReason, setRejectReason] = useState('');

  // Institute Onboarding Form State
  const [institutesList, setInstitutesList] = useState([]);
  const [selectedInstId, setSelectedInstId] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminName, setAdminName] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [onboarding, setOnboarding] = useState(false);

  const fetchBatches = async () => {
    try {
      setLoadingBatches(true);
      const res = await aicteApi.getBatches();
      setBatches(res.batches || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingBatches(false);
    }
  };

  const fetchEmailStatus = async () => {
    try {
      const res = await aicteApi.getEmailStatus();
      setEmailStatus(res);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchInstitutes = async () => {
    try {
      const res = await aicteApi.getInstitutesList();
      setInstitutesList(res.institutes || []);
      if (res.institutes?.length > 0) setSelectedInstId(String(res.institutes[0].id));
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchBatches();
    fetchEmailStatus();
    fetchInstitutes();
  }, [user]);

  // Start Real SSE Verification Run Stream
  const handleBeginVerification = (batch) => {
    setActiveRunBatch(batch);
    setRunStarted(true);
    setStreamedStudents([]);
    setRunSummary(null);
    setCurrentStageIndex(0);
    setSelectedStudentDetail(null);

    const token = getAuthToken();
    const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    const sseUrl = `${API_BASE}/aicte/batches/${batch.batch_id}/run-verification?token=${encodeURIComponent(token)}`;

    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'run_started') {
          // Started
        } else if (data.event === 'student_checked') {
          setStreamedStudents((prev) => {
            const exists = prev.find((p) => p.student_id === data.student_id);
            if (exists) return prev;
            return [...prev, data];
          });
          setCurrentStageIndex(Math.min(10, Math.floor((data.index / data.total_students) * 10)));
        } else if (data.event === 'run_completed') {
          setRunSummary(data.summary);
          setCurrentStageIndex(10);
          eventSource.close();
          fetchBatches();
        }
      } catch (err) {
        console.error('SSE JSON error:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Stream error:', err);
      eventSource.close();
    };
  };

  const handleOpenPreviousRun = async (batch) => {
    setActiveRunBatch(batch);
    setRunStarted(true);
    setStreamedStudents([]);
    setRunSummary(null);
    setCurrentStageIndex(0);
    setSelectedStudentDetail(null);
    try {
      const run = await aicteApi.getLastRun(batch.batch_id);
      if (run.has_run && run.students?.length > 0) {
        // Normalize field names to match SSE format
        const normalized = run.students.map((s) => ({
          ...s,
          apaar_id: s.apaar_id_masked || s.apaar_id || '',
        }));
        setRunSummary(run.summary);
        setStreamedStudents(normalized);
        setCurrentStageIndex(10);
      } else {
        // No saved results — start a fresh run
        handleBeginVerification(batch);
      }
    } catch (err) {
      console.error(err);
      handleBeginVerification(batch);
    }
  };

  const handleSubmitDecision = async () => {
    if (!decisionStudent || !decisionNote.trim()) {
      alert('A detailed reviewer note is mandatory.');
      return;
    }
    setSubmittingDecision(true);
    try {
      const resId = decisionStudent.result_id || decisionStudent.student_id;
      await aicteApi.submitReviewerDecision(resId, decisionChoice, decisionNote.trim());
      setActionMessage({ type: 'success', text: `Reviewer decision logged for ${decisionStudent.student_name}.` });
      setDecisionStudent(null);
      setDecisionNote('');

      // Refresh run results
      const updated = await aicteApi.getLastRun(activeRunBatch.batch_id);
      if (updated.has_run) {
        const normalized = (updated.students || []).map((s) => ({
          ...s,
          apaar_id: s.apaar_id_masked || s.apaar_id || '',
        }));
        setStreamedStudents(normalized);
        setRunSummary(updated.summary);

        // Also update selectedStudentDetail if it's currently selected
        if (selectedStudentDetail) {
          const match = normalized.find((s) => s.student_id === selectedStudentDetail.student_id);
          if (match) setSelectedStudentDetail(match);
        }
      }
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleApproveEoA = async () => {
    setApproving(true);
    try {
      const res = await aicteApi.approveBatch(activeRunBatch.batch_id);
      setActionMessage({
        type: 'success',
        text: 'Batch approved! Official Extension of Approval issued and cryptographically anchored to ledger.'
      });
      fetchBatches();
      setActiveRunBatch(null);
      setRunStarted(false);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setApproving(false);
    }
  };

  const handleRejectBatch = async () => {
    if (!rejectReason.trim()) return;
    try {
      await aicteApi.rejectBatch(rejectModalBatch.batch_id, rejectReason.trim());
      setActionMessage({ type: 'info', text: 'Batch returned to institution with feedback.' });
      setRejectModalBatch(null);
      setRejectReason('');
      fetchBatches();
      setActiveRunBatch(null);
      setRunStarted(false);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleOnboardSubmit = async (e) => {
    e.preventDefault();
    setOnboarding(true);
    try {
      const res = await aicteApi.onboardInstitute(
        Number(selectedInstId),
        adminEmail.trim(),
        adminName.trim(),
        adminPassword.trim()
      );
      setActionMessage({ type: 'success', text: res.message });
      setAdminEmail('');
      setAdminName('');
      setAdminPassword('');
      setActiveTab('batches');
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setOnboarding(false);
    }
  };

  // 10 Verification Check definitions
  const verificationStages = [
    { key: 'apaar_format', label: '1. APAAR ID Format' },
    { key: 'honeytoken_scan', label: '2. Honeytoken Scan' },
    { key: 'exact_duplicate', label: '3. Exact Duplicate' },
    { key: 'fuzzy_duplicate', label: '4. Fuzzy Duplicate' },
    { key: 'self_verification', label: '5. Student Confirmation' },
    { key: 'geographic_plausibility', label: '6. Geographic Plausibility' },
    { key: 'lifecycle_plausibility', label: '7. Lifecycle Plausibility' },
    { key: 'field_consistency', label: '8. Field & NRI Consistency' },
    { key: 'capacity_check', label: '9. Approved Intake Capacity' },
    { key: 'closure_check', label: '10. Closed Programme Check' },
  ];

  // Filtering students in the matrix
  const filteredStudents = streamedStudents.filter((s) => {
    if (filterVerdict !== 'all' && s.verdict !== filterVerdict) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = s.student_name?.toLowerCase().includes(q);
      const matchProg = s.program?.toLowerCase().includes(q);
      const matchApaar = s.apaar_id?.toLowerCase().includes(q);
      return matchName || matchProg || matchApaar;
    }
    return true;
  });

  // Calculate unaddressed flagged count for the approval gate
  const pendingDecisionsCount = streamedStudents.filter(
    (s) => (s.verdict === 'blocked' || s.verdict === 'needs_review') && !s.reviewer_decision
  ).length;

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50">
      <Header />

      {/* Pale Mint Hero Section */}
      <section className="bg-gradient-to-b from-[#d7f9e4] to-[#f0fdf5] border-b border-teal-100 py-7 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[#272727] tracking-tight">
              AICTE Regulatory Verification Console
            </h1>
            <p className="text-xs text-slate-600 mt-1">
              Automated 10-point cross-institutional audit, capacity compliance, and cryptographic EoA generation
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <EmailServiceChip statusData={emailStatus} />
            <div className="bg-white px-3 py-1 rounded-full border border-purple-200 text-[#8177f1] text-xs font-semibold shadow-sm">
              {batches.length} Submitted Batch{batches.length === 1 ? '' : 'es'}
            </div>
          </div>
        </div>
      </section>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Action Message Banner */}
        {actionMessage && (
          <div
            className={`mb-6 p-4 rounded-xl text-xs font-medium border flex items-center justify-between ${
              actionMessage.type === 'error'
                ? 'bg-rose-50 text-rose-800 border-rose-200'
                : 'bg-emerald-50 text-emerald-800 border-emerald-200'
            }`}
          >
            <span>{actionMessage.text}</span>
            <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-slate-600 font-bold ml-4">
              ×
            </button>
          </div>
        )}

        {/* Tab Switcher */}
        {!runStarted && (
          <div className="flex border-b border-slate-200 mb-6 space-x-6 text-xs font-semibold">
            <button
              onClick={() => setActiveTab('batches')}
              className={`pb-3 border-b-2 flex items-center space-x-2 transition ${
                activeTab === 'batches' ? 'border-[#1b756b] text-[#1b756b]' : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <Layers className="h-4 w-4" />
              <span>Institutional Batches</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-700">
                {batches.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('onboard')}
              className={`pb-3 border-b-2 flex items-center space-x-2 transition ${
                activeTab === 'onboard' ? 'border-[#1b756b] text-[#1b756b]' : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <UserPlus className="h-4 w-4" />
              <span>Onboard Institute Account</span>
            </button>
          </div>
        )}

        {/* TAB 1: BATCH LIST (DEFAULT VIEW) */}
        {!runStarted && activeTab === 'batches' && (
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-base font-bold text-[#272727]">Submitted Academic Batches</h2>
                <p className="text-xs text-slate-500">
                  Batches awaiting review or approved by the AICTE Regulatory Bureau
                </p>
              </div>
              <button onClick={fetchBatches} className="text-slate-400 hover:text-slate-600 p-1" title="Refresh">
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>

            {loadingBatches ? (
              <div className="text-center py-8 text-xs text-slate-400">Loading submitted batches...</div>
            ) : batches.length === 0 ? (
              <div className="text-center py-12 text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                No batches submitted yet. Once an institution pushes a cohort, it will appear here for review.
              </div>
            ) : (
              <div className="border border-slate-200 rounded-xl overflow-x-auto">
                <table className="w-full text-left text-xs divide-y divide-slate-200">
                  <thead className="bg-slate-50 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Batch Name</th>
                      <th className="px-4 py-3">Institution</th>
                      <th className="px-4 py-3">Students</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Regulatory Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {batches.map((b) => (
                      <tr key={b.batch_id} className="hover:bg-slate-50/50">
                        <td className="px-4 py-3 font-semibold text-[#272727]">{b.name}</td>
                        <td className="px-4 py-3 text-slate-600">{b.institute_name}</td>
                        <td className="px-4 py-3 text-slate-500">{b.student_count} records</td>
                        <td className="px-4 py-3">
                          <StatusChip status={b.status} label={b.status_label} />
                        </td>
                        <td className="px-4 py-3 text-right space-x-2">
                          {b.status === 'pushed' && (
                            <button
                              onClick={() => handleBeginVerification(b)}
                              className="px-3 py-1.5 bg-[#1b756b] hover:bg-[#145952] text-white rounded-lg text-xs font-semibold shadow-sm transition inline-flex items-center space-x-1"
                            >
                              <Play className="h-3.5 w-3.5" />
                              <span>Begin Verification Run</span>
                            </button>
                          )}
                          {b.status === 'under_review' && (
                            <button
                              onClick={() => handleOpenPreviousRun(b)}
                              className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold shadow-sm transition inline-flex items-center space-x-1"
                            >
                              <Eye className="h-3.5 w-3.5" />
                              <span>Resume Verification Run</span>
                            </button>
                          )}
                          {b.status === 'approved' && (
                            <button
                              onClick={() => handleOpenPreviousRun(b)}
                              className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                            >
                              View Completed Audit
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: ONBOARD INSTITUTE ACCOUNT */}
        {!runStarted && activeTab === 'onboard' && (
          <div className="bg-white max-w-lg mx-auto p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div>
              <h2 className="text-base font-bold text-[#272727]">Onboard Institution Account</h2>
              <p className="text-xs text-slate-500">
                Provision a verified administrator login for an institution present in the loaded AICTE reference data.
              </p>
            </div>

            <form onSubmit={handleOnboardSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Select Institution</label>
                <select
                  value={selectedInstId}
                  onChange={(e) => setSelectedInstId(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white outline-none focus:ring-1 focus:ring-[#1b756b]"
                >
                  {institutesList.map((inst) => (
                    <option key={inst.id} value={inst.id}>
                      {inst.name} ({inst.state || 'National'}) [{inst.aicte_code}]
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Administrator Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="principal@institution.edu"
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Administrator Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="Prof. S. R. Kulkarni"
                  value={adminName}
                  onChange={(e) => setAdminName(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Initial Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <button
                type="submit"
                disabled={onboarding}
                className="w-full bg-[#1b756b] hover:bg-[#145952] text-white py-2.5 rounded-lg font-semibold shadow-sm transition disabled:opacity-50"
              >
                {onboarding ? 'Provisioning Account...' : 'Provision Institution Account'}
              </button>
            </form>
          </div>
        )}

        {/* SECTION 3: LIVE VERIFICATION RUN WORKSPACE (THE COOL PART) */}
        {runStarted && activeRunBatch && (
          <div className="space-y-6">
            {/* Top Run Header & Summary Bar */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center space-x-3 mb-1">
                  <h2 className="text-xl font-bold text-[#272727]">{activeRunBatch.name}</h2>
                  <span className="text-xs text-slate-400 font-medium">({activeRunBatch.institute_name})</span>
                </div>
                <div className="flex items-center space-x-2 text-xs text-slate-500">
                  <span>Batch Run Pipeline</span>
                  <span>•</span>
                  <span>Processed: {streamedStudents.length} Students</span>
                </div>
              </div>

              {/* Counts & Gate Actions */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center space-x-2 text-xs">
                  <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                    ✓ Cleared: {streamedStudents.filter((s) => s.verdict === 'cleared').length}
                  </span>
                  <span className="px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-bold">
                    ⚠ Needs Review: {streamedStudents.filter((s) => s.verdict === 'needs_review').length}
                  </span>
                  <span className="px-2.5 py-1 rounded-full bg-rose-50 text-rose-800 border border-rose-200 font-bold">
                    ✕ Blocked: {streamedStudents.filter((s) => s.verdict === 'blocked').length}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setRejectModalBatch(activeRunBatch)}
                    className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-800 rounded-lg text-xs font-semibold"
                  >
                    Reject Batch
                  </button>

                  <button
                    onClick={handleApproveEoA}
                    disabled={approving || pendingDecisionsCount > 0 || currentStageIndex < 10}
                    className="px-4 py-1.5 bg-[#1b756b] hover:bg-[#145952] text-white rounded-lg text-xs font-bold shadow-sm transition disabled:opacity-40"
                    title={
                      pendingDecisionsCount > 0
                        ? `Cannot approve: ${pendingDecisionsCount} flagged student(s) still require a reviewer decision note.`
                        : ''
                    }
                  >
                    {approving ? 'Issuing EoA...' : 'Approve and Issue EoA'}
                  </button>

                  <button
                    onClick={() => {
                      setRunStarted(false);
                      setActiveRunBatch(null);
                    }}
                    className="p-1.5 text-slate-400 hover:text-slate-600"
                    title="Close Run Workspace"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Approval Gate Notice if Blocked */}
            {pendingDecisionsCount > 0 && currentStageIndex === 10 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center justify-between">
                <span>
                  <strong>Approval Gate:</strong> {pendingDecisionsCount} flagged student record(s) must have a reviewer decision and note entered in the drawer before the Extension of Approval can be issued.
                </span>
              </div>
            )}

            {/* Approved Intake Capacity Overview */}
            {runSummary?.course_capacities && (
              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm text-xs">
                <span className="font-bold text-[#272727] block mb-2">Approved Intake vs. Enrolled Gauge:</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {runSummary.course_capacities.map((cap, i) => (
                    <div key={i} className="p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                      <div className="font-semibold text-slate-800">{cap.course}</div>
                      <div className="text-slate-500 text-[11px] mt-0.5">{cap.note}</div>
                      <div className="mt-1">
                        <StatusChip
                          status={cap.status === 'pass' ? 'cleared' : cap.status === 'not_assessable' ? 'needs_review' : 'blocked'}
                          label={cap.status === 'pass' ? 'Within Intake' : cap.status === 'not_assessable' ? 'Extended EoA' : 'Over Capacity'}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3-Panel Main Workspace: Left Stages | Center Matrix | Right Drawer */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Panel: 10 Stage Tracker */}
              <div className="lg:col-span-3 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                <span className="text-xs font-bold text-[#272727] uppercase tracking-wider block">
                  Verification Pipeline
                </span>

                {/* Progress bar */}
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-[#1b756b] h-2 transition-all duration-300"
                    style={{ width: `${(currentStageIndex / 10) * 100}%` }}
                  />
                </div>

                <div className="space-y-2 text-xs">
                  {verificationStages.map((stg, i) => {
                    const isDone = currentStageIndex > i;
                    const isCurrent = currentStageIndex === i && currentStageIndex < 10;
                    return (
                      <div
                        key={stg.key}
                        className={`p-2 rounded-xl transition flex items-center justify-between ${
                          isDone
                            ? 'bg-[#d7f9e4]/40 text-[#1b756b] font-medium'
                            : isCurrent
                            ? 'bg-amber-50 text-amber-800 font-semibold border border-amber-200'
                            : 'text-slate-400'
                        }`}
                      >
                        <span>{stg.label}</span>
                        {isDone ? <Check className="h-4 w-4 text-[#1b756b]" /> : isCurrent ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : null}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Center Panel: Student-by-Check Matrix */}
              <div className="lg:col-span-6 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                {/* Search & Filter Controls */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-slate-100">
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="font-semibold text-slate-600">Filter Verdict:</span>
                    {['all', 'cleared', 'needs_review', 'blocked'].map((v) => (
                      <button
                        key={v}
                        onClick={() => setFilterVerdict(v)}
                        className={`px-2 py-0.5 rounded-lg capitalize font-medium ${
                          filterVerdict === v
                            ? 'bg-[#1b756b] text-white'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        {v.replace(/_/g, ' ')}
                      </button>
                    ))}
                  </div>

                  <div className="relative w-full sm:w-44">
                    <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-2" />
                    <input
                      type="text"
                      placeholder="Search students..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-2 py-1 text-xs border border-slate-200 rounded-lg outline-none"
                    />
                  </div>
                </div>

                {/* Matrix Table */}
                <div className="border border-slate-200 rounded-xl overflow-x-auto max-h-[500px]">
                  <table className="w-full text-left text-xs divide-y divide-slate-200 sticky-header">
                    <thead className="bg-slate-50 text-slate-600 font-semibold uppercase text-[10px] tracking-wider sticky top-0 z-10">
                      <tr>
                        <th className="px-3 py-2.5">Student</th>
                        <th className="px-2 py-2.5 text-center">Fmt</th>
                        <th className="px-2 py-2.5 text-center">Canary</th>
                        <th className="px-2 py-2.5 text-center">Exact</th>
                        <th className="px-2 py-2.5 text-center">Fuzzy</th>
                        <th className="px-2 py-2.5 text-center">Confirm</th>
                        <th className="px-2 py-2.5 text-center">Geo</th>
                        <th className="px-2 py-2.5 text-center">Life</th>
                        <th className="px-2 py-2.5 text-center">Verdict</th>
                        <th className="px-2 py-2.5 text-center">Review</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredStudents.length === 0 ? (
                        <tr>
                          <td colSpan={10} className="px-4 py-8 text-center text-slate-400">
                            {streamedStudents.length === 0
                              ? 'Executing verification pipeline...'
                              : 'No students matching filter.'}
                          </td>
                        </tr>
                      ) : (
                        filteredStudents.map((std) => {
                          const isSelected = selectedStudentDetail?.student_id === std.student_id;
                          return (
                            <tr
                              key={std.student_id}
                              onClick={() => setSelectedStudentDetail(std)}
                              className={`cursor-pointer transition ${
                                isSelected ? 'bg-teal-50/70 font-semibold' : 'hover:bg-slate-50/60'
                              }`}
                            >
                              <td className="px-3 py-2">
                                <div className="text-[#272727] truncate max-w-[120px]">{std.student_name}</div>
                                <div className="text-[10px] font-mono text-slate-400">{std.apaar_id}</div>
                              </td>

                              {/* Matrix Cell Badges with Text */}
                              {[
                                'apaar_format',
                                'honeytoken_scan',
                                'exact_duplicate',
                                'fuzzy_duplicate',
                                'self_verification',
                                'geographic_plausibility',
                                'lifecycle_plausibility',
                              ].map((ckey) => {
                                const checkObj = std.checks?.[ckey];
                                const isPass = checkObj?.status === 'pass';
                                const isWarn = checkObj?.status === 'warning';
                                const isFail = checkObj?.status === 'fail';

                                return (
                                  <td key={ckey} className="px-1.5 py-2 text-center text-[10px]">
                                    {isPass && <span className="text-emerald-700 font-bold">✓ Pass</span>}
                                    {isWarn && <span className="text-amber-700 font-bold">⚠ Warn</span>}
                                    {isFail && <span className="text-rose-700 font-bold">✕ Fail</span>}
                                  </td>
                                );
                              })}

                              <td className="px-2 py-2 text-center">
                                <StatusChip status={std.verdict} label={getStatusLabel(std.verdict)} />
                              </td>
                              <td className="px-2 py-2 text-center">
                                {std.reviewer_decision ? (
                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 capitalize" title={std.reviewer_note}>
                                    ✓ {std.reviewer_decision}
                                  </span>
                                ) : (std.verdict === 'needs_review' || std.verdict === 'blocked') ? (
                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
                                    Pending
                                  </span>
                                ) : (
                                  <span className="text-slate-400 text-[10px]">-</span>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Right Panel: Selected Student Detail Drawer */}
              <div className="lg:col-span-3 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                <span className="text-xs font-bold text-[#272727] uppercase tracking-wider block">
                  Forensic Detail Drawer
                </span>

                {selectedStudentDetail ? (
                  <div className="space-y-4 text-xs">
                    <div>
                      <h4 className="text-sm font-bold text-[#272727]">{selectedStudentDetail.student_name}</h4>
                      <div className="text-slate-400 font-mono text-[11px]">{selectedStudentDetail.apaar_id}</div>
                      <div className="text-slate-500 text-[11px] mt-0.5">{selectedStudentDetail.program}</div>
                      <div className="mt-2">
                        <StatusChip
                          status={selectedStudentDetail.verdict}
                          label={getStatusLabel(selectedStudentDetail.verdict)}
                        />
                      </div>
                    </div>

                    {/* Breakdown of Checks and Reasons */}
                    <div className="space-y-2 border-t border-slate-100 pt-3 max-h-60 overflow-y-auto">
                      {Object.entries(selectedStudentDetail.checks || {}).map(([key, val]) => (
                        <div key={key} className="p-2 bg-slate-50 rounded-xl text-[11px] space-y-1">
                          <div className="font-semibold text-slate-800 flex justify-between">
                            <span>{getCheckLabel(key)}:</span>
                            <span className="capitalize font-bold text-slate-600">{val.status}</span>
                          </div>
                          <p className="text-slate-600 text-[10px] leading-relaxed">{val.reason}</p>
                          {val.evidence && (
                            <pre className="text-[9px] bg-white p-1 rounded border border-slate-200 overflow-x-auto text-slate-500">
                              {JSON.stringify(val.evidence, null, 1)}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Audit Ledger Block Hash */}
                    <div className="p-2 bg-slate-100 rounded-xl text-[10px] font-mono break-all text-slate-600">
                      <span className="font-bold block">Audit Ledger Hash:</span>
                      {selectedStudentDetail.audit_hash}
                    </div>

                    {/* Reviewer Decision Status */}
                    {selectedStudentDetail.reviewer_decision ? (
                      <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-xs">
                        <span className="font-bold text-emerald-900 block">Reviewer Decision Recorded:</span>
                        <div className="capitalize font-semibold text-emerald-800 mt-0.5">
                          {selectedStudentDetail.reviewer_decision}
                        </div>
                        <p className="text-slate-600 text-[11px] mt-1">{selectedStudentDetail.reviewer_note}</p>
                      </div>
                    ) : (
                      (selectedStudentDetail.verdict === 'needs_review' || selectedStudentDetail.verdict === 'blocked') && (
                        <button
                          onClick={() => {
                            setDecisionStudent(selectedStudentDetail);
                            setDecisionChoice('accepted');
                            setDecisionNote('');
                          }}
                          className="w-full bg-[#1b756b] hover:bg-[#145952] text-white py-2 rounded-xl text-xs font-semibold shadow-sm transition"
                        >
                          Submit Reviewer Decision
                        </button>
                      )
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-xs text-slate-400">
                    Click any student row in the matrix to view detailed forensic evidence, audit block hash, and enter reviewer notes.
                  </div>
                )}
              </div>
            </div>

            {/* Reviewer Decision Modal */}
            {decisionStudent && (
              <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
                <div className="bg-white max-w-md w-full rounded-2xl p-6 shadow-xl space-y-4">
                  <h3 className="text-base font-bold text-[#272727]">
                    Reviewer Decision: {decisionStudent.student_name}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Provide mandatory reviewer notes to satisfy the EoA approval gate.
                  </p>

                  <div className="space-y-3 text-xs">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Decision Action</label>
                      <select
                        value={decisionChoice}
                        onChange={(e) => setDecisionChoice(e.target.value)}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg outline-none bg-white"
                      >
                        <option value="accepted">Accept with Note (Permit in Batch)</option>
                        <option value="rejected">Reject Record (Exclude from Approval)</option>
                        <option value="correction_requested">Request Institutional Correction</option>
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        Mandatory Reviewer Note (Audit Trail)
                      </label>
                      <textarea
                        rows="3"
                        required
                        placeholder="State your justification (e.g. Relocation soft signal accepted after verifying local residence certificate)..."
                        value={decisionNote}
                        onChange={(e) => setDecisionNote(e.target.value)}
                        className="w-full p-2.5 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end space-x-2 pt-2">
                    <button
                      onClick={() => setDecisionStudent(null)}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmitDecision}
                      disabled={submittingDecision || !decisionNote.trim()}
                      className="px-4 py-1.5 bg-[#1b756b] hover:bg-[#145952] text-white font-semibold rounded-lg text-xs disabled:opacity-50"
                    >
                      {submittingDecision ? 'Logging Decision...' : 'Commit Decision to Audit Chain'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Batch Rejection Modal */}
            {rejectModalBatch && (
              <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
                <div className="bg-white max-w-md w-full rounded-2xl p-6 shadow-xl space-y-4">
                  <h3 className="text-base font-bold text-rose-900">Return Batch to Institution</h3>
                  <p className="text-xs text-slate-500">
                    State the regulatory grounds for returning batch <strong>{rejectModalBatch.name}</strong>.
                  </p>

                  <textarea
                    rows="3"
                    required
                    placeholder="e.g. Unresolved dual-enrollment APAAR duplicates detected across institutions..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="w-full p-2.5 text-xs border border-rose-300 rounded-lg outline-none focus:ring-1 focus:ring-rose-500"
                  />

                  <div className="flex justify-end space-x-2 pt-2">
                    <button
                      onClick={() => setRejectModalBatch(null)}
                      className="px-3 py-1.5 bg-slate-100 rounded-lg text-xs text-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleRejectBatch}
                      disabled={!rejectReason.trim()}
                      className="px-4 py-1.5 bg-rose-700 hover:bg-rose-800 text-white font-semibold rounded-lg text-xs disabled:opacity-50"
                    >
                      Return Batch with Feedback
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
