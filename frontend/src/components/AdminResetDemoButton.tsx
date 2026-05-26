import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCcw, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/config";

export const AdminResetDemoButton = () => {
  const [isResetting, setIsResetting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleReset = async () => {
    setIsResetting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/demo/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: "RESET_LOANEASE_DEMO" }),
      });

      if (!response.ok) throw new Error("Reset failed");
      
      const data = await response.json();
      toast.success(`Demo Reset Successful: ${data.sessions_cleared} sessions wiped.`);
      
      // Clear local storage too
      localStorage.clear();
      
      // Short delay and reload to ensure clean state
      setTimeout(() => {
        window.location.href = window.location.origin + window.location.pathname + "?demo=true";
      }, 1500);
    } catch (error) {
      toast.error("Failed to reset demo environment");
      setIsResetting(false);
      setShowConfirm(false);
    }
  };

  if (showConfirm) {
    return (
      <div className="flex flex-col gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg animate-in fade-in zoom-in duration-200">
        <div className="flex items-center gap-2 text-red-400 font-bold text-xs uppercase tracking-wider">
          <AlertTriangle className="w-3.5 h-3.5" />
          Confirm Wipe All Data?
        </div>
        <p className="text-[10px] text-[hsl(0,0%,70%)] leading-tight">
          This will clear all active sessions, blockchain history, and local storage.
        </p>
        <div className="flex gap-2 mt-1">
          <Button
            size="sm"
            variant="destructive"
            className="h-7 text-[10px] flex-1"
            onClick={handleReset}
            disabled={isResetting}
          >
            {isResetting ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <RefreshCcw className="w-3 h-3 mr-1" />}
            Reset Now
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-[10px] flex-1 bg-white/5 hover:bg-white/10"
            onClick={() => setShowConfirm(false)}
            disabled={isResetting}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setShowConfirm(true)}
      className={cn(
        "w-full h-9 text-[11px] font-bold uppercase tracking-widest transition-all duration-300",
        "border-[hsl(0,0%,25%)] hover:border-red-500/50 hover:bg-red-500/5 text-[hsl(0,0%,70%)] hover:text-red-400"
      )}
    >
      <RefreshCcw className="w-3.5 h-3.5 mr-2" />
      Reset Demo Environment
    </Button>
  );
};
