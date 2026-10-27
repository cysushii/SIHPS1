import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Header, Footer, StatusChip } from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { instituteApi } from '../../api/api';
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
  ExternalLink,
  RefreshCw,
  Mail,
  CheckCircle,
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
  const [capacityData, setCapacityData] = useState(null);

  // Ingestion form state
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);

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

  const fetchCapacity = async () => {
    if (!user?.institute_id) return;
    try {
      const cap = await instituteApi.getCapacity(user.institute_id);
      setCapacityData(cap);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchBatches();
    fetchCapacity();
  }, [user]);

  const handleCreateBatch = async (e) => {
    e.preventDefault();
    if (!newBatchName.trim()) return;
    setCreatingBatch(true);
    try {
      await instituteApi.createBatch(newBatchName, user.institute_id);
      setNewBatchName('');
      setActionMessage({ type: 'success', text: 'Batch created successfully!' });
      fetchBatches();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setCreatingBatch(false);
    }
  };

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

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', uploadFile);
    if (user?.institute_id) {
      formData.append('institute_id', user.institute_id);
    }

    try {
      const res = await instituteApi.uploadStudents(formData);
      setUploadResult(res);
      setActionMessage({ type: 'success', text: `Ingested ${res.inserted || 0} students with full verification.` });
      // If a batch is selected and in draft, prompt or add them
      if (selectedBatch) {
        handleSelectBatch(selectedBatch);
      }
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setUploading(false);
    }
  };

  const handlePushBatch = async (batchId) => {
    if (!confirm('Are you sure you want to push this batch to AICTE for official regulatory review?')) return;
    try {
      await instituteApi.pushBatch(batchId);
      setActionMessage({ type: 'success', text: 'Batch pushed to AICTE successfully!' });
      fetchBatches();
      if (selectedBatch === batchId) handleSelectBatch(batchId);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleGenerateTokens = async (batchId) => {
    try {
      const res = await instituteApi.generateTokens(batchId);
      setActionMessage({ type: 'success', text: `Generated ${res.generated_count} self-verification links.` });
      handleSelectBatch(batchId);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleSendEmails = async (batchId) => {
    try {
      const res = await instituteApi.sendVerificationEmails(batchId);
      setActionMessage({
        type: 'success',
        text: `Verification emails dispatched: ${res.sent} sent, ${res.skipped} skipped (dry-run/mock).`,
      });
      handleSelectBatch(batchId);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleMarkUnresponsive = async (batchId) => {
    try {
      const res = await instituteApi.markUnresponsive(batchId);
      setActionMessage({
        type: 'info',
        text: `Demo Action: Marked ${res.marked_unresponsive} pending tokens as unresponsive.`,
      });
      handleSelectBatch(batchId);
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
      a.download = `AICTE_Approval_Batch_${batchId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleNotifyStudents = async (batchId) => {
    try {
      const res = await instituteApi.notifyStudents(batchId);
      setActionMessage({
        type: 'success',
        text: `Completion emails dispatched to approved students: ${res.sent} sent, ${res.skipped} mocked.`,
      });
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Institute Info Header */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="inline-block px-2 py-0.5 rounded bg-teal-100 text-teal-800 text-xs font-semibold uppercase tracking-wider mb-2">
              Institute Operations Portal
            </span>
            <h1 className="text-2xl font-bold text-[#1a3a5c]">
              Institution #{user?.institute_id || '—'} Dashboard
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Manage student datasets, verify APAAR IDs, create submission batches, and interact with AICTE.
            </p>
          </div>

          {/* Real-World Capacity Status Card */}
          {capacityData && (
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 min-w-[260px]">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide block mb-1">
                AICTE Intake Approval
              </span>
              {capacityData.status === 'no_course_data_available' ? (
                <div>
                  <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 inline-block mb-1">
                    Multi-Year Extended EOA
                  </span>
                  <p className="text-[11px] text-slate-500">Autonomous / Deemed status (no course rows required)</p>
                </div>
              ) : (
                <div>
                  <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 inline-block mb-1">
                    Standard Course Intake Active
                  </span>
                  <p className="text-[11px] text-slate-500">
                    {capacityData.programs?.length || 0} approved programme streams verified
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Global Action Banner */}
        {actionMessage && (
          <div
            className={`mb-6 p-4 rounded-lg text-xs font-medium border flex items-center justify-between ${
              actionMessage.type === 'error'
                ? 'bg-rose-50 text-rose-800 border-rose-200'
                : actionMessage.type === 'info'
                ? 'bg-purple-50 text-purple-800 border-purple-200'
                : 'bg-emerald-50 text-emerald-800 border-emerald-200'
            }`}
          >
            <span>{actionMessage.text}</span>
            <button
              onClick={() => setActionMessage(null)}
              className="text-slate-400 hover:text-slate-600 font-bold ml-4"
            >
              ×
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Upload + Batch Management */}
          <div className="space-y-6">
            {/* Student Upload Box */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center space-x-2 mb-3">
                <Upload className="h-5 w-5 text-[#0d9488]" />
                <h2 className="text-base font-bold text-[#1a3a5c]">Upload Student Roster</h2>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Upload CSV or Excel containing student APAAR IDs, names, and program info.
              </p>

              <form onSubmit={handleFileUpload} className="space-y-3">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  required
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  className="block w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-teal-50 file:text-[#0d9488] hover:file:bg-teal-100 cursor-pointer"
                />

                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="w-full bg-[#0d9488] hover:bg-[#0f766e] text-white py-2 px-3 rounded-lg text-xs font-semibold shadow transition disabled:opacity-50 flex items-center justify-center space-x-1.5"
                >
                  <FileSpreadsheet className="h-4 w-4" />
                  <span>{uploading ? 'Processing Data...' : 'Ingest & Validate Roster'}</span>
                </button>
              </form>

              {uploadResult && (
                <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                  <div className="font-semibold text-slate-700">Ingestion Results:</div>
                  <div className="text-emerald-700">✓ Inserted: {uploadResult.inserted}</div>
                  {uploadResult.rejected > 0 && (
                    <div className="text-rose-600 font-medium">✕ Rejected: {uploadResult.rejected}</div>
                  )}
                  {uploadResult.flags_created > 0 && (
                    <div className="text-amber-700">⚠ Anomaly Flags Raised: {uploadResult.flags_created}</div>
                  )}
                </div>
              )}
            </div>

            {/* Create New Batch */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center space-x-2 mb-3">
                <PlusCircle className="h-5 w-5 text-[#1a3a5c]" />
                <h2 className="text-base font-bold text-[#1a3a5c]">Create Submission Batch</h2>
              </div>

              <form onSubmit={handleCreateBatch} className="space-y-3">
                <div>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 2024-25 CSE & ECE Regular Batch"
                    value={newBatchName}
                    onChange={(e) => setNewBatchName(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0d9488] outline-none"
                  />
                </div>
                <button
                  type="submit"
                  disabled={creatingBatch || !newBatchName.trim()}
                  className="w-full bg-[#1a3a5c] hover:bg-[#122942] text-white py-2 px-3 rounded-lg text-xs font-semibold shadow transition disabled:opacity-50"
                >
                  {creatingBatch ? 'Creating Batch...' : 'Initialize New Batch'}
                </button>
              </form>
            </div>

            {/* Batches List */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <Layers className="h-5 w-5 text-[#1a3a5c]" />
                  <h2 className="text-base font-bold text-[#1a3a5c]">Your Batches</h2>
                </div>
                <button
                  onClick={fetchBatches}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded"
                  title="Refresh"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              </div>

              {loading ? (
                <div className="text-center py-6 text-xs text-slate-400">Loading batches...</div>
              ) : batches.length === 0 ? (
                <div className="text-center py-6 text-xs text-slate-400">
                  No batches created yet. Create your first batch above.
                </div>
              ) : (
                <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
                  {batches.map((b) => (
                    <div
                      key={b.batch_id}
                      onClick={() => handleSelectBatch(b.batch_id)}
                      className={`p-3 rounded-lg cursor-pointer transition flex items-center justify-between text-xs ${
                        selectedBatch === b.batch_id
                          ? 'bg-teal-50 border border-teal-200'
                          : 'hover:bg-slate-50'
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="font-semibold text-slate-800">{b.name}</div>
                        <div className="text-slate-400 flex items-center space-x-2">
                          <span>{b.student_count} students</span>
                          <span>•</span>
                          <StatusChip status={b.status} />
                        </div>
                      </div>
                      <ChevronRight className="h-4 w-4 text-slate-400" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right 2 Columns: Batch Detail & Lifecycle Actions */}
          <div className="lg:col-span-2 space-y-6">
            {selectedBatch && batchDetails ? (
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
                {/* Batch Overview Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-4">
                  <div>
                    <div className="flex items-center space-x-3 mb-1">
                      <h2 className="text-xl font-bold text-[#1a3a5c]">{batchDetails.name}</h2>
                      <StatusChip status={batchDetails.status} />
                    </div>
                    <span className="text-xs text-slate-400">
                      Batch ID: #{batchDetails.batch_id} • {batchDetails.student_count} Students Enrolled
                    </span>
                  </div>

                  {/* Batch Action Buttons */}
                  <div className="flex flex-wrap items-center gap-2">
                    {batchDetails.status === 'draft' && (
                      <>
                        <button
                          onClick={() => handleGenerateTokens(batchDetails.batch_id)}
                          className="bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1"
                        >
                          <Users className="h-3.5 w-3.5" />
                          <span>Generate Self-Verify Links</span>
                        </button>
                        <button
                          onClick={() => handlePushBatch(batchDetails.batch_id)}
                          className="bg-[#1a3a5c] hover:bg-[#122942] text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1"
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
                          className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1"
                        >
                          <FileCheck2 className="h-3.5 w-3.5" />
                          <span>Download Signed AICTE EOA PDF</span>
                        </button>
                        <button
                          onClick={() => handleNotifyStudents(batchDetails.batch_id)}
                          className="bg-[#1a3a5c] hover:bg-[#122942] text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1"
                        >
                          <Mail className="h-3.5 w-3.5" />
                          <span>Notify Students</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Batch Rejection Reason if any */}
                {batchDetails.reject_reason && (
                  <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-xs">
                    <span className="font-bold text-rose-800 block mb-1">AICTE Regulatory Feedback (Rejected):</span>
                    <p className="text-rose-700">{batchDetails.reject_reason}</p>
                  </div>
                )}

                {/* Self-Verification Operations Toolbar */}
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="font-semibold text-slate-700 block">Student Self-Verification Links</span>
                    <span className="text-[11px] text-slate-500">
                      In production, students receive this via email. For demo, test the link directly below.
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleSendEmails(batchDetails.batch_id)}
                      className="px-2.5 py-1.5 bg-white border border-slate-300 hover:bg-slate-100 rounded text-slate-700 font-medium transition"
                    >
                      Send / Mock Emails
                    </button>
                    <button
                      onClick={() => handleMarkUnresponsive(batchDetails.batch_id)}
                      className="px-2.5 py-1.5 bg-purple-50 border border-purple-200 hover:bg-purple-100 rounded text-purple-700 font-medium transition"
                    >
                      Simulate Unresponsive
                    </button>
                  </div>
                </div>

                {/* Students Table */}
                <div>
                  <h3 className="text-sm font-bold text-slate-800 mb-3">Enrolled Student Records</h3>
                  <div className="border border-slate-200 rounded-lg overflow-x-auto">
                    <table className="w-full text-left text-xs divide-y divide-slate-200">
                      <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                        <tr>
                          <th className="px-4 py-3">Student Name</th>
                          <th className="px-4 py-3">APAAR ID</th>
                          <th className="px-4 py-3">Programme</th>
                          <th className="px-4 py-3">Year</th>
                          <th className="px-4 py-3">Verification</th>
                          <th className="px-4 py-3">Self-Verify URL</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {batchDetails.students?.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                              No students attached to this batch yet.
                            </td>
                          </tr>
                        ) : (
                          batchDetails.students?.map((s) => (
                            <tr key={s.student_id} className="hover:bg-slate-50">
                              <td className="px-4 py-3 font-medium text-slate-800">{s.name}</td>
                              <td className="px-4 py-3 font-mono text-slate-600">{s.apaar_id}</td>
                              <td className="px-4 py-3 text-slate-600">{s.program}</td>
                              <td className="px-4 py-3 text-slate-500">{s.enrollment_year}</td>
                              <td className="px-4 py-3">
                                <StatusChip status={s.verification_status} />
                              </td>
                              <td className="px-4 py-3">
                                {s.verify_token ? (
                                  <Link
                                    to={`/verify/${s.verify_token}`}
                                    target="_blank"
                                    className="text-teal-600 hover:text-teal-800 font-medium inline-flex items-center space-x-1"
                                  >
                                    <span>Open Link</span>
                                    <ExternalLink className="h-3 w-3" />
                                  </Link>
                                ) : (
                                  <span className="text-slate-400 italic">Not generated</span>
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
              <div className="bg-white p-12 rounded-xl border border-dashed border-slate-300 text-center space-y-3">
                <Layers className="h-10 w-10 text-slate-300 mx-auto" />
                <h3 className="text-base font-semibold text-slate-600">Select or Create a Batch</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Click on an existing batch from the list on the left to review students, dispatch verification links, or submit to AICTE.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
