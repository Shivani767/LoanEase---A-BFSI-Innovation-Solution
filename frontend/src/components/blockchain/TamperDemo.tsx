import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, ShieldAlert, RefreshCw, ChevronRight, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/config";

interface TamperDemoProps {
  onTamper: (data: any) => void;
  sanctionReference?: string;
  onReset: () => void;
}

export const TamperDemo = ({ onTamper, sanctionReference, onReset }: TamperDemoProps) => {
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  const runTamperTest = async () => {
    // Use fallback reference if none provided
    const reference = sanctionReference || "DEMO-2026-00001";
    
    setIsRunning(true);
    try {
      const response = await fetch(`${API_BASE_URL}/blockchain/tamper-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reference: reference,
          tamper_field: "loan_amount",
          tamper_value: 5000000 // 50 Lakhs instead of 5 Lakhs
        })
      });

      const data = await response.json();
      setResult(data);
      onTamper(data);

      // Auto-reset after 7 seconds
      setTimeout(() => {
        setResult(null);
        setIsRunning(false);
        onReset();
      }, 7000);
    } catch (error) {
      console.error("Tamper test failed", error);
      setIsRunning(false);
    }
  };

  return (
    <div className="bg-[hsl(0,0%,7%)] border border-red-500/20 rounded-2xl p-6 relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-4 opacity-10">
        <ShieldAlert size={80} className="text-red-500" />
      </div>

      <div className="relative z-10">
        <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-2">
          <AlertTriangle className="text-red-500" size={20} />
          🔬 Tamper Detection Demo
        </h3>
        <p className="text-xs text-muted-foreground mb-6 max-w-md">
          Simulate a malicious actor trying to modify a sanctioned loan amount 
          directly in the data storage. Watch how the blockchain detects the mismatch instantly.
        </p>

        {!result ? (
          <div className="flex flex-col gap-4">
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-center justify-between">
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold mb-1">Target Sanction</p>
                <p className="text-sm text-white font-mono">{sanctionReference || "DEMO-2026-00001"}</p>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold mb-1">Manipulation</p>
                <p className="text-xs font-bold text-red-400">₹5,00,000 → ₹50,00,000</p>
              </div>
            </div>

            <Button 
              variant="destructive" 
              onClick={runTamperTest}
              disabled={isRunning}
              className="w-full bg-red-500 hover:bg-red-600 font-bold uppercase tracking-widest text-xs h-12"
            >
              {isRunning ? (
                <RefreshCw size={16} className="mr-2 animate-spin" />
              ) : (
                <ShieldAlert size={16} className="mr-2" />
              )}
              {isRunning ? "Running Analysis..." : "Run Tamper Test"}
            </Button>
          </div>
        ) : (
          <div className="space-y-4 animate-in zoom-in duration-300">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-3">
                <p className="text-[10px] font-bold text-green-400 uppercase tracking-widest mb-2">Original Block Hash</p>
                <p className="text-[10px] font-mono break-all text-green-200/60">{result.original_hash}</p>
              </div>
              <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-3">
                <p className="text-[10px] font-bold text-red-400 uppercase tracking-widest mb-2">Tampered Content Hash</p>
                <p className="text-[10px] font-mono break-all text-red-200/60">{result.tamper_hash || result.tampered_hash}</p>
              </div>
            </div>

            <div className="bg-red-500/10 border-2 border-red-500 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-2">
                <ShieldAlert className="text-red-500" size={24} />
                <h4 className="text-red-500 font-black uppercase tracking-tighter text-xl">
                  Hash Mismatch Detected!
                </h4>
              </div>
              <p className="text-xs text-red-200/80 leading-relaxed font-medium">
                The content of Block #{sanctionReference} has been altered. 
                The calculated hash for the current data does not match the block header 
                stored in the chain. This block and all subsequent blocks are now 
                invalidated and the audit trail is broken.
              </p>
            </div>

            <div className="text-center pt-2">
              <p className="text-[10px] text-[hsl(47,100%,50%)] animate-pulse font-bold uppercase tracking-[0.2em]">
                System self-healing in progress... Ledger restored in 5s
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
