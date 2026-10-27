import React, { useState, useEffect } from 'react';
import { Header, Footer, StatusChip } from '../../components/Layout';
import { aicteApi, publicApi } from '../../api/api';
import {
  ShieldAlert,
  Award,
  Layers,
  FileSearch,
  CheckCircle2,
  XCircle,
  Database,
  Lock,
  RefreshCw,
  Anchor,
  FileCheck2,
  AlertTriangle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

export function AictePortal() {
  const [activeTab, setActiveTab] = useState('overview'); // overview | batches | duplicates | security | flags
  const [trustScores, setTrustScores] = useState([]);
  const [batches, setBatches] = useState([]);
  const [duplicates, setDuplicates] = useState({ total_duplicates: 0, grouped_by_severity: {} });
  const [flags, setFlags] = useState([]);
  const [securityStatus, setSecurityStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState(null);

  // Review modal / action
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [scoresRes, batchesRes, dupsRes, flagsRes, honeyRes, chainRes, anchorRes] =
        await Promise.allSettled([
          aicteApi.getTrustScores(),
          aicteApi.getBatches(),
          aicteApi.getDuplicates(),
          aicteApi.getFlaggedRecords('open'),
          aicteApi.getHoneytokensStatus(),
          aicteApi.verifyChain(),
          aicteApi.verifyAnchored(),
        ]);

      if (scoresRes.status === 'fulfilled') setTrustScores(scoresRes.value.institutes || []);
      if (batchesRes.status === 'fulfilled') setBatches(batchesRes.value.batches || []);
      if (dupsRes.status === 'fulfilled') setDuplicates(dupsRes.value || {});
      if (flagsRes.status === 'fulfilled') setFlags(flagsRes.value.flagged_records || []);

      setSecurityStatus({
        honeytokens: honeyRes.status === 'fulfilled' ? honeyRes.value : null,
        chain: chainRes.status === 'fulfilled' ? chainRes.value : null,
        anchors: anchorRes.status === 'fulfilled' ? anchorRes.value : null,
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleApproveBatch = async (batchId) => {
    if (!confirm('Approve this batch and automatically digitally sign the AICTE EOA report?')) return;
    setActionLoading(true);
    try {
      await aicteApi.approveBatch(batchId);
      setActionMessage({ type: 'success', text: 'Batch approved! Digital certificate & signed PDF generated.' });
      fetchData();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectBatch = async (batchId) => {
    if (!rejectReason.trim()) {
      alert('Please enter a rejection reason for the institution.');
      return;
    }
    setActionLoading(true);
    try {
      await aicteApi.rejectBatch(batchId, rejectReason);
      setActionMessage({ type: 'info', text: 'Batch rejected with official feedback.' });
      setShowRejectInput(false);
      setRejectReason('');
      fetchData();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReviewFlag = async (flagId) => {
    try {
      await aicteApi.reviewFlag(flagId, 'Reviewed and acknowledged by AICTE Officer');
      setActionMessage({ type: 'success', text: `Flag #${flagId} marked as reviewed.` });
      fetchData();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleCreateCheckpoint = async () => {
    try {
      const res = await aicteApi.createCheckpoint();
      setActionMessage({
        type: 'success',
        text: `External audit checkpoint anchored to /data/checkpoints.log (Block: ${res.checkpoint?.checkpoint_block}).`,
      });
      fetchData();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  // Recharts Trust Score chart data
  const chartData = trustScores.slice(0, 8).map((inst) => ({
    name: inst.name.length > 18 ? inst.name.slice(0, 15) + '...' : inst.name,
    score: inst.trust_score,
  }));

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Regulator Header */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="inline-block px-2 py-0.5 rounded bg-indigo-100 text-indigo-800 text-xs font-semibold uppercase tracking-wider mb-2">
              National Regulatory Console
            </span>
            <h1 className="text-2xl font-bold text-[#1a3a5c]">AICTE Central Regulatory Authority</h1>
            <p className="text-xs text-slate-500 mt-1">
              Cross-institutional deduplication, automated trust scoring, cryptographic anchoring, and batch approval.
            </p>
          </div>

          <button
            onClick={fetchData}
            className="self-start sm:self-auto px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-xs font-semibold text-slate-700 flex items-center space-x-1.5 transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh State</span>
          </button>
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

        {/* Nav Tabs */}
        <div className="flex border-b border-slate-200 mb-6 space-x-4 text-xs font-semibold">
          {[
            { id: 'overview', label: 'Overview & Trust Scores', icon: Award },
            { id: 'batches', label: 'Batch Approvals', icon: Layers, badge: batches.filter(b => b.status === 'pushed').length },
            { id: 'duplicates', label: 'Cross-Institute Deduplication', icon: FileSearch, badge: duplicates.total_duplicates },
            { id: 'flags', label: 'Anomaly & Fraud Flags', icon: ShieldAlert, badge: flags.length },
            { id: 'security', label: 'Security & Hash Chain', icon: Lock },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`pb-3 border-b-2 flex items-center space-x-2 transition ${
                  active
                    ? 'border-[#0d9488] text-[#1a3a5c]'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? 'text-[#0d9488]' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
                {Boolean(tab.badge) && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-100 text-rose-800 font-bold">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* TAB 1: OVERVIEW & TRUST SCORES */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Quick Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-semibold text-slate-500 uppercase">Institutions Evaluated</span>
                <div className="text-2xl font-bold text-[#1a3a5c] mt-1">{trustScores.length}</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-semibold text-slate-500 uppercase">Pending Review Batches</span>
                <div className="text-2xl font-bold text-amber-600 mt-1">
                  {batches.filter((b) => b.status === 'pushed').length}
                </div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-semibold text-slate-500 uppercase">Duplicate Flags</span>
                <div className="text-2xl font-bold text-rose-600 mt-1">{duplicates.total_duplicates || 0}</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <span className="text-[11px] font-semibold text-slate-500 uppercase">Audit Chain Status</span>
                <div className="text-sm font-bold text-emerald-600 mt-2 flex items-center space-x-1">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Immutable Verified</span>
                </div>
              </div>
            </div>

            {/* Trust Scores Chart & Table */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="text-sm font-bold text-[#1a3a5c] mb-1">Institutional Trust Index</h3>
                <p className="text-[11px] text-slate-500 mb-4">
                  Dynamic 0-100 score computed from 7 forensic signals.
                </p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} />
                      <YAxis dataKey="name" type="category" tick={{ fontSize: 9 }} width={70} />
                      <Tooltip />
                      <Bar dataKey="score" fill="#0d9488" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="text-sm font-bold text-[#1a3a5c] mb-3">Institutional Breakdown</h3>
                <div className="border border-slate-200 rounded-lg overflow-x-auto">
                  <table className="w-full text-left text-xs divide-y divide-slate-200">
                    <thead className="bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                      <tr>
                        <th className="px-4 py-2.5">Institution</th>
                        <th className="px-4 py-2.5">AICTE Code</th>
                        <th className="px-4 py-2.5">State</th>
                        <th className="px-4 py-2.5 text-center">Trust Score</th>
                        <th className="px-4 py-2.5">Primary Deduction Drivers</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {trustScores.map((inst) => (
                        <tr key={inst.institute_id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-800">{inst.name}</td>
                          <td className="px-4 py-3 font-mono text-slate-500">{inst.aicte_code}</td>
                          <td className="px-4 py-3 text-slate-600">{inst.state || '—'}</td>
                          <td className="px-4 py-3 text-center">
                            <span
                              className={`inline-block px-2 py-0.5 rounded font-bold text-xs ${
                                inst.trust_score >= 80
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : inst.trust_score >= 60
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-rose-100 text-rose-800'
                              }`}
                            >
                              {inst.trust_score}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-[11px] text-slate-500">
                            {inst.breakdown?.capacity_mismatch_rate > 0 && (
                              <span className="text-rose-600 mr-2 font-medium">Over-capacity</span>
                            )}
                            {inst.breakdown?.duplicate_rate > 0 && (
                              <span className="text-amber-600 mr-2 font-medium">Duplicate hits</span>
                            )}
                            {inst.breakdown?.unverified_rate > 0 && (
                              <span className="text-purple-600 mr-2 font-medium">Unverified students</span>
                            )}
                            {inst.trust_score === 100 && <span className="text-emerald-600">Zero penalties</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: BATCH APPROVALS */}
        {activeTab === 'batches' && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div>
              <h2 className="text-base font-bold text-[#1a3a5c]">Institutional Submission Batches</h2>
              <p className="text-xs text-slate-500">
                Review batches submitted by institutions. Approving a batch generates a cryptographically signed AICTE EOA PDF.
              </p>
            </div>

            <div className="border border-slate-200 rounded-lg overflow-x-auto">
              <table className="w-full text-left text-xs divide-y divide-slate-200">
                <thead className="bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Batch Name</th>
                    <th className="px-4 py-3">Institution</th>
                    <th className="px-4 py-3">Students</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Regulatory Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {batches.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                        No submission batches recorded.
                      </td>
                    </tr>
                  ) : (
                    batches.map((b) => (
                      <tr key={b.batch_id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-semibold text-slate-800">{b.name}</td>
                        <td className="px-4 py-3 text-slate-600">{b.institute_name || `Inst #${b.institute_id}`}</td>
                        <td className="px-4 py-3 text-slate-500">{b.student_count} records</td>
                        <td className="px-4 py-3">
                          <StatusChip status={b.status} />
                        </td>
                        <td className="px-4 py-3 text-right space-x-2">
                          {b.status === 'pushed' && (
                            <>
                              <button
                                onClick={() => handleApproveBatch(b.batch_id)}
                                disabled={actionLoading}
                                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold shadow transition"
                              >
                                Approve & Sign EOA
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedBatch(b.batch_id);
                                  setShowRejectInput(true);
                                }}
                                disabled={actionLoading}
                                className="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-semibold shadow transition"
                              >
                                Reject
                              </button>
                            </>
                          )}
                          {b.status === 'approved' && (
                            <span className="text-xs text-emerald-700 font-semibold">✓ Signed & Approved</span>
                          )}
                          {b.status === 'rejected' && (
                            <span className="text-xs text-rose-600 font-medium">✕ Rejected</span>
                          )}
                          {b.status === 'draft' && (
                            <span className="text-xs text-slate-400 italic">Not yet submitted</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Rejection Modal Input */}
            {showRejectInput && (
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg space-y-3">
                <h4 className="text-xs font-bold text-rose-800">
                  Reject Batch #{selectedBatch} — Provide Regulatory Reason
                </h4>
                <textarea
                  rows="2"
                  placeholder="e.g. Over-enrolled past approved intake, or unverified duplicate APAAR IDs detected..."
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  className="w-full p-2 text-xs border border-rose-300 rounded focus:ring-2 focus:ring-rose-500 outline-none"
                />
                <div className="flex justify-end space-x-2">
                  <button
                    onClick={() => setShowRejectInput(false)}
                    className="px-3 py-1 bg-white border border-slate-300 rounded text-xs text-slate-600"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleRejectBatch(selectedBatch)}
                    disabled={actionLoading}
                    className="px-3 py-1 bg-rose-700 hover:bg-rose-800 text-white rounded text-xs font-semibold"
                  >
                    Confirm Rejection
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: DEDUPLICATION */}
        {activeTab === 'duplicates' && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div>
              <h2 className="text-base font-bold text-[#1a3a5c]">Cross-Institutional Deduplication</h2>
              <p className="text-xs text-slate-500">
                Exact APAAR matches across different institutions indicate dual-enrollment fraud. Fuzzy token sort matches highlight identity discrepancies.
              </p>
            </div>

            <div className="space-y-4">
              {/* Confirmed Duplicates */}
              <div>
                <h3 className="text-xs font-bold text-rose-800 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Confirmed Cross-Institute Duplicates ({duplicates.grouped_by_severity?.confirmed?.length || 0})</span>
                </h3>
                <div className="border border-rose-200 rounded-lg overflow-x-auto">
                  <table className="w-full text-left text-xs divide-y divide-rose-100">
                    <thead className="bg-rose-50 text-rose-900 font-semibold uppercase text-[10px]">
                      <tr>
                        <th className="px-4 py-2.5">Flag ID</th>
                        <th className="px-4 py-2.5">Student Record ID(s)</th>
                        <th className="px-4 py-2.5">Fraud Signal Details</th>
                        <th className="px-4 py-2.5">Severity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-rose-50 bg-white">
                      {duplicates.grouped_by_severity?.confirmed?.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="px-4 py-4 text-center text-slate-400">
                            No confirmed cross-institute duplicates found.
                          </td>
                        </tr>
                      ) : (
                        duplicates.grouped_by_severity?.confirmed?.map((item) => (
                          <tr key={item.id} className="hover:bg-rose-50/50">
                            <td className="px-4 py-3 font-mono text-slate-500">#{item.id}</td>
                            <td className="px-4 py-3 font-semibold text-slate-800">{item.record_id}</td>
                            <td className="px-4 py-3 text-rose-700 font-medium">{item.flag_reason}</td>
                            <td className="px-4 py-3">
                              <StatusChip status={item.severity} />
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Suspected Fuzzy Duplicates */}
              <div>
                <h3 className="text-xs font-bold text-amber-800 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Suspected Identity / Re-Upload Flags ({duplicates.grouped_by_severity?.needs_review?.length || 0})</span>
                </h3>
                <div className="border border-slate-200 rounded-lg overflow-x-auto">
                  <table className="w-full text-left text-xs divide-y divide-slate-100">
                    <thead className="bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                      <tr>
                        <th className="px-4 py-2.5">Flag ID</th>
                        <th className="px-4 py-2.5">Record ID(s)</th>
                        <th className="px-4 py-2.5">Description</th>
                        <th className="px-4 py-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {duplicates.grouped_by_severity?.needs_review?.map((item) => (
                        <tr key={item.id}>
                          <td className="px-4 py-2.5 font-mono text-slate-400">#{item.id}</td>
                          <td className="px-4 py-2.5 font-medium text-slate-700">{item.record_id}</td>
                          <td className="px-4 py-2.5 text-slate-600">{item.flag_reason}</td>
                          <td className="px-4 py-2.5">
                            <StatusChip status={item.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: ANOMALY & FRAUD FLAGS */}
        {activeTab === 'flags' && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div>
              <h2 className="text-base font-bold text-[#1a3a5c]">Open Anomaly & Compliance Flags</h2>
              <p className="text-xs text-slate-500">
                Covers geographic mismatches, lifecycle timeline implausibilities, and honeytoken canary hits.
              </p>
            </div>

            <div className="border border-slate-200 rounded-lg overflow-x-auto">
              <table className="w-full text-left text-xs divide-y divide-slate-200">
                <thead className="bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Flag ID</th>
                    <th className="px-4 py-3">Target Entity</th>
                    <th className="px-4 py-3">Reason / Description</th>
                    <th className="px-4 py-3">Severity</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {flags.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                        No open flags pending regulatory review.
                      </td>
                    </tr>
                  ) : (
                    flags.map((f) => (
                      <tr key={f.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-mono text-slate-500">#{f.id}</td>
                        <td className="px-4 py-3 font-semibold text-slate-800">
                          {f.record_type} #{f.record_id}
                        </td>
                        <td className="px-4 py-3 text-slate-600">{f.flag_reason}</td>
                        <td className="px-4 py-3">
                          <StatusChip status={f.severity} />
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => handleReviewFlag(f.id)}
                            className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold"
                          >
                            Mark Reviewed
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: SECURITY & IMMUTABILITY */}
        {activeTab === 'security' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Honeytokens Canary Monitor */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center space-x-2">
                  <ShieldAlert className="h-5 w-5 text-indigo-600" />
                  <h3 className="text-sm font-bold text-[#1a3a5c]">Honeytoken Canary IDs</h3>
                </div>
                <p className="text-xs text-slate-500">
                  Reserved APAAR IDs generated with valid format but never assigned. Any appearance in uploads proves data scraping or unauthorized database access.
                </p>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center text-xs">
                  <div>
                    <span className="font-semibold text-slate-700 block">Canary Trigger Status:</span>
                    <span className="text-slate-500 text-[11px]">
                      {securityStatus?.honeytokens?.triggered_count || 0} of{' '}
                      {securityStatus?.honeytokens?.total_honeytokens || 10} canaries triggered
                    </span>
                  </div>
                  {securityStatus?.honeytokens?.triggered_count > 0 ? (
                    <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold text-xs">
                      ALERT TRIGGERED
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-medium text-xs">
                      All Quiet
                    </span>
                  )}
                </div>
              </div>

              {/* External Hash-Chain Checkpointing */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center space-x-2">
                  <Anchor className="h-5 w-5 text-[#0d9488]" />
                  <h3 className="text-sm font-bold text-[#1a3a5c]">External Hash-Chain Anchoring</h3>
                </div>
                <p className="text-xs text-slate-500">
                  Every 20 audit blocks, the chain-head hash is anchored to an append-only external log (/data/checkpoints.log), making historical rewrites provably detectable.
                </p>

                <div className="flex items-center justify-between pt-2">
                  <div className="text-xs text-slate-600">
                    <div>Chain blocks: {securityStatus?.chain?.total_audit_blocks || 0}</div>
                    <div className="text-emerald-700 font-semibold mt-0.5">
                      {securityStatus?.anchors?.tamper_detected
                        ? '⚠ TAMPER DETECTED VIA EXTERNAL LOG'
                        : '✓ Anchored Integrity Verified'}
                    </div>
                  </div>

                  <button
                    onClick={handleCreateCheckpoint}
                    className="px-3 py-1.5 bg-[#1a3a5c] hover:bg-[#122942] text-white rounded text-xs font-semibold shadow transition"
                  >
                    Trigger Anchor
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
