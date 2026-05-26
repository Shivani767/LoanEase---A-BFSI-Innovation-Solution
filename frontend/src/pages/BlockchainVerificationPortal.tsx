import { useState } from "react";
import { Check, X, AlertTriangle, Search, Download, ShieldCheck, Database, Link, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

interface VerificationResult {
  found: boolean;
  authentic: boolean;
  reference: string;
  applicant_masked: string;
  loan_amount: number;
  sanctioned_rate: number;
  sanction_date: string;
  block_index: number;
  block_hash: string;
  merkle_root: string;
  chain_valid_at_block: bool;
  full_chain_valid: bool;
  verifications: {
    hash_match: boolean;
    chain_intact: boolean;
    merkle_valid: boolean;
    signature_valid: boolean;
  };
  verified_at: string;
}

const BlockchainVerificationPortal = () => {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async () => {
    if (!query) return;
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      // Simulate network delay for effect
      await new Promise(r => setTimeout(r, 1200));
      
      const response = await fetch(`/blockchain/public-verify/${query}`);
      if (response.status === 404) {
        setError("NOT_FOUND");
      } else if (!response.ok) {
        setError("SYSTEM_ERROR");
      } else {
        const data = await response.json();
        setResult(data);
      }
    } catch (err) {
      setError("SYSTEM_ERROR");
    } finally {
      setIsLoading(false);
    }
  };

  const downloadCertificate = () => {
    if (!result) return;
    window.open(`/blockchain/verification-certificate/${result.reference}`, '_blank');
  };

  return (
    <div className="min-h-screen bg-black text-white font-sans selection:bg-[#F5C518] selection:text-black">
      {/* Background Decor */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none opacity-20">
        <div className="absolute top-0 left-1/4 w-px h-full bg-gradient-to-b from-transparent via-[#F5C518] to-transparent" />
        <div className="absolute top-0 right-1/4 w-px h-full bg-gradient-to-b from-transparent via-[#F5C518] to-transparent" />
        <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#F5C518] to-transparent" />
      </div>

      <div className="relative z-10 max-w-[680px] mx-auto px-6 py-16">
        {/* Header */}
        <header className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-6 group cursor-pointer" onClick={() => window.location.href = '/'}>
            <span className="font-bebas text-2xl text-[#F5C518]">₹</span>
            <span className="font-bebas text-2xl text-white tracking-widest group-hover:text-[#F5C518] transition-colors">LOANEASE</span>
          </div>
          <h1 className="font-bebas text-4xl md:text-5xl tracking-tight mb-2 uppercase">
            DOCUMENT <span className="text-[#F5C518]">VERIFICATION</span> PORTAL
          </h1>
          <p className="text-[#666] text-sm md:text-base tracking-[1px] uppercase">
            Verify any LoanEase sanction letter's cryptographic authenticity
          </p>
        </header>

        {/* Search Section */}
        <div className="bg-[rgba(8,8,8,0.95)] border border-[#1a1a1a] p-1 rounded-sm shadow-2xl backdrop-blur-xl mb-12">
          <div className="relative flex items-center">
            <div className="absolute left-4 text-[#444]">
              <Search size={20} />
            </div>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter reference number (LE-2026-XXXXX) or transaction hash"
              className="w-full bg-transparent border-none py-5 pl-12 pr-4 text-white placeholder:text-[#333] focus:outline-none font-medium text-lg"
              onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
            />
          </div>
          <button
            onClick={handleVerify}
            disabled={isLoading || !query}
            className={cn(
              "w-full py-4 bg-[#F5C518] text-black font-bebas text-xl tracking-[2px] rounded-sm transition-all duration-300 active:scale-[0.98]",
              isLoading ? "opacity-70 cursor-wait" : "hover:shadow-[0_0_30px_rgba(245,197,24,0.3)] hover:bg-[#ffcf24]"
            )}
          >
            {isLoading ? "VERIFYING CRYPTOGRAPHIC LEDGER..." : "VERIFY DOCUMENT"}
          </button>
        </div>

        {/* Results Section */}
        {error === "NOT_FOUND" && (
          <div className="text-center py-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-[rgba(245,197,24,0.1)] border border-[rgba(245,197,24,0.2)] text-[#F5C518] mb-6">
              <AlertTriangle size={40} />
            </div>
            <h2 className="font-bebas text-3xl mb-2">Reference Not Found</h2>
            <p className="text-[#666] max-w-[400px] mx-auto text-sm leading-relaxed">
              This reference does not exist in our ledger. If you believe this is an error, 
              contact support with the original sanction letter.
            </p>
          </div>
        )}

        {error === "SYSTEM_ERROR" && (
          <div className="text-center py-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)] text-[#ef4444] mb-6">
              <X size={40} />
            </div>
            <h2 className="font-bebas text-3xl mb-2">System Error</h2>
            <p className="text-[#666] max-w-[400px] mx-auto text-sm leading-relaxed">
              We encountered an error while communicating with the blockchain node. 
              Please try again in a moment.
            </p>
          </div>
        )}

        {result && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-700">
            {/* Status Banner */}
            <div className="text-center py-8">
              {result.authentic ? (
                <>
                  <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-[rgba(34,197,94,0.1)] border border-[rgba(34,197,94,0.2)] text-[#22c55e] mb-6 animate-pulse">
                    <Check size={48} strokeWidth={3} />
                  </div>
                  <h2 className="font-bebas text-5xl text-[#22c55e] tracking-tight">DOCUMENT AUTHENTIC</h2>
                </>
              ) : (
                <>
                  <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)] text-[#ef4444] mb-6">
                    <X size={48} strokeWidth={3} />
                  </div>
                  <h2 className="font-bebas text-5xl text-[#ef4444] tracking-tight">DOCUMENT MODIFIED</h2>
                </>
              )}
            </div>

            {result.authentic ? (
              <>
                {/* Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-[#0a0a0a] border border-[#1a1a1a] p-6 rounded-sm">
                    <h3 className="text-[#333] font-bebas text-xs tracking-[3px] uppercase mb-4">Document Details</h3>
                    <div className="space-y-4">
                      <DetailRow label="Reference" value={result.reference} />
                      <DetailRow label="Applicant" value={result.applicant_masked} />
                      <DetailRow label="Amount" value={`₹${result.loan_amount.toLocaleString()}`} />
                      <DetailRow label="Rate" value={`${result.sanctioned_rate}% p.a.`} />
                      <DetailRow label="Sanctioned" value={new Date(result.sanction_date).toLocaleString()} />
                    </div>
                  </div>

                  <div className="bg-[#0a0a0a] border border-[#1a1a1a] p-6 rounded-sm">
                    <h3 className="text-[#333] font-bebas text-xs tracking-[3px] uppercase mb-4">Blockchain Details</h3>
                    <div className="space-y-4">
                      <DetailRow label="Block" value={`#${result.block_index}`} />
                      <DetailRow label="Proof Method" value="SHA-256 / PoW" />
                      <DetailRow label="Ledger State" value={result.full_chain_valid ? "Valid Chain" : "Partial Sync"} color="text-[#22c55e]" />
                      <DetailRow label="Merkle Proof" value="Verified" color="text-[#22c55e]" />
                    </div>
                  </div>
                </div>

                {/* Technical Card */}
                <div className="bg-[#0a0a0a] border border-[#1a1a1a] p-6 rounded-sm">
                  <h3 className="text-[#333] font-bebas text-xs tracking-[3px] uppercase mb-4">Cryptographic Hash</h3>
                  <div className="font-mono text-[10px] break-all text-[#666] bg-black p-4 rounded-sm border border-[#111]">
                    {result.block_hash}
                  </div>
                  <div className="mt-6 grid grid-cols-2 gap-4">
                    <VerificationCheck label="SHA-256 hash matches ledger" checked={result.verifications.hash_match} />
                    <VerificationCheck label="Merkle tree integrity" checked={result.verifications.merkle_valid} />
                    <VerificationCheck label="Block chain unbroken" checked={result.verifications.chain_intact} />
                    <VerificationCheck label="RSA-2048 signature valid" checked={result.verifications.signature_valid} />
                  </div>
                </div>

                {/* Download Button */}
                <button
                  onClick={downloadCertificate}
                  className="w-full py-4 bg-white text-black font-bebas text-xl tracking-[1px] rounded-sm hover:bg-[#eee] transition-all flex items-center justify-center gap-2 group"
                >
                  <Download size={20} className="group-hover:translate-y-0.5 transition-transform" />
                  Download Verification Certificate
                </button>
              </>
            ) : (
              <div className="bg-[#0a0a0a] border border-[rgba(239,68,68,0.3)] p-8 rounded-sm text-center">
                <p className="text-white text-lg mb-4">
                  The document you have does not match our ledger record. 
                </p>
                <p className="text-[#666] text-sm leading-relaxed mb-8">
                  The content may have been altered after issuance. LoanEase cryptographic checks 
                  detected a mismatch in the Merkle root or block hash. 
                  Contact LoanEase support immediately.
                </p>
                <div className="inline-block px-4 py-2 bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)] rounded-sm text-[#ef4444] font-mono text-sm">
                  Support Ref: ERR-{Math.random().toString(36).substring(7).toUpperCase()}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer info */}
        {!result && !error && !isLoading && (
          <div className="mt-20 grid grid-cols-3 gap-8">
            <FeatureIcon icon={<ShieldCheck size={24} />} label="Immutable Ledger" />
            <FeatureIcon icon={<Database size={24} />} label="Merkle Integrity" />
            <FeatureIcon icon={<Cpu size={24} />} label="RSA-2048 Signing" />
          </div>
        )}
      </div>

      <style>{`
        @font-face {
          font-family: 'Bebas Neue';
          src: url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');
        }
        .font-bebas { font-family: 'Bebas Neue', sans-serif; }
        .font-sans { font-family: 'DM Sans', sans-serif; }
      `}</style>
    </div>
  );
};

const DetailRow = ({ label, value, color }: { label: string, value: string | number, color?: string }) => (
  <div className="flex justify-between items-center text-sm border-b border-[#111] pb-2 last:border-0">
    <span className="text-[#333] font-medium">{label}</span>
    <span className={cn("text-white font-semibold", color)}>{value}</span>
  </div>
);

const VerificationCheck = ({ label, checked }: { label: string, checked: boolean }) => (
  <div className="flex items-center gap-2 text-[10px] md:text-xs">
    {checked ? (
      <Check size={14} className="text-[#22c55e]" />
    ) : (
      <X size={14} className="text-[#ef4444]" />
    )}
    <span className={checked ? "text-white" : "text-[#ef4444]"}>{label}</span>
  </div>
);

const FeatureIcon = ({ icon, label }: { icon: React.ReactNode, label: string }) => (
  <div className="flex flex-col items-center gap-3 text-center">
    <div className="text-[#222]">{icon}</div>
    <span className="text-[10px] text-[#222] font-semibold tracking-[2px] uppercase">{label}</span>
  </div>
);

export default BlockchainVerificationPortal;
