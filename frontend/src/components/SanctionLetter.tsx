import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Link } from "react-router-dom";
import { Download, Shield, FileCheck, TrendingUp, CheckCircle2, Lock, QrCode, BarChart3 } from "lucide-react";
import { useState } from "react";
import { ENDPOINTS } from "@/config";

interface SanctionLetterProps {
  customerName: string;
  loanAmount: number;
  interestRate: number;
  tenure: number;
  emi: number;
  sanctionDate: string;
  referenceId: string;
  blockchainHash: string;
  blockIndex?: number;
  sessionId?: string;
  onViewAnalytics?: () => void;
}

export const SanctionLetter = ({
  customerName,
  loanAmount,
  interestRate,
  tenure,
  emi,
  sanctionDate,
  referenceId,
  blockchainHash,
  blockIndex,
  sessionId,
  onViewAnalytics,
}: SanctionLetterProps) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadPDF = async () => {
    try {
      setIsDownloading(true);
      
      // Fetch PDF from backend
      const response = await fetch(`${ENDPOINTS.blockchain_sanction}?reference_id=${encodeURIComponent(referenceId)}`, {
        method: "GET",
        headers: {
          "Accept": "application/pdf",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to generate PDF");
      }

      // Create blob from response
      const blob = await response.blob();
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Sanction_Letter_${referenceId}.pdf`;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("PDF download failed:", error);
      alert("Failed to download PDF. Please try again.");
    } finally {
      setIsDownloading(false);
    }
  };
  return (
    <Card className="max-w-2xl mx-auto animate-slide-up overflow-hidden border-2 border-border/50 shadow-2xl">
      <div className="bg-gradient-primary p-6 text-primary-foreground relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10"></div>
        <div className="flex items-center justify-between relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center backdrop-blur-sm">
              <FileCheck className="w-6 h-6 text-yellow-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold font-display tracking-tight text-white">LOANEASE DIGITAL SANCTION LETTER</h2>
              <p className="text-sm text-yellow-400/90 font-medium">Officially Generated Document</p>
            </div>
          </div>
          <Badge variant="secondary" className="bg-green-500/20 text-green-400 border border-green-500/30">
            <Shield className="w-3 h-3 mr-1" />
            Verified
          </Badge>
        </div>
      </div>

      <CardContent className="p-6 space-y-6">
        <div className="grid grid-cols-2 gap-4 bg-muted/20 p-4 rounded-xl border border-border/30">
          <div>
            <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">Reference ID</p>
            <p className="font-mono text-sm font-medium">{referenceId}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">Sanction Date</p>
            <p className="font-medium text-sm">{sanctionDate}</p>
          </div>
        </div>

        <div className="border border-border/40 rounded-xl p-5 space-y-5 bg-card relative">
          <div>
            <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">Customer Name</p>
            <p className="font-bold text-lg">{customerName}</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">Loan Amount</p>
              <p className="font-black text-yellow-400 text-lg">₹{loanAmount.toLocaleString('en-IN')}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">Interest Rate</p>
              <p className="font-bold text-lg">{interestRate}% <span className="text-xs text-muted-foreground font-normal">p.a.</span></p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">Tenure</p>
              <p className="font-bold text-lg">{tenure} <span className="text-xs text-muted-foreground font-normal">mo</span></p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1">Monthly EMI</p>
              <p className="font-black text-yellow-400 text-lg">₹{emi.toLocaleString('en-IN')}</p>
            </div>
          </div>
        </div>

        {/* Blockchain Seal Component */}
        <div className="relative rounded-xl p-0.5 bg-gradient-to-r from-yellow-400/30 via-yellow-200/10 to-yellow-400/30">
          <div className="bg-card rounded-[10px] p-5 flex flex-col sm:flex-row gap-5 items-center sm:items-start relative overflow-hidden">
            <div className="absolute -right-10 -top-10 w-32 h-32 bg-yellow-400/5 rounded-full blur-2xl"></div>
            
            <div className="shrink-0 bg-white p-2 rounded-lg border border-yellow-400/20 shadow-[0_0_15px_rgba(250,204,21,0.15)] relative">
              <QrCode className="w-16 h-16 text-black" />
              <div className="absolute -bottom-2 -right-2 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center border-2 border-card shadow-lg">
                <Lock className="w-3 h-3 text-black" />
              </div>
            </div>

            <div className="flex-1 space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-yellow-400" />
                <h4 className="font-black tracking-wide text-sm text-foreground uppercase">Blockchain Verified Seal</h4>
              </div>
              
              <div className="space-y-1.5">
                <div className="flex items-start gap-2">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground w-12 shrink-0">Hash</span>
                  <span className="font-mono text-[10px] text-muted-foreground break-all">{blockchainHash}</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground w-12 shrink-0">Block</span>
                  <span className="font-mono text-[10px] text-foreground">#{blockIndex !== undefined ? blockIndex : 'Latest'}</span>
                </div>
              </div>

              <div className="flex flex-wrap gap-3 pt-1">
                <div className="flex items-center gap-1.5 bg-green-500/10 px-2 py-1 rounded-md border border-green-500/20">
                  <CheckCircle2 className="w-3 h-3 text-green-500" />
                  <span className="text-[10px] font-bold text-green-500 uppercase tracking-wider">RSA-2048 Signed</span>
                </div>
                <div className="flex items-center gap-1.5 bg-green-500/10 px-2 py-1 rounded-md border border-green-500/20">
                  <CheckCircle2 className="w-3 h-3 text-green-500" />
                  <span className="text-[10px] font-bold text-green-500 uppercase tracking-wider">Merkle Verified</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <Button 
            variant="accent" 
            className="w-full h-12 text-sm font-bold tracking-wide" 
            size="lg"
            type="button"
            onClick={handleDownloadPDF}
            disabled={isDownloading}
          >
            <Download className="w-4 h-4 mr-2" />
            {isDownloading ? "Generating..." : "Download PDF"}
          </Button>

          {onViewAnalytics && (
            <Button
              variant="outline"
              className="w-full h-12 text-sm font-bold tracking-wide border-border hover:bg-muted"
              size="lg"
              type="button"
              onClick={onViewAnalytics}
            >
              <BarChart3 className="w-4 h-4 mr-2" />
              View Loan Analytics
            </Button>
          )}

          <Link to="/blockchain/explorer" className="w-full">
            <Button
              variant="outline"
              className="w-full h-12 text-sm font-bold tracking-wide border-border hover:bg-muted"
              size="lg"
              type="button"
            >
              <Shield className="w-4 h-4 mr-2" />
              Verify on Ledger
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
