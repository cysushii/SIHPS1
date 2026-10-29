import React, { useState, useEffect } from 'react';
import { Header, Footer, StatusChip, EmailServiceChip } from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { instituteApi } from '../../api/api';
import { formatTitleCase, getStatusLabel } from '../../utils/formatters';
import {
  Upload,
  PlusCircle,
  FileCheck2,
  Send,
  Users,
  AlertTriangle,
  FileSpreadsheet,
  Layers,
  ChevronRight,
  RefreshCw,
  Mail,
  CheckCircle2,
  Inbox
} from 'lucide-react';

export function InstitutePortal() {
  const { user } = useAuth();
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newBatchName, setNewBatchName] = useState('');
  const [creatingBatch, setCreatingBatch] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [batchDetails, setBatchDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [emailStatus, setEmailStatus] = useState(null);

  // Ingestion form state
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);

  // Diagnostic Test Email
  const [testEmailAddr, setTestEmailAddr] = useState('');
  const [sendingTest, setSendingTest] = useState(false);

  // Correction Review Modal
  const [correctionTarget, setCorrectionTarget] = useState(null);
  const [reviewNote, setReviewNote] = useState('');

  const fetchBatches = async () => {
    try {
      setLoading(true);
      const res = await instituteApi.getBatches();
      setBatches(res.batches || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchEmailStatus = async () => {
    try {
      const res = await instituteApi.getEmailStatus();
      setEmailStatus(res);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchBatches();
    fetchEmailStatus();
  }, [user]);

  const handleSelectBatch = async (batchId) => {
    setSelectedBatch(batchId);
    setLoadingDetails(true);
    try {
      const details = await instituteApi.getBatchDetails(batchId);
      setBatchDetails(details);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleCreateBatch = async (e) => {
    e.preventDefault();
    if (!newBatchName.trim()) return;
    setCreatingBatch(true);
    try {
      const res = await instituteApi.createBatch(newBatchName);
      setNewBatchName('');
      setActionMessage({ type: 'success', text: `Batch '${res.name}' created with ${res.student_count} attached student(s).` });
      fetchBatches();
      handleSelectBatch(res.batch_id);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setCreatingBatch(false);
    }
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', uploadFile);

    try {
      const res = await instituteApi.uploadStudents(formData);
      setUploadResult(res);
      setActionMessage({ type: 'success', text: `Roster processed: ${res.inserted} students registered.` });
      fetchBatches();
      if (selectedBatch) handleSelectBatch(selectedBatch);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setUploading(false);
    }
  };

  const handleSendVerifications = async (batchId) => {
    try {
      const res = await instituteApi.sendVerifications(batchId);
      setActionMessage({
        type: 'success',
        text: `Verification dispatch complete: ${res.sent_count} sent successfully (${res.provider}${res.test_mode ? ` - Routed to ${res.test_redirect}` : ''}).`
      });
      handleSelectBatch(batchId);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handlePushBatch = async (batchId) => {
    if (!confirm('Are you sure you want to push this batch to AICTE for official regulatory review?')) return;
    try {
      await instituteApi.pushBatch(batchId);
      setActionMessage({ type: 'success', text: 'Batch pushed to AICTE regulatory desk.' });
      fetchBatches();
      if (selectedBatch === batchId) handleSelectBatch(batchId);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleSendTestEmail = async (e) => {
    e.preventDefault();
    if (!testEmailAddr.trim()) return;
    setSendingTest(true);
    try {
      const res = await instituteApi.sendTestEmail(testEmailAddr.trim());
      setActionMessage({
        type: res.delivered ? 'success' : 'error',
        text: `Diagnostic test response: ${res.provider_response}`
      });
      fetchEmailStatus();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setSendingTest(false);
    }
  };

  const handleReviewCorrection = async (action) => {
    if (!correctionTarget) return;
    try {
      await instituteApi.reviewCorrection(selectedBatch, correctionTarget.student_id, action, reviewNote);
      setActionMessage({ type: 'success', text: `Correction proposal ${action}ed.` });
      setCorrectionTarget(null);
      setReviewNote('');
      handleSelectBatch(selectedBatch);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleDownloadPdf = async (batchId) => {
    try {
      const blob = await instituteApi.downloadReport(batchId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AICTE_EoA_Batch_${batchId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleNotifyApproved = async (batchId) => {
    try {
      const res = await instituteApi.notifyStudents(batchId);
      setActionMessage({
        type: 'success',
        text: `Completion notice dispatched to ${res.sent_count} approved student(s).`
      });
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const instituteDisplayName = user?.institute_name ? formatTitleCase(user.institute_name) : 'Institute Administrator';

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50">
      <Header />

      {/* Pale Mint Hero Section */}
      <section className="bg-gradient-to-b from-[#d7f9e4] to-[#f0fdf5] border-b border-teal-100 py-7 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[#272727] tracking-tight">
              {instituteDisplayName}
            </h1>
            <p className="text-xs text-slate-600 mt-1">
              Student enrollment roster management, single-use self-verification, and AICTE approval tracking
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <EmailServiceChip statusData={emailStatus} />
            <div className="bg-white px-3 py-1 rounded-full border border-purple-200 text-[#8177f1] text-xs font-semibold shadow-sm">
              {batches.length} Batch{batches.length === 1 ? '' : 'es'} Registered
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Upload Roster + Create Batch */}
          <div className="space-y-6">
            {/* Upload Box */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center space-x-2 mb-2">
                <Upload className="h-5 w-5 text-[#1b756b]" />
                <h2 className="text-sm font-bold text-[#272727]">Upload Student Roster</h2>
              </div>
              <p className="text-xs text-slate-500 mb-3">
                Upload CSV roster with mandatory columns: apaar_id, name, program, enrollment_year, and email.
              </p>
              <a
                href={`${import.meta.env.BASE_URL}sample_roster.csv`}
                download="sample_roster.csv"
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#1b756b] hover:underline mb-3"
              >
                ⬇ Download Sample CSV
              </a>

              <form onSubmit={handleFileUpload} className="space-y-3">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  required
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  className="block w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-[#d7f9e4] file:text-[#1b756b] hover:file:bg-teal-200 cursor-pointer"
                />
                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="w-full bg-[#1b756b] hover:bg-[#145952] text-white py-2 px-3 rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50 flex items-center justify-center space-x-1.5"
                >
                  <FileSpreadsheet className="h-4 w-4" />
                  <span>{uploading ? 'Processing Data...' : 'Ingest & Validate Roster'}</span>
                </button>
              </form>

              {uploadResult && (
                <div className="mt-3 p-3 bg-slate-50 rounded-lg text-xs space-y-1">
                  <div className="font-semibold text-slate-700">Roster Ingest Result:</div>
                  <div className="text-emerald-700 font-medium">✓ {uploadResult.inserted} students registered</div>
                  {uploadResult.rejected > 0 && (
                    <div className="text-rose-600 font-medium">✕ {uploadResult.rejected} rows rejected</div>
                  )}
                  <div className="mt-2 pt-2 border-t border-slate-200 text-teal-700 font-semibold flex items-center gap-1">
                    ✅ Students ready! Now create a new batch below ↓
                  </div>
                </div>
              )}
            </div>

            {/* Create Batch Box */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center space-x-2 mb-2">
                <PlusCircle className="h-5 w-5 text-[#1b756b]" />
                <h2 className="text-sm font-bold text-[#272727]">Create Submission Batch</h2>
              </div>
              <form onSubmit={handleCreateBatch} className="space-y-3">
                <input
                  type="text"
                  required
                  placeholder="e.g. 2026 Academic Submission Cohort"
                  value={newBatchName}
                  onChange={(e) => setNewBatchName(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#1b756b] outline-none"
                />
                <button
                  type="submit"
                  disabled={creatingBatch || !newBatchName.trim()}
                  className="w-full bg-[#272727] hover:bg-black text-white py-2 px-3 rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {creatingBatch ? 'Initializing...' : 'Initialize New Batch'}
                </button>
              </form>
            </div>

            {/* Batches List */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <Layers className="h-5 w-5 text-[#1b756b]" />
                  <h2 className="text-sm font-bold text-[#272727]">Registered Batches</h2>
                </div>
                <button onClick={fetchBatches} className="text-slate-400 hover:text-slate-600 p-1" title="Refresh">
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
              </div>

              {loading ? (
                <div className="text-center py-6 text-xs text-slate-400">Loading batches...</div>
              ) : batches.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-400 bg-slate-50 rounded-xl p-4 border border-dashed border-slate-200">
                  <Inbox className="h-6 w-6 text-slate-300 mx-auto mb-1" />
                  <span>No batches yet. Upload a student roster to begin.</span>
                </div>
              ) : (
                <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
                  {batches.map((b) => (
                    <div
                      key={b.batch_id}
                      onClick={() => handleSelectBatch(b.batch_id)}
                      className={`p-3 rounded-xl cursor-pointer transition flex items-center justify-between text-xs ${
                        selectedBatch === b.batch_id ? 'bg-[#d7f9e4]/40 border border-teal-200' : 'hover:bg-slate-50'
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="font-semibold text-[#272727]">{b.name}</div>
                        <div className="text-slate-400 flex items-center space-x-2">
                          <span>{b.student_count} student(s)</span>
                          <span>•</span>
                          <StatusChip status={b.status} label={b.status_label} />
                        </div>
                      </div>
                      <ChevronRight className="h-4 w-4 text-slate-400" />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Diagnostic Email Testing Box */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-xs space-y-3">
              <span className="font-bold text-[#272727] block">Send Diagnostic Test Email</span>
              <p className="text-[11px] text-slate-500">
                Directly verify live delivery connectivity to any target address.
              </p>
              <form onSubmit={handleSendTestEmail} className="space-y-2">
                <input
                  type="email"
                  required
                  placeholder="recipient@example.com"
                  value={testEmailAddr}
                  onChange={(e) => setTestEmailAddr(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
                <button
                  type="submit"
                  disabled={sendingTest || !testEmailAddr.trim()}
                  className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 py-1.5 rounded-lg font-medium text-xs disabled:opacity-50"
                >
                  {sendingTest ? 'Sending...' : 'Send Test Message'}
                </button>
              </form>
            </div>
          </div>

          {/* Right 2 Columns: Batch Workspace */}
          <div className="lg:col-span-2 space-y-6">
            {selectedBatch && batchDetails ? (
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-4">
                  <div>
                    <div className="flex items-center space-x-3 mb-1">
                      <h2 className="text-xl font-bold text-[#272727]">{batchDetails.name}</h2>
                      <StatusChip status={batchDetails.status} label={batchDetails.status_label} />
                    </div>
                    <span className="text-xs text-slate-400">
                      {batchDetails.student_count} Enrolled Student Record(s)
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {batchDetails.status === 'draft' && (
                      <>
                        <button
                          onClick={() => handleSendVerifications(batchDetails.batch_id)}
                          disabled={!emailStatus?.can_send || batchDetails.student_count === 0}
                          className="bg-[#1b756b] hover:bg-[#145952] text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition flex items-center space-x-1.5 disabled:opacity-40"
                          title={!emailStatus?.can_send ? 'Email service not configured' : ''}
                        >
                          <Mail className="h-3.5 w-3.5" />
                          <span>Dispatch Verification Emails</span>
                        </button>
                        <button
                          onClick={() => handlePushBatch(batchDetails.batch_id)}
                          disabled={batchDetails.student_count === 0}
                          className="bg-[#272727] hover:bg-black text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition flex items-center space-x-1.5 disabled:opacity-40"
                        >
                          <Send className="h-3.5 w-3.5" />
                          <span>Push to AICTE</span>
                        </button>
                      </>
                    )}

                    {batchDetails.status === 'approved' && (
                      <>
                        <button
                          onClick={() => handleDownloadPdf(batchDetails.batch_id)}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition flex items-center space-x-1.5"
                        >
                          <FileCheck2 className="h-3.5 w-3.5" />
                          <span>Download Signed EoA PDF</span>
                        </button>
                        <button
                          onClick={() => handleNotifyApproved(batchDetails.batch_id)}
                          className="bg-[#1b756b] hover:bg-[#145952] text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition flex items-center space-x-1.5"
                        >
                          <Mail className="h-3.5 w-3.5" />
                          <span>Notify Approved Students</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {batchDetails.reject_reason && (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900">
                    <span className="font-bold block mb-1">Feedback from AICTE Regulatory Review:</span>
                    <p>{batchDetails.reject_reason}</p>
                  </div>
                )}

                {/* Students Roster Table */}
                <div>
                  <h3 className="text-sm font-bold text-[#272727] mb-3">Enrolled Student Records</h3>
                  <div className="border border-slate-200 rounded-xl overflow-x-auto">
                    <table className="w-full text-left text-xs divide-y divide-slate-200">
                      <thead className="bg-slate-50 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                        <tr>
                          <th className="px-4 py-3">Student Name</th>
                          <th className="px-4 py-3">Masked APAAR</th>
                          <th className="px-4 py-3">Programme</th>
                          <th className="px-4 py-3">Year</th>
                          <th className="px-4 py-3">Verification</th>
                          <th className="px-4 py-3">Email Dispatch</th>
                          <th className="px-4 py-3 text-right">Student Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {batchDetails.students?.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                              No student records attached to this batch.
                            </td>
                          </tr>
                        ) : (
                          batchDetails.students?.map((s) => (
                            <tr key={s.student_id} className="hover:bg-slate-50/50">
                              <td className="px-4 py-3 font-medium text-[#272727]">{s.name}</td>
                              <td className="px-4 py-3 font-mono text-slate-500">{s.apaar_id_masked}</td>
                              <td className="px-4 py-3 text-slate-600">{s.program}</td>
                              <td className="px-4 py-3 text-slate-500">{s.enrollment_year}</td>
                              <td className="px-4 py-3">
                                <StatusChip status={s.verification_status} label={s.verification_status_label} />
                              </td>
                              <td className="px-4 py-3">
                                <StatusChip status={s.email_status} label={s.email_status_label} />
                              </td>
                              <td className="px-4 py-3 text-right">
                                {s.verification_status === 'correction_requested' && s.corrections && (
                                  <button
                                    onClick={() => setCorrectionTarget(s)}
                                    className="px-2.5 py-1 bg-amber-100 hover:bg-amber-200 text-amber-900 font-semibold rounded text-[11px]"
                                  >
                                    Review Correction
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white p-12 rounded-2xl border border-dashed border-slate-300 text-center space-y-3">
                <Layers className="h-10 w-10 text-slate-300 mx-auto" />
                <h3 className="text-base font-semibold text-slate-600">Select or Initialize a Batch</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Select an academic submission cohort from the left panel to review student enrollment records, dispatch verification requests, or submit to AICTE.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Correction Review Modal */}
        {correctionTarget && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
            <div className="bg-white max-w-md w-full rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-base font-bold text-[#272727]">
                Review Student Proposed Correction
              </h3>
              <p className="text-xs text-slate-500">
                Student <strong>{correctionTarget.name}</strong> submitted these corrected values:
              </p>

              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs space-y-2">
                {Object.entries(correctionTarget.corrections || {}).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-slate-500 capitalize">{key.replace(/_/g, ' ')}:</span>
                    <span className="font-semibold text-teal-800">{String(val)}</span>
                  </div>
                ))}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Institutional Note (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Verified against physical grade sheet"
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-none"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  onClick={() => setCorrectionTarget(null)}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleReviewCorrection('reject')}
                  className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-800 font-semibold rounded-lg text-xs"
                >
                  Reject Proposal
                </button>
                <button
                  onClick={() => handleReviewCorrection('accept')}
                  className="px-3 py-1.5 bg-[#1b756b] hover:bg-[#145952] text-white font-semibold rounded-lg text-xs"
                >
                  Accept & Update Record
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
