import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChatInterface } from "@/components/ChatInterface";
import { cn } from "@/lib/utils";

// --- Components ---

const HeroSection = ({ onStartChat, onHowItWorks, onWhatsApp }: { onStartChat: () => void, onHowItWorks: () => void, onWhatsApp: () => void }) => {
  const [typedLines, setTypedLines] = useState<string[]>([]);
  const lines = [
    "> INITIALIZING_GROQ_LLaMA_70B...",
    "> KYC_OCR_SCAN_ACTIVE...",
    "> SHA256_MERKLE_READY...",
    "> AWAITING_CONFIRMATION..."
  ];

  // Real-time activity polling
  const [systemLogs, setSystemLogs] = useState<any[]>([]);
  const [systemStats, setSystemStats] = useState<any>({ total_active_sessions: 0 });

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch("/pipeline/global-logs");
        if (response.ok) {
          const data = await response.json();
          setSystemLogs(data.logs || []);
          setSystemStats(data);
        }
      } catch (e) {
        console.warn("Failed to fetch global logs", e);
      }
    };
    
    fetchLogs();
    const interval = setInterval(fetchLogs, 4000);
    return () => clearInterval(interval);
  }, []);

  const agentsList = [
    { id: "MasterOrchestratorAgent", name: "MASTER_AGENT" },
    { id: "KYCVerificationAgent", name: "KYC_VERIFIER" },
    { id: "CreditUnderwritingAgent", name: "CREDIT_ENGINE" },
    { id: "Negotiation Agent", name: "NEGOTIATION_BOT" },
    { id: "BlockchainAuditAgent", name: "BLOCKCHAIN_LEDGER" }
  ];

  const getAgentStatus = (agentId: string) => {
    const lastAction = systemLogs.find(l => l.agent === agentId);
    if (!lastAction) return "WAITING";
    
    const lastTimestamp = new Date(lastAction.timestamp).getTime();
    const now = new Date().getTime();
    const diffSec = (now - lastTimestamp) / 1000;
    
    if (diffSec < 10) return "ACTIVE";
    if (diffSec < 60) return "RUNNING";
    return "IDLE";
  };

  useEffect(() => {
    let currentLineIdx = 0;
    let currentCharIdx = 0;
    let isDeleting = false;
    
    const type = () => {
      const currentFullLine = lines[currentLineIdx];
      
      if (!isDeleting) {
        setTypedLines(prev => {
          const next = [...prev];
          next[currentLineIdx] = currentFullLine.substring(0, currentCharIdx + 1);
          return next;
        });
        currentCharIdx++;
        
        if (currentCharIdx === currentFullLine.length) {
          if (currentLineIdx === lines.length - 1) {
            setTimeout(() => isDeleting = true, 2000);
          } else {
            currentLineIdx++;
            currentCharIdx = 0;
          }
        }
      } else {
        setTypedLines([]);
        currentLineIdx = 0;
        currentCharIdx = 0;
        isDeleting = false;
      }
    };

    const interval = setInterval(type, 30);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative min-h-screen bg-black overflow-hidden flex flex-col justify-end">
      {/* Layer 2 - Vertical light columns */}
      <div className="absolute right-0 top-0 w-[55%] h-full pointer-events-none">
        {[4, 9, 15, 22, 28, 35, 40, 46, 52].map((left, i) => (
          <div
            key={i}
            className="absolute top-0 w-px bg-gradient-to-b from-transparent via-[rgba(245,197,24,0.12)] to-transparent"
            style={{
              left: `${left}%`,
              height: `${60 + Math.random() * 30}%`,
              top: `${Math.random() * 20}%`,
              backgroundColor: i % 3 === 0 ? "rgba(255,255,255,0.03)" : undefined,
              opacity: 0.8
            }}
          />
        ))}
      </div>

      {/* Layer 3 - Floor glow */}
      <div 
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80%] h-[30%] pointer-events-none"
        style={{
          background: "radial-gradient(ellipse 80% 30% at 50% 100%, rgba(245,197,24,0.07) 0%, transparent 70%)"
        }}
      />

      {/* Layer 4 - Vignette */}
      <div className="absolute inset-0 shadow-[inset_0_0_200px_rgba(0,0,0,0.9)] pointer-events-none" />

      {/* Layer 5 - Grain */}
      <svg style={{ position: 'absolute', width: 0, height: 0 }}>
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/>
          <feColorMatrix type="saturate" values="0"/>
        </filter>
      </svg>
      <div className="absolute inset-0 opacity-[0.04] pointer-events-none" style={{ filter: "url(#grain)" }} />

      {/* Hero Content */}
      <div className="relative z-10 w-full px-16 pb-20 grid grid-cols-2 h-[45%] items-end">
        {/* Left Column */}
        <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
          <div className="inline-block px-3.5 py-1.5 bg-[rgba(245,197,24,0.08)] border border-[rgba(245,197,24,0.2)] rounded-sm mb-5">
            <span className="font-sans font-medium text-[10px] text-[#F5C518] tracking-[3px] uppercase">
              ⚡ 5 AGENTIC AI MODELS • LIVE
            </span>
          </div>
          
          <h1 className="font-bebas text-[clamp(56px,8vw,120px)] leading-[0.95] tracking-[0.01em] m-0">
            <span className="text-white block animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">PERSONAL LOANS.</span>
            <span className="text-[#F5C518] block animate-in fade-in slide-in-from-bottom-8 duration-700 delay-250">POWERED BY AI.</span>
          </h1>

          <p className="font-sans text-[17px] text-[#666666] leading-[1.6] mt-5 max-w-[400px] animate-in fade-in duration-700 [animation-delay:400ms]">
            From blockchain-secured KYC to signed sanction letter — in under 5 minutes.
          </p>

          <div className="flex items-center gap-3 mt-8 animate-in fade-in duration-700 [animation-delay:550ms]">
            <button 
              onClick={onStartChat}
              className="px-8 py-3.5 bg-[#F5C518] text-black font-sans font-bold text-[13px] tracking-[1px] rounded-sm border-none cursor-pointer transition-all duration-200 hover:shadow-[0_0_40px_rgba(245,197,24,0.45)] hover:-translate-y-px active:translate-y-0"
            >
              START APPLICATION →
            </button>
            <button 
              onClick={onHowItWorks}
              className="px-8 py-3.5 bg-transparent text-[#555555] font-sans font-bold text-[13px] tracking-[1px] rounded-sm border border-[#222222] cursor-pointer transition-all duration-200 hover:border-[#F5C518] hover:text-white"
            >
              HOW IT WORKS
            </button>
            <button 
              onClick={onWhatsApp}
              className="px-6 py-3.5 bg-transparent text-[#22c55e] font-sans font-bold text-[11px] tracking-[1px] rounded-sm border border-[rgba(34,197,94,0.1)] cursor-pointer transition-all duration-200 hover:border-[#22c55e] hover:bg-[rgba(34,197,94,0.02)]"
            >
              WHATSAPP DEMO
            </button>
          </div>

          <div className="mt-7 flex gap-1 animate-in fade-in duration-700 [animation-delay:700ms]">
            <span className="font-sans text-[12px] text-[#333333] tracking-[1px] uppercase">
              82.1% ACCURACY  •  99.4% FASTER  •  BLOCKCHAIN-SECURED
            </span>
          </div>
        </div>

        {/* Right Column */}
        <div className="flex items-end justify-end">
          <div 
            className="w-[300px] bg-[rgba(8,8,8,0.92)] border border-[#1a1a1a] rounded-md backdrop-blur-2xl shadow-[0_32px_80px_rgba(0,0,0,0.8),0_0_100px_rgba(245,197,24,0.04)] animate-in fade-in slide-in-from-bottom-5 duration-700 delay-300"
            style={{ animation: "float 5s ease-in-out infinite" }}
          >
            <div className="px-3.5 py-2.5 border-b border-[#111] bg-[#050505] rounded-t-md flex items-center gap-2">
              <div className="flex gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-[#ef4444]" />
                <div className="w-1.5 h-1.5 rounded-full bg-[#F5C518]" />
                <div className="w-1.5 h-1.5 rounded-full bg-[#22c55e]" />
              </div>
              <span className="ml-auto font-sans font-medium text-[9px] text-[#333] tracking-[2px] uppercase">
                AGENT TERMINAL v1.0
              </span>
            </div>
            
            <div className="p-4 space-y-[2px]">
              {agentsList.map((agent, i) => {
                const status = getAgentStatus(agent.id);
                return (
                <div 
                  key={i} 
                  className={cn(
                    "flex items-center gap-2.5 px-2.5 py-1.5 rounded-sm transition-all duration-500",
                    status === "ACTIVE" && "bg-[rgba(245,197,24,0.06)] border-l-2 border-l-[#F5C518] shadow-[inset_0_0_10px_rgba(245,197,24,0.05)]"
                  )}
                >
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    status === "ACTIVE" ? "bg-[#22c55e] shadow-[0_0_10px_#22c55e] animate-pulse" :
                    status === "RUNNING" ? "bg-[#F5C518]" : "bg-[#222222]"
                  )} />
                  <span className={cn(
                    "font-sans font-medium text-[11px] tracking-[0.5px]",
                    status === "ACTIVE" ? "text-white" : 
                    status === "RUNNING" ? "text-[#F5C518]" : "text-[#333333]"
                  )}>
                    {agent.name}
                  </span>
                  <div className={cn(
                    "ml-auto font-sans font-medium text-[9px] px-2 py-0.5 border rounded-sm transition-colors",
                    status === "ACTIVE" ? "text-[#22c55e] border-[#22c55e]" :
                    status === "RUNNING" ? "text-[#F5C518] border-[#F5C518]" : "text-[#2a2a2a] border-[#2a2a2a]"
                  )}>
                    [{status}]
                  </div>
                </div>
                );
              })}

              <div className="h-px bg-[#0f0f0f] my-3" />

              <div className="font-sans text-[9px] text-[rgba(245,197,24,0.4)] leading-[1.8] min-h-[65px] max-h-[100px] overflow-hidden">
                {systemLogs.length > 0 ? (
                  systemLogs.slice(0, 4).map((log, i) => (
                    <div key={i} className="animate-in fade-in slide-in-from-left duration-300">
                      <span className="text-white opacity-40">[{log.session_id?.slice(-6) || "SYS"}]</span> {(log.agent || "System").split('Agent')[0].toUpperCase()}: {log.action || "Active"}
                    </div>
                  ))
                ) : (
                  typedLines.map((line, i) => (
                    <div key={i}>{line}</div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-bounce">
        <span className="font-sans text-[10px] text-[#2a2a2a] tracking-[3px] uppercase">[ SCROLL ]</span>
      </div>
    </section>
  );
};

const TrustBar = () => {
  const items = ["FastAPI", "XGBoost", "Groq LLaMA 70B", "RapidOCR", "SHA-256", "React 18"];
  return (
    <div className="bg-black border-y border-[#111] py-4.5 overflow-hidden">
      <div className="flex justify-center items-center gap-10">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-10">
            <span className="font-sans font-medium text-[11px] text-[#222222] tracking-[2px] uppercase cursor-default transition-colors duration-200 hover:text-[#F5C518]">
              {item}
            </span>
            {i < items.length - 1 && <span className="text-[#1a1a1a]">·</span>}
          </div>
        ))}
      </div>
    </div>
  );
};

const FiveAgents = () => {
  const [activeIndex, setActiveIndex] = useState(0);
  const agents = [
    {
      num: "01",
      title: "MASTER AGENT",
      name: "MASTER AGENT",
      desc: "Groq LLaMA 3.3 70B orchestrates every conversation turn",
      pills: ["Groq API", "State Machine", "Hindi/Hinglish"],
      metric: "450",
      metricLabel: "tokens/s",
      pipeline: ["USER_INPUT", "ROUTE_AGENT", "SEND_RESPONSE"]
    },
    {
      num: "02",
      title: "KYC VERIFIER",
      name: "KYC VERIFIER",
      desc: "RapidOCR extracts PAN and Aadhaar fields in under 2 seconds",
      pills: ["RapidOCR", "OpenCV", "rapidfuzz"],
      metric: "91%",
      metricLabel: "confidence",
      pipeline: ["UPLOAD_DOC", "OCR_EXTRACT", "CROSS_VALIDATE"]
    },
    {
      num: "03",
      title: "CREDIT ENGINE",
      name: "CREDIT ENGINE",
      desc: "XGBoost + SHAP delivers an explainable risk score in 0.9s",
      pills: ["XGBoost", "SHAP", "PAN-hash CIBIL"],
      metric: "82.1%",
      metricLabel: "accuracy",
      pipeline: ["APPLICANT_DATA", "XGBOOST_SCORE", "SHAP_EXPLAIN"]
    },
    {
      num: "04",
      title: "NEGOTIATION BOT",
      name: "NEGOTIATION BOT",
      desc: "Stateful rate negotiation across up to 3 rounds within risk bands",
      pills: ["Policy Engine", "Rate Bands", "EMI Formula"],
      metric: "3",
      metricLabel: "max rounds",
      pipeline: ["RISK_TIER", "OFFER_RATE", "NEGOTIATE"]
    },
    {
      num: "05",
      title: "BLOCKCHAIN LEDGER",
      name: "BLOCKCHAIN LEDGER",
      desc: "SHA-256 hash anchored sanction letter with Merkle verification",
      pills: ["SHA-256", "Merkle Tree", "Web3 structure"],
      metric: "0ms",
      metricLabel: "tamper detect",
      pipeline: ["LETTER_CONTENT", "SHA256_HASH", "LEDGER_STORE"]
    }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveIndex(prev => (prev + 1) % agents.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const activeAgent = agents[activeIndex];

  return (
    <section id="features" className="bg-black py-[140px] px-16">
      <div className="mb-20">
        <span className="font-bebas text-[13px] text-[#F5C518] tracking-[5px] block mb-4 uppercase">ARCHITECTURE</span>
        <h2 className="font-bebas text-[clamp(52px,7vw,88px)] text-white leading-[0.92] m-0">
          FIVE AGENTS.<br />ONE LOAN CONVERSATION.
        </h2>
      </div>

      <div className="grid grid-cols-[32%_68%] gap-0">
        <div className="flex flex-col gap-1">
          {agents.map((agent, i) => (
            <div 
              key={i}
              onClick={() => setActiveIndex(i)}
              className={cn(
                "p-5 pl-5 rounded-[3px] cursor-pointer transition-all duration-250 flex items-start gap-4",
                activeIndex === i ? "bg-[rgba(245,197,24,0.04)] border-l-2 border-l-[#F5C518]" : "hover:bg-[rgba(255,255,255,0.02)]"
              )}
            >
              <span className={cn(
                "font-bebas text-[36px] leading-none",
                activeIndex === i ? "text-[#F5C518]" : "text-[#1c1c1c]"
              )}>
                {agent.num}
              </span>
              <span className={cn(
                "font-sans font-semibold text-[15px] mt-2",
                activeIndex === i ? "text-white" : "text-[#2a2a2a]"
              )}>
                {agent.title}
              </span>
            </div>
          ))}
        </div>

        <div 
          key={activeIndex}
          className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-sm p-12 animate-in fade-in slide-in-from-right-2.5 duration-200"
        >
          <div className="flex items-center gap-4">
            <h3 className="font-bebas text-[56px] text-white m-0 uppercase">{activeAgent.name}</h3>
            <div className={cn(
              "font-sans font-semibold text-[10px] px-3 py-1 border rounded-[2px]",
              activeIndex === 0 ? "text-[#22c55e] border-[#22c55e]" : "text-[#F5C518] border-[#F5C518]"
            )}>
              {activeIndex === 0 ? "ACTIVE" : "READY"}
            </div>
          </div>

          <p className="font-sans text-[16px] text-[#555555] mt-3 max-w-[480px]">
            {activeAgent.desc}
          </p>

          <div className="flex flex-wrap gap-2 mt-6">
            {activeAgent.pills.map((pill, i) => (
              <span key={i} className="font-sans font-medium text-[11px] text-[#555555] bg-[#111111] border border-[#1e1e1e] px-3.5 py-1.5 rounded-[2px]">
                {pill}
              </span>
            ))}
          </div>

          <div className="mt-10">
            <div className="font-bebas text-[80px] text-[#F5C518] leading-[1]">{activeAgent.metric}</div>
            <div className="font-sans text-[14px] text-[#444] mt-0">{activeAgent.metricLabel}</div>
          </div>

          <div className="mt-10 flex items-center gap-2">
            {activeAgent.pipeline.map((step, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="font-sans font-medium text-[12px] text-[#333333] bg-[#111] border border-[#1e1e1e] px-4 py-2.5 rounded-[3px]">
                  {step}
                </div>
                {i < activeAgent.pipeline.length - 1 && <span className="text-[#F5C518] font-sans text-[16px]">→</span>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

const ComparisonSection = () => {
  const [stats, setStats] = useState({ approval: 0, accuracy: 0 });
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        let start = 0;
        const duration = 1500;
        const interval = 20;
        const steps = duration / interval;
        const approvalIncr = 99.4 / steps;
        const accuracyIncr = 82.1 / steps;
        
        const timer = setInterval(() => {
          start++;
          setStats(prev => ({
            approval: Math.min(99.4, start * approvalIncr),
            accuracy: Math.min(82.1, start * accuracyIncr)
          }));
          if (start >= steps) clearInterval(timer);
        }, interval);
        observer.disconnect();
      }
    }, { threshold: 0.15 });

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const rows = [
    { feature: "Approval Time", bank: "3–5 Business Days", loanease: "Instant (Sub-second)", bankOk: false, loanOk: true, highlight: true },
    { feature: "Credit Scoring", bank: "FICO Score Only", loanease: "12+ Feature ML Model", bankOk: false, loanOk: true },
    { feature: "Rate Negotiation", bank: "Fixed, Rigid", loanease: "Dynamic AI Negotiation", bankOk: false, loanOk: true },
    { feature: "Rejection Reason", bank: "None Given", loanease: "SHAP Explains Every Factor", bankOk: false, loanOk: true },
    { feature: "Document KYC", bank: "Manual Submission", loanease: "OCR Auto-Extract", bankOk: false, loanOk: true },
    { feature: "Sanction Letter", bank: "Paper, Days Later", loanease: "Blockchain PDF, Instant", bankOk: false, loanOk: true },
    { feature: "Language Support", bank: "English Only", loanease: "Hindi · English · Hinglish", bankOk: false, loanOk: true }
  ];

  return (
    <section id="technology" ref={sectionRef} className="bg-black py-[140px] px-16">
      <div className="mb-16">
        <span className="font-bebas text-[13px] text-[#F5C518] tracking-[5px] block mb-4 uppercase">STARK COMPARISON</span>
        <h2 className="font-bebas text-[clamp(44px,6vw,76px)] text-white m-0">
          TRADITIONAL BANKING IS BROKEN.
        </h2>
      </div>

      <div className="flex gap-0.5">
        <div className="flex-1 bg-[#0a0a0a] border border-[#1a1a1a] border-t-2 border-t-[#F5C518] rounded-sm p-10 flex flex-col gap-2">
          <div className="font-bebas text-[72px] text-[#F5C518] leading-[1]">{stats.approval.toFixed(1)}%</div>
          <div className="font-sans text-[13px] text-[#444444] tracking-[1px] uppercase mt-2">APPROVAL CONFIDENCE</div>
        </div>
        <div className="flex-1 bg-[#0a0a0a] border border-[#1a1a1a] border-t-2 border-t-[#F5C518] rounded-sm p-10 flex flex-col gap-2">
          <div className="font-bebas text-[72px] text-[#F5C518] leading-[1]">{stats.accuracy.toFixed(1)}%</div>
          <div className="font-sans text-[13px] text-[#444444] tracking-[1px] uppercase mt-2">MODEL ACCURACY</div>
        </div>
        <div className="flex-1 bg-[#0d0d0d] border border-[#1a1a1a] border-t-2 border-t-white rounded-sm p-10 flex flex-col gap-2">
          <div className="font-bebas text-[72px] text-white leading-[1]">0</div>
          <div className="font-sans text-[13px] text-[#444444] tracking-[1px] uppercase mt-2">HIDDEN FEES</div>
        </div>
      </div>

      <div className="mt-[60px] max-w-[860px] border border-[#1a1a1a] rounded-[4px] overflow-hidden">
        <div className="grid grid-cols-[1.5fr_1fr_1fr] bg-[#0a0a0a] border-b border-[#1a1a1a]">
          <div className="p-4 px-6 font-sans font-semibold text-[11px] text-[#333] tracking-[2px] uppercase">FEATURE</div>
          <div className="p-4 px-6 font-sans font-semibold text-[11px] text-[#333] tracking-[2px] uppercase">TRADITIONAL BANKS</div>
          <div className="p-4 px-6 font-sans font-semibold text-[11px] text-[#F5C518] tracking-[2px] uppercase">LOANEASE AI</div>
        </div>
        {rows.map((row, i) => (
          <div key={i} className={cn("grid grid-cols-[1.5fr_1fr_1fr] border-b border-[#0d0d0d]", i % 2 === 0 ? "bg-black" : "bg-[#040404]")}>
            <div className="p-4 px-6 font-sans font-medium text-[14px] text-white">{row.feature}</div>
            <div className="p-4 px-6 font-sans text-[14px] text-[#444] flex items-center gap-2">
              <span className="text-[#ef4444]">✗</span> {row.bank}
            </div>
            <div className={cn("p-4 px-6 font-sans text-[14px] flex items-center gap-2", row.highlight ? "text-[#F5C518]" : "text-white")}>
              <span className="text-[#22c55e]">✓</span> {row.loanease}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

const HowItWorks = () => {
  const [hoverIndex, setHoverIndex] = useState(4);
  const steps = [
    { num: "01", title: "CONNECT IDENTITY", body: "Upload PAN + Aadhaar — OCR reads everything" },
    { num: "02", title: "AI SCANS", body: "Our agents evaluate your real-world profile" },
    { num: "03", title: "RISK MODELLING", body: "XGBoost + SHAP scores your creditworthiness" },
    { num: "04", title: "NEGOTIATE", body: "AI negotiates the lowest rate your profile qualifies for" },
    { num: "05", title: "FINAL SANCTION", body: "Blockchain-verified letter delivered instantly" }
  ];

  return (
    <section className="bg-black py-[140px] px-16">
      <div className="mb-16">
        <span className="font-bebas text-[13px] text-[#F5C518] tracking-[5px] block mb-4 uppercase">WORKFLOW</span>
        <h2 className="font-bebas text-[clamp(44px,6vw,76px)] text-white m-0">
          KYC TO SANCTION. FIVE STEPS.
        </h2>
      </div>

      <div className="flex gap-0.5">
        {steps.map((step, i) => (
          <div 
            key={i}
            onMouseEnter={() => setHoverIndex(i)}
            className="flex-1 bg-[#0a0a0a] border border-[#111] p-8 rounded-[3px] transition-all duration-300"
          >
            <div className={cn(
              "w-10 h-10 flex items-center justify-center border rounded-[2px] font-bebas text-[22px] mb-6 transition-colors duration-300",
              hoverIndex === i ? "bg-[#F5C518] border-[#F5C518] text-black" : "bg-[#111] border-[#1e1e1e] text-white"
            )}>
              {step.num}
            </div>
            <h3 className="font-sans font-semibold text-[14px] text-white mb-2 uppercase">{step.title}</h3>
            <p className="font-sans text-[13px] text-[#444] leading-[1.5]">{step.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

const CTAClose = ({ onStartChat }: { onStartChat: () => void }) => {
  return (
    <section className="relative bg-black py-[180px] px-16 overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 opacity-20" style={{ background: "radial-gradient(ellipse 60% 60% at 50% 50%, rgba(245,197,24,0.06), transparent)" }} />
        {/* Same vertical lines as hero */}
        <div className="absolute right-0 top-0 w-full h-full">
          {[10, 20, 30, 40, 50, 60, 70, 80, 90].map((left, i) => (
            <div
              key={i}
              className="absolute top-0 w-px bg-gradient-to-b from-transparent via-[rgba(245,197,24,0.04)] to-transparent"
              style={{ left: `${left}%`, height: '100%' }}
            />
          ))}
        </div>
      </div>

      <div className="relative z-10 flex flex-col items-center text-center">
        <h2 className="font-bebas text-[clamp(44px,7vw,96px)] text-white leading-[0.92] m-0 max-w-[1000px]">
          GET YOUR LOAN APPROVED BEFORE<br />YOUR COFFEE GETS COLD.
        </h2>
        
        <button 
          onClick={onStartChat}
          className="mt-12 px-14 py-5 bg-[#F5C518] text-black font-sans font-bold text-[14px] tracking-[2px] rounded-sm border-none cursor-pointer transition-all duration-300 hover:shadow-[0_0_60px_rgba(245,197,24,0.5)] hover:-translate-y-0.5 active:translate-y-0 uppercase"
        >
          INITIALIZE NOW
        </button>

        <div className="mt-4 font-sans text-[11px] text-[#2a2a2a] tracking-[3px] uppercase">
          NO CREDIT IMPACT INQUIRY
        </div>
      </div>
    </section>
  );
};

const Footer = ({ onWhatsApp }: { onWhatsApp: () => void }) => {
  return (
    <footer className="bg-black border-t border-[#111] px-16 pt-20 pb-10">
      <div className="flex gap-20">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-bebas text-2xl text-[#F5C518]">₹</span>
            <span className="font-bebas text-2xl text-white tracking-widest">LOANEASE</span>
          </div>
          <p className="font-sans text-[12px] text-[#2a2a2a] tracking-[1px] mt-3 uppercase">
            REDEFINING LIQUIDITY THROUGH AI.
          </p>
        </div>

        <div className="flex flex-col gap-4">
          <span className="font-sans font-semibold text-[11px] text-[#333] tracking-[2px] uppercase">PLATFORM</span>
          <div className="flex flex-col gap-2 font-sans text-[13px] text-[#333]">
            <a href="#technology" className="hover:text-[#F5C518] transition-colors">Technology</a>
            <a href="#" className="hover:text-[#F5C518] transition-colors">Security</a>
            <a href="#features" className="hover:text-[#F5C518] transition-colors">Features</a>
            <a href="#" className="hover:text-[#F5C518] transition-colors">Research</a>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <span className="font-sans font-semibold text-[11px] text-[#333] tracking-[2px] uppercase">LEGAL</span>
          <div className="flex flex-col gap-2 font-sans text-[13px] text-[#333]">
            <a href="#" className="hover:text-[#F5C518] transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-[#F5C518] transition-colors">Terms of Service</a>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <span className="font-sans font-semibold text-[11px] text-[#333] tracking-[2px] uppercase">SOCIAL</span>
          <div className="flex flex-col gap-2 font-sans text-[13px] text-[#333]">
            <a href="#" className="hover:text-[#F5C518] transition-colors">Twitter/X</a>
            <a href="#" className="hover:text-[#F5C518] transition-colors">LinkedIn</a>
            <a href="#" className="hover:text-[#F5C518] transition-colors">GitHub</a>
            <button 
              onClick={onWhatsApp}
              className="text-left hover:text-[#F5C518] transition-colors font-sans text-[13px] text-[#333] mt-2"
            >
              Demo WhatsApp →
            </button>
          </div>
        </div>
      </div>

      <div className="mt-[60px] border-t border-[#0d0d0d] pt-6 flex justify-between items-center">
        <div className="font-sans text-[11px] text-[#1e1e1e]">
          © 2026 LoanEase • K.J. Somaiya College of Engineering • All Rights Reserved
        </div>
      </div>
    </footer>
  );
};

// --- Main Page Component ---

const LandingPage = () => {
  const [showChat, setShowChat] = useState(false);
  const chatAnchorRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!showChat) return;
    requestAnimationFrame(() => {
      chatAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [showChat]);

  const handleHowItWorks = () => {
    const el = document.getElementById("how-it-works");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  const handleWhatsApp = () => {
    navigate('/whatsapp');
  };

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
        }
      });
    }, { threshold: 0.15 });

    document.querySelectorAll('section').forEach(section => {
      section.classList.add('section-reveal');
      observer.observe(section);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <div className="bg-black text-white selection:bg-[#F5C518] selection:text-black min-h-screen">
      {/* Scroll indicator for sections */}
      <style>{`
        @font-face {
          font-family: 'Bebas Neue';
          src: url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');
        }
        .font-bebas { font-family: 'Bebas Neue', sans-serif; }
        .font-sans { font-family: 'DM Sans', sans-serif; }
        
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }

        .section-reveal {
          opacity: 0;
          transform: translateY(40px);
          transition: all 0.6s ease;
        }
        .section-reveal.active {
          opacity: 1;
          transform: translateY(0);
        }
      `}</style>

      {/* Nav */}
      <nav className="fixed top-0 left-0 w-full px-16 py-6 z-50 flex justify-between items-center mix-blend-difference">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => window.scrollTo({top: 0, behavior: 'smooth'})}>
          <span className="font-bebas text-2xl text-[#F5C518]">LOANEASE</span>
        </div>
        <div className="flex items-center gap-12">
          <a href="#features" className="font-bebas text-[11px] tracking-[3px] text-[#444] hover:text-[#F5C518] transition-colors uppercase">TECHNOLOGY</a>
          <button 
            onClick={() => setShowChat(true)}
            className="font-bebas text-[11px] tracking-[3px] bg-[#F5C518] text-black px-4 py-1.5 rounded-sm hover:scale-105 transition-all"
          >
            START APPLICATION
          </button>
        </div>
      </nav>

      <HeroSection onStartChat={() => setShowChat(true)} onHowItWorks={handleHowItWorks} onWhatsApp={handleWhatsApp} />
      
      <div id="scroll-content">
        <TrustBar />
        <FiveAgents />
        <ComparisonSection />
        <div id="how-it-works">
          <HowItWorks />
        </div>
        <CTAClose onStartChat={() => setShowChat(true)} />
        <Footer onWhatsApp={handleWhatsApp} />
      </div>

      <div ref={chatAnchorRef}>
        {showChat && (
          <div className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-md">
             <ChatInterface onClose={() => setShowChat(false)} />
          </div>
        )}
      </div>
    </div>
  );
};

export default LandingPage;
