import { useState, useEffect, useCallback } from "react";
import { X, CheckCircle2, Circle, RotateCcw, ClipboardList, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { AdminResetDemoButton } from "./AdminResetDemoButton";

const CHECKLIST_ITEMS = [
  "Start fresh session",
  "Type loan amount (₹5,00,000)",
  "Upload PAN card",
  "Upload Aadhaar card",
  "Show credit score reveal",
  "Show SHAP explanation",
  "Negotiate rate (click button)",
  "Accept final offer",
  "Show blockchain sanction",
  "Open blockchain explorer",
  "Run tamper detection demo",
  "Show agent activity log",
];

export const DemoChecklist = () => {
  const [visible, setVisible] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [checked, setChecked] = useState<Set<number>>(new Set());

  // Read URL param to decide if checklist should show
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const demoParam = params.get("demo");
    if (demoParam === "true") {
      setVisible(true);
    } else if (demoParam === "false") {
      setVisible(false);
    }
  }, []);

  const toggle = useCallback((idx: number) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  }, []);

  const resetAll = useCallback(() => {
    setChecked(new Set());
  }, []);

  const progress = checked.size;
  const total = CHECKLIST_ITEMS.length;
  const progressPct = Math.round((progress / total) * 100);

  if (!visible) return null;

  // Minimized floating button
  if (minimized) {
    return (
      <button
        onClick={() => setMinimized(false)}
        className={cn(
          "fixed bottom-6 left-6 z-[60] w-14 h-14 rounded-full",
          "bg-[hsl(0,0%,18%)] border-2 border-[hsl(47,100%,50%)]",
          "shadow-[0_0_20px_hsl(47,100%,50%/0.3)]",
          "flex items-center justify-center",
          "transition-all duration-300 hover:scale-110 hover:shadow-[0_0_30px_hsl(47,100%,50%/0.5)]"
        )}
        title="Open Demo Checklist"
      >
        <ClipboardList className="w-6 h-6 text-[hsl(47,100%,50%)]" />
        {progress > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-green-500 text-[10px] font-bold text-white flex items-center justify-center">
            {progress}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 left-6 z-[60] w-80 animate-in slide-in-from-bottom-5 duration-300">
      <div
        className={cn(
          "rounded-xl overflow-hidden flex flex-col max-h-[85vh]",
          "bg-[hsl(0,0%,14%)/0.95] backdrop-blur-xl",
          "border border-[hsl(0,0%,25%)]",
          "shadow-[0_8px_32px_hsl(0,0%,0%/0.6),0_0_0_1px_hsl(47,100%,50%/0.1)]"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(0,0%,25%)] bg-[hsl(0,0%,18%)/0.6]">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5" />
            <span className="text-sm font-bold text-white tracking-tight">Demo Checklist</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[hsl(47,100%,50%)] text-[hsl(0,0%,13%)] font-semibold">
              {progress}/{total}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={resetAll}
              className="p-1 rounded-md hover:bg-[hsl(0,0%,25%)] transition-colors"
              title="Reset all"
            >
              <RotateCcw className="w-3.5 h-3.5 text-[hsl(0,0%,70%)]" />
            </button>
            <button
              onClick={() => setMinimized(true)}
              className="p-1 rounded-md hover:bg-[hsl(0,0%,25%)] transition-colors"
              title="Minimize"
            >
              <X className="w-4 h-4 text-[hsl(0,0%,70%)]" />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="px-4 pt-2 pb-1">
          <div className="w-full h-1.5 rounded-full bg-[hsl(0,0%,25%)] overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[hsl(47,100%,50%)] to-[hsl(142,76%,36%)] transition-all duration-500 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Items */}
        <div className="px-3 py-2 space-y-0.5 overflow-y-auto scrollbar-hide">
          {CHECKLIST_ITEMS.map((item, idx) => {
            const isDone = checked.has(idx);
            return (
              <button
                key={idx}
                onClick={() => toggle(idx)}
                className={cn(
                  "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left",
                  "transition-all duration-200 group",
                  isDone
                    ? "bg-green-500/10 hover:bg-green-500/15"
                    : "hover:bg-[hsl(0,0%,22%)]"
                )}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0 transition-transform duration-200 scale-110" />
                ) : (
                  <Circle className="w-4 h-4 text-[hsl(0,0%,45%)] shrink-0 group-hover:text-[hsl(0,0%,60%)] transition-colors" />
                )}
                <span
                  className={cn(
                    "text-[13px] leading-tight transition-all duration-200",
                    isDone
                      ? "text-green-400 line-through opacity-80"
                      : "text-[hsl(0,0%,85%)] group-hover:text-white"
                  )}
                >
                  {item}
                </span>
              </button>
            );
          })}
        </div>

        {/* Footer */}
        {progress === total && (
          <div className="px-4 py-2.5 border-t border-[hsl(0,0%,25%)] bg-green-500/5">
            <div className="text-center text-xs font-semibold text-green-400">
              <CheckCircle2 className="w-4 h-4 inline mr-1" />
All demo features covered!
            </div>
          </div>
        )}

        <div className="px-4 py-3 border-t border-[hsl(0,0%,20%)] bg-[hsl(0,0%,12%)/0.5] space-y-3">
          <AdminResetDemoButton />
          <div className="text-[9px] text-[hsl(0,0%,40%)] text-center font-mono uppercase tracking-tighter">
            Environment Gated: <span className="text-[hsl(47,100%,50%)]">DEMO_MODE=ON</span>
          </div>
        </div>
      </div>
    </div>
  );
};
