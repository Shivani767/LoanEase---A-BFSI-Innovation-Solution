import { useMemo, useState, useEffect, useRef } from "react";
import { ChevronDown, Loader2, CheckCircle2, Bot, X, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export interface AgentTraceItem {
  step: number;
  agent: string;
  action: string;
  reasoning: string;
  duration_ms: number;
  timestamp: string;
}

interface AgentActivityPanelProps {
  trace: AgentTraceItem[];
  pipelineStatus: string;
  activeAgentLabel?: string | null;
  liveProcessing?: boolean;
  liveLogLines?: string[];
}

const AGENT_ORDER = [
  "MasterOrchestratorAgent",
  "KYCVerificationAgent",
  "CreditUnderwritingAgent",
  "Negotiation Agent",
  "BlockchainAuditAgent",
];

const LABELS: Record<string, string> = {
  MasterOrchestratorAgent: "Master Agent",
  KYCVerificationAgent: "KYC Agent",
  CreditUnderwritingAgent: "Credit Agent",
  "Negotiation Agent": "Negotiation Agent",
  BlockchainAuditAgent: "Blockchain Agent",
};

const STATUS_TO_AGENT: Record<string, string> = {
  "INITIATED": "MasterOrchestratorAgent",
  "KYC_PENDING": "KYCVerificationAgent",
  "KYC_VERIFIED": "CreditUnderwritingAgent",
  "CREDIT_ASSESSED": "CreditUnderwritingAgent",
  "OFFER_GENERATED": "Negotiation Agent",
  "NEGOTIATING": "Negotiation Agent",
  "ACCEPTED": "BlockchainAuditAgent",
  "SANCTIONED": "BlockchainAuditAgent",
  "FAILED": "MasterOrchestratorAgent"
};

export const AgentActivityPanel = ({ trace, pipelineStatus, activeAgentLabel, liveProcessing = false, liveLogLines = [] }: AgentActivityPanelProps) => {
  const [collapsed, setCollapsed] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const doneSet = useMemo(() => new Set((trace || []).map((item) => item.agent)), [trace]);

  const labelToAgent = useMemo<Record<string, string>>(
    () => ({
      "Master Agent": "MasterOrchestratorAgent",
      "KYC Verification Agent": "KYCVerificationAgent",
      "Credit Underwriting Agent": "CreditUnderwritingAgent",
      "Loan Recommendation Engine": "CreditUnderwritingAgent",
      "Dynamic Negotiation Agent": "Negotiation Agent",
      "Blockchain Audit Agent": "BlockchainAuditAgent",
    }),
    []
  );
  
  const activeAgent = useMemo(() => {
    const overrideAgent = activeAgentLabel ? labelToAgent[activeAgentLabel] : null;

    if (overrideAgent) {
      return overrideAgent;
    }

    // If status gives us a clear hint, use it
    if (pipelineStatus && STATUS_TO_AGENT[pipelineStatus]) {
      return STATUS_TO_AGENT[pipelineStatus];
    }
    
    // Fallback to trace-based detection
    const next = AGENT_ORDER.find((agent) => !doneSet.has(agent));
    return pipelineStatus === "SANCTIONED" || pipelineStatus === "FAILED" ? null : next ?? null;
  }, [activeAgentLabel, doneSet, labelToAgent, pipelineStatus]);

  // Detect demo mode from URL param
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setIsDemoMode(params.get("demo") === "true");
  }, []);

  // Detect visibility with Intersection Observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsInView(entry.isIntersecting);
        // Auto-expand when comes into view if there's an active agent
        if (entry.isIntersecting && activeAgent) {
          setCollapsed(false);
        }
      },
      { threshold: 0.1, rootMargin: "100px" }
    );

    if (panelRef.current) {
      observer.observe(panelRef.current);
    }

    return () => {
      if (panelRef.current) {
        observer.unobserve(panelRef.current);
      }
    };
  }, [activeAgent]);

  // Auto-expand when active, but allow manual collapse
  useEffect(() => {
    if (activeAgent && isInView) {
      setCollapsed(false);
    }
  }, [activeAgent, isInView]);

  const hasActiveAgent = activeAgent !== null;

  // Don't show if not in view and collapsed
  if (!isInView && collapsed) {
    return (
      <div 
        ref={panelRef}
        className="fixed bottom-6 right-6 z-50 w-1 h-1"
        aria-hidden="true"
      >
        {liveProcessing && (
          <div className="border-t border-[#1a1a1a] bg-[#0a0a0a] px-4 py-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="font-display text-[10px] font-semibold uppercase tracking-[2px] text-[#444444]">Live Output</div>
              <span className="text-[10px] font-mono text-yellow-400/60">processing...</span>
            </div>
            <div className="max-h-32 overflow-hidden space-y-1 font-mono text-[11px] text-[rgba(245,197,24,0.6)]">
              {liveLogLines.length > 0 ? liveLogLines.slice(-8).map((line, index) => (
                <div
                  key={`${line}-${index}`}
                  className="animate-in fade-in slide-in-from-bottom-2 duration-300"
                  style={{ animationDelay: `${index * 70}ms` }}
                >
                  {line}
                </div>
              )) : (
                <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                  &gt; SYSTEM: Awaiting output...
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (collapsed) {
    return (
      <div 
        ref={panelRef}
        className="fixed bottom-6 right-6 z-50 animate-slide-up"
        onClick={() => setCollapsed(false)}
      >
        <button className={cn(
          "w-14 h-14 rounded-full bg-card border-2 shadow-2xl flex items-center justify-center transition-all duration-300 hover:scale-110",
          hasActiveAgent ? "border-yellow-400" : "border-border"
        )}>
          <Bot className={cn("w-8 h-8", hasActiveAgent && "animate-pulse")} />
          {hasActiveAgent && (
            <span className="absolute top-0 right-0 w-3 h-3 bg-yellow-400 rounded-full border-2 border-card animate-pulse" />
          )}
        </button>
      </div>
    );
  }

  return (
    <div ref={panelRef} className={cn("flex flex-col h-full w-full")}>
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-3 border-b border-border/50 bg-muted/30 lg:hidden">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5" />
            <div className="text-sm font-bold tracking-tight">Agent Activity</div>
            {isDemoMode && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-yellow-400/20 text-yellow-400 font-semibold border border-yellow-400/30 animate-pulse-soft">
                <Zap className="w-3 h-3 mr-1" />
Demo
              </span>
            )}
          </div>
          <button 
            className="p-1 hover:bg-muted rounded-md transition-colors"
            onClick={() => setCollapsed(true)}
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <div className="p-3 space-y-2 overflow-y-auto overflow-x-hidden scrollbar-hide">
          {AGENT_ORDER.map((agent) => {
            const item = trace.find((t) => t.agent === agent);
            const isDone = Boolean(item);
            const isActive = activeAgent === agent;
            
            return (
              <div 
                key={agent} 
                className={cn(
                  "flex flex-col gap-1 p-2.5 rounded-lg border transition-all duration-500",
                  isDone ? "border-border/50 bg-card border-l-4 border-l-green-500" : 
                  isActive ? "border-yellow-400/50 bg-yellow-400/5 shadow-[0_0_15px_rgba(250,204,21,0.15)] ring-1 ring-yellow-400 animate-pulse-soft" : 
                  "border-transparent bg-transparent opacity-60"
                )}
              >
                <div className="flex items-center gap-2">
                  {isDone ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                  ) : isActive ? (
                    <Loader2 className="h-4 w-4 animate-spin text-yellow-400 shrink-0" />
                  ) : (
                    <div className="h-4 w-4 rounded-full border-2 border-muted-foreground shrink-0" />
                  )}
                  
                  <div className="min-w-0 flex-1">
                    <div className={cn(
                      "truncate text-sm font-semibold",
                      isActive && "text-yellow-400"
                    )}>
                      {LABELS[agent]}
                    </div>
                  </div>
                </div>

                <div className="pl-6">
                  {isDone && item && (
                    <div className="text-xs text-muted-foreground break-words leading-tight">
                      {item.action || "Completed successfully"}
                      <div className="mt-1 text-[10px] opacity-70 font-mono">
                        {(item.duration_ms / 1000).toFixed(1)}s ago
                      </div>
                    </div>
                  )}
                  
                  {isActive && (
                    <div className="text-xs text-muted-foreground break-words leading-tight">
                      <div className="w-full bg-muted rounded-full h-1.5 mt-1 mb-1.5 overflow-hidden">
                        <div className="bg-yellow-400 h-full w-2/3 animate-pulse" />
                      </div>
                      Processing...
                    </div>
                  )}

                  {!isDone && !isActive && (
                    <div className="text-xs text-muted-foreground">Waiting</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        
        {hasActiveAgent && (
          <div className="p-2 border-t border-border/50 bg-muted/10 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              <span className="text-[10px] font-medium text-muted-foreground">Groq LLaMA 70B: Active</span>
            </div>
            <span className="text-[10px] text-muted-foreground font-mono">📡 loanease.local:8000</span>
          </div>
        )}
      </div>
    </div>
  );
};
