import React, { useState } from 'react';
import { Header, Footer } from '../../components/Layout';
import { publicApi } from '../../api/api';
import { ShieldCheck, FileCheck, CheckCircle2, XCircle, Search } from 'lucide-react';

export function DocumentVerifier() {
  const [apaarInput, setApaarInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [signedPack, setSignedPack] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');

  const handleFetchDocument = async (e) => {
    e.preventDefault();
    if (!apaarInput.trim()) return;
    setLoading(true);
    setError('');
    setSignedPack(null);
    setVerificationResult(null);

    try {
      const res = await publicApi.getDocumentByApaar(apaarInput.trim());
      setSignedPack(res);
    } catch (err) {
      setError(err.message || 'No registered student found for this APAAR ID.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (docToVerify) => {
    setVerifying(true);
    setVerificationResult(null);
    try {
      const res = await publicApi.verifyDocument(docToVerify || signedPack.document, signedPack.signature);
      setVerificationResult(res);
    } catch (err) {
      setVerificationResult({ is_valid: false, status: 'TAMPER_DETECTED' });
    } finally {
      setVerifying(false);
    }
  };

  const handleTamper = (field, value) => {
    if (!signedPack) return;
    setSignedPack({
      ...signedPack,
      document: {
        ...signedPack.document,
        [field]: value,
      },
    });
    setVerificationResult(null);
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-50">
      <Header />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 bg-[#d7f9e4] rounded-2xl text-[#1b756b] mb-1">
            <ShieldCheck className="h-8 w-8" />
          </div>
          <h1 className="text-2xl font-bold text-[#272727]">Public RSA Digital Certificate Verifier</h1>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Test mathematical authenticity: verify RSA-2048 public key signatures or modify any character to observe instant tamper detection.
          </p>
        </div>

        {/* Lookup Box */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <form onSubmit={handleFetchDocument} className="flex gap-2">
            <input
              type="text"
              placeholder="Enter 12-digit APAAR ID"
              value={apaarInput}
              onChange={(e) => setApaarInput(e.target.value)}
              className="flex-1 px-4 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-[#1b756b] outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-[#1b756b] hover:bg-[#145952] text-white rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50 flex items-center space-x-1"
            >
              <Search className="h-4 w-4" />
              <span>{loading ? 'Searching...' : 'Lookup & Sign'}</span>
            </button>
          </form>

          {error && <div className="mt-3 text-xs text-rose-600 font-medium">{error}</div>}
        </div>

        {signedPack && (
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-4 border-b border-slate-200 gap-4">
              <div>
                <h2 className="text-base font-bold text-[#272727]">Digitally Signed Academic Credential</h2>
                <span className="text-[11px] font-mono text-slate-400">
                  SHA-256 Digest: {signedPack.hash?.slice(0, 36)}...
                </span>
              </div>

              {signedPack.qr_code_base64 && (
                <div className="text-center">
                  <img
                    src={`data:image/png;base64,${signedPack.qr_code_base64}`}
                    alt="Certificate QR"
                    className="h-16 w-16 border p-0.5 rounded-lg"
                  />
                  <span className="text-[9px] text-slate-400 block mt-0.5">Scannable QR</span>
                </div>
              )}
            </div>

            {/* Document Payload Form */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Student Name</label>
                <input
                  type="text"
                  value={signedPack.document.name}
                  onChange={(e) => handleTamper('name', e.target.value)}
                  className="w-full px-3 py-1.5 border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">APAAR ID</label>
                <input
                  type="text"
                  value={signedPack.document.apaar_id}
                  onChange={(e) => handleTamper('apaar_id', e.target.value)}
                  className="w-full px-3 py-1.5 border border-slate-300 rounded-lg font-mono outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Institution</label>
                <input
                  type="text"
                  value={signedPack.document.institute}
                  onChange={(e) => handleTamper('institute', e.target.value)}
                  className="w-full px-3 py-1.5 border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Programme / Degree</label>
                <input
                  type="text"
                  value={signedPack.document.program}
                  onChange={(e) => handleTamper('program', e.target.value)}
                  className="w-full px-3 py-1.5 border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-[#1b756b]"
                />
              </div>
            </div>

            <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900">
              <span className="font-bold">Cryptographic Tamper Test:</span> Edit any letter above and click Verify to observe mathematical signature failure.
            </div>

            <div className="flex justify-center pt-2">
              <button
                onClick={() => handleVerify(signedPack.document)}
                disabled={verifying}
                className="px-6 py-2.5 bg-[#1b756b] hover:bg-[#145952] text-white rounded-xl text-xs font-bold shadow-sm transition disabled:opacity-50 flex items-center space-x-2"
              >
                <FileCheck className="h-4 w-4" />
                <span>{verifying ? 'Verifying RSA Signature...' : 'Verify Cryptographic Signature'}</span>
              </button>
            </div>

            {verificationResult && (
              <div
                className={`p-4 rounded-xl text-xs font-semibold flex items-center space-x-3 border ${
                  verificationResult.is_valid
                    ? 'bg-emerald-50 text-emerald-900 border-emerald-300'
                    : 'bg-rose-50 text-rose-900 border-rose-300'
                }`}
              >
                {verificationResult.is_valid ? (
                  <>
                    <CheckCircle2 className="h-6 w-6 text-emerald-600 flex-shrink-0" />
                    <div>
                      <div className="font-bold text-sm">CERTIFICATE AUTHENTIC & UNTAMPERED</div>
                      <div className="text-[11px] text-emerald-700 font-normal">
                        RSA-2048 public key verified the document SHA-256 digest with mathematical certainty.
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <XCircle className="h-6 w-6 text-rose-600 flex-shrink-0" />
                    <div>
                      <div className="font-bold text-sm">TAMPER DETECTED / INVALID SIGNATURE</div>
                      <div className="text-[11px] text-rose-700 font-normal">
                        Document payload does not match the signed cryptographic digest. Verification failed.
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
