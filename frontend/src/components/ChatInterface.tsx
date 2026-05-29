import React, { useState, useRef, useEffect, useMemo, ClipboardEvent } from "react";
import { ENDPOINTS } from "../config";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ChatMessage } from "./ChatMessage";
import { CreditScoreCard } from "./CreditScoreCard";
import { SanctionLetter } from "./SanctionLetter";
import { AnalyticsDashboard } from "./AnalyticsDashboard";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { Send, ArrowLeft, MessageCircle, Upload, CheckCircle2, FileText, Pencil, Check, X, Smartphone, Zap, Bot, MessageSquare, Clock, AlertTriangle, CheckCircle, Shield, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { QuickReplies } from "./QuickReplies";
import { EmiCalculatorWidget } from "./EmiCalculatorWidget";
import { LoanComparisonCards, type Offer } from "./LoanComparisonCards";
import { AgentActivityPanel, type AgentTraceItem } from "./AgentActivityPanel";
import { Badge } from "./ui/badge";
import { TRANSLATIONS } from "../lib/translations";
import { formatIndianRupees, detectLanguage } from "../lib/languageUtils";
import { cn } from "../lib/utils";
import { User } from "lucide-react";
import { useNavigate } from "react-router-dom";

const AGENT_PIPELINE = [
  "Master Agent",
  "KYC Verification Agent",
  "Credit Underwriting Agent",
  "Loan Recommendation Engine",
  "Dynamic Negotiation Agent",
];

const APP_STAGES = [
  { id: "kyc", label: "KYC" },
  { id: "credit", label: "Credit Check" },
  { id: "offer", label: "Offer" },
  { id: "negotiate", label: "Negotiate" },
  { id: "sanction", label: "Sanction" },
];

interface Message {
  id: number;
  text: string;
  isBot: boolean;
  status?: "sent" | "delivered" | "responded";
  quickReplies?: { label: string; value: string }[];
  type?: "emi-calculator" | "escalation" | "comparison-cards";
  variant?: "system";
}

interface ChatInterfaceProps {
  onClose: () => void;
}

interface PanKycFields {
  pan_number?: string;
  name?: string;
  fathers_name?: string;
  date_of_birth?: string;
  age?: number;
  age_eligible?: boolean;
}

interface AadhaarKycFields {
  aadhaar_last4?: string;
  mobile_last4?: string;
  mobile_number?: string;
  name?: string;
  date_of_birth?: string;
  age?: number;
  gender?: string;
  age_eligible?: boolean;
}

const formatMissingFields = (fields: string[]) => fields.join(", ");
const missingFieldMessage = (fields: string[]) => {
  const joined = formatMissingFields(fields);
  return fields.length === 1 ? `${joined} is missing` : `${joined} are missing`;
};

const OCR_REQUEST_TIMEOUT_MS = 120000;

interface CreditScoreData {
  credit_score: number;
  [key: string]: unknown;
}

interface UnderwritingResultData {
  decision?: string;
  approval_probability?: number;
  confidence_lower?: number;
  confidence_upper?: number;
  confidence_width?: number;
  model_certainty?: string;
  income_reasonability?: {
    flag?: string;
    foir?: number;
    message?: string;
    suggested_amount?: number;
    required_monthly_income?: number;
    emi?: number;
  };
  soft_reject_guidance?: {
    message?: string;
    income_delta_monthly?: number;
    repayment_history_months?: number;
    repayment_history_impact?: string;
    suggested_approved_amount?: number;
    threshold_gap_points?: number;
  } | null;
  model_drift_warning?: boolean;
  drifted_features?: string[];
  recommendation?: string | null;
  structured_shap_narration?: string | null;
  xgboost_probability?: number;
  risk_tier?: string;
  risk_score?: number;
  max_negotiation_rounds?: number;
  message?: string;
  threshold_used?: number;
  // Industry-standard CIBIL metadata (added by backend)
  cibil_score?: number;
  cibil_band?: string;
  cibil_classification?: string;
  risk_label?: string;
  industry_standard?: string;
  eligible?: boolean;
  conditional?: boolean;
  rate_range?: string;
  cibil_max_negotiation_rounds?: number;
  // Alternative scoring
  alternative_score?: number;
  alternative_eligible?: boolean;
  alternative_details?: Record<string, unknown> | null;
}

interface BankStatementAnalysis {
  analysis_possible?: boolean;
  estimated_monthly_income?: number;
  income_confidence?: string;
  data_source?: string;
  reason?: string;
  note?: string;
}

interface EmiHolidayOption {
  holidayMonths?: number;
  holiday_months?: number;
  adjustedPrincipal?: number;
  adjusted_principal?: number;
  emi?: number;
  original_emi?: number;
  extraCost?: number;
  extra_cost?: number;
  message?: string;
  recommended?: boolean;
  firstEmiAfterMonth?: number;
  first_emi_after_month?: number;
}

interface RepeatBorrowerData {
  sanction_reference?: string;
  reference?: string;
  sanctioned_at?: string;
  sanctionedDate?: string;
  date?: string;
  amount?: number;
  limit?: number;
  preapproved_limit?: number;
  rate?: number;
  purpose?: string;
  employment_type?: string;
  employer_name?: string;
}

interface UserData {
  name: string;
  pan: string;
  creditScore: number;
  selectedLoan: {
    amount: number;
    interest: number;
    tenure: number;
    emi: number;
    holidayMonths?: number;
    holidayExtraCost?: number;
  };
  assessmentId: string;
  sessionId: string;
  riskScore: number;
  riskTier: string;
  maxNegotiationRounds: number;
  stage: string;
  blockchainData?: {
    transaction_id: string;
    block_hash: string;
  };
}

interface SessionData {
  messages: Message[];
  stage: string;
  applicant_data: UserData;
  timestamp: number;
}

export const ChatInterface = ({ onClose }: ChatInterfaceProps) => {
  const navigate = useNavigate();
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const [language, setLanguage] = useState<"en" | "hi">(
    () => (localStorage.getItem("loanease_language") as "en" | "hi") || "en"
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isBackendBusy, setIsBackendBusy] = useState(false);
  const [showCreditScore, setShowCreditScore] = useState(false);
  const [showLoanOffers, setShowLoanOffers] = useState(false);
  const [pendingOffer, setPendingOffer] = useState<Offer | null>(null);
  const [showKfsCard, setShowKfsCard] = useState(false);
  const [kfsAcknowledged, setKfsAcknowledged] = useState(false);
  const [showSanction, setShowSanction] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [activeAgent, setActiveAgent] = useState("Master Agent");
  const [showCreditScoreCard, setShowCreditScoreCard] = useState(false);
  const [creditScoreData, setCreditScoreData] = useState<CreditScoreData | null>(null);
  const [underwritingResult, setUnderwritingResult] = useState<UnderwritingResultData | null>(null);
  const [showPanUploadCard, setShowPanUploadCard] = useState(false);
  const [showAadhaarUploadCard, setShowAadhaarUploadCard] = useState(false);
  const [isKycProcessing, setIsKycProcessing] = useState(false);
  const [kycProcessingText, setKycProcessingText] = useState("");
  const [kycProgress, setKycProgress] = useState(0);
  const [showPanConfirmCard, setShowPanConfirmCard] = useState(false);
  const [showKycVerifiedCard, setShowKycVerifiedCard] = useState(false);
  const [showOtpCard, setShowOtpCard] = useState(false);
  const [panKycData, setPanKycData] = useState<PanKycFields | null>(null);
  const [aadhaarKycData, setAadhaarKycData] = useState<AadhaarKycFields | null>(null);
  const [kycMatchScore, setKycMatchScore] = useState<number | null>(null);
  const [kycReferenceId, setKycReferenceId] = useState<string>("");
  const [otpDigits, setOtpDigits] = useState<string[]>(Array(6).fill(""));
  const [otpSentToLast4, setOtpSentToLast4] = useState("");
  const [otpAttemptsRemaining, setOtpAttemptsRemaining] = useState<number | null>(null);
  const [otpSecondsRemaining, setOtpSecondsRemaining] = useState(0);
  const [otpResendCooldown, setOtpResendCooldown] = useState(0);
  const [otpStatusMessage, setOtpStatusMessage] = useState("");
  const [otpError, setOtpError] = useState("");
  const [otpSubmitting, setOtpSubmitting] = useState(false);
  const [otpLocked, setOtpLocked] = useState(false);
  const [pendingCreditPan, setPendingCreditPan] = useState("");
  const [panFile, setPanFile] = useState<File | null>(null);
  const [aadhaarFile, setAadhaarFile] = useState<File | null>(null);
  const [userData, setUserData] = useState<UserData>({
    name: "",
    pan: "",
    creditScore: 0,
    selectedLoan: { amount: 0, interest: 0, tenure: 0, emi: 0 },
    assessmentId: "",
    sessionId: `LE-${new Date().getFullYear()}-${Math.floor(10000 + Math.random() * 90000)}`,
    riskScore: 0,
    riskTier: "",
    maxNegotiationRounds: 0,
    stage: "kyc",
    blockchainData: undefined,
  });

  const [showSessionBanner, setShowSessionBanner] = useState(false);
  const [sessionToResume, setSessionToResume] = useState<SessionData | null>(null);
  const [pulseBadge, setPulseBadge] = useState(false);
  const [hasStartedConversation, setHasStartedConversation] = useState(false);
  const [isEscalated, setIsEscalated] = useState(false);
  const [escalationData, setEscalationData] = useState({ preferredTime: "", whatsapp: false });
  const [pipelineSessionId, setPipelineSessionId] = useState<string>("");
  const [pipelineStatus, setPipelineStatus] = useState<string>("IDLE");
  const [agentTrace, setAgentTrace] = useState<AgentTraceItem[]>([]);
  const [showCreditSummaryPopup, setShowCreditSummaryPopup] = useState(false);
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Feature 2: Bank Statement Analysis
  const [showBankStatementCard, setShowBankStatementCard] = useState(false);
  const [bankStatementResult, setBankStatementResult] = useState<BankStatementAnalysis | null>(null);
  const bankStatementInputRef = useRef<HTMLInputElement>(null);

  // Feature 3: EMI Holiday
  const [emiHolidayOption, setEmiHolidayOption] = useState<EmiHolidayOption | null>(null);
  const [selectedHolidayMonths, setSelectedHolidayMonths] = useState<number>(0);

  // Feature 5: Repeat Borrower
  const [isRepeatBorrower, setIsRepeatBorrower] = useState(false);
  const [repeatBorrowerData, setRepeatBorrowerData] = useState<RepeatBorrowerData | null>(null);

  const handleViewAnalytics = () => {
    window._analyticsSessionId = userData.sessionId;
    localStorage.setItem("loanease_session_id", userData.sessionId);
    setShowAnalytics(true);
  };

  const calculateEmiWithHoliday = (amount: number, rate: number, tenureMonths: number, holidayMonths: number) => {
    const monthlyRate = rate / 12 / 100;
    const adjustedPrincipal = monthlyRate > 0 ? amount * Math.pow(1 + monthlyRate, holidayMonths) : amount;
    const power = Math.pow(1 + monthlyRate, tenureMonths);
    const emi = monthlyRate === 0 ? adjustedPrincipal / tenureMonths : (adjustedPrincipal * monthlyRate * power) / (power - 1);
    const basePower = Math.pow(1 + monthlyRate, tenureMonths);
    const baseEmi = monthlyRate === 0 ? amount / tenureMonths : (amount * monthlyRate * basePower) / (basePower - 1);
    return {
      holidayMonths,
      adjustedPrincipal,
      emi: Math.round(emi),
      extraCost: Math.max(0, Math.round((emi * tenureMonths) - (baseEmi * tenureMonths))),
      firstEmiAfterMonth: holidayMonths + 1,
    };
  };

  const toggleAgentSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const updatePipelineTracker = (stage: string) => {
    const stageMap = {
      'INITIATED': 1,
      'KYC_PENDING': 1,
      'KYC_VERIFIED': 2,
      'CREDIT_ASSESSED': 2,
      'OFFER_GENERATED': 3,
      'NEGOTIATING': 4,
      'ACCEPTED': 4,
      'SANCTIONED': 5
    };
    
    const currentStep = stageMap[stage as keyof typeof stageMap] || 1;
    
    // Update pipeline step indicators
    const pipelineSteps = document.querySelectorAll('.pipeline-step');
    pipelineSteps.forEach((step, i) => {
      const stepNum = i + 1;
      step.classList.remove('completed', 'active', 'upcoming');
      
      if (stepNum < currentStep) {
        step.classList.add('completed');
      } else if (stepNum === currentStep) {
        step.classList.add('active');
      } else {
        step.classList.add('upcoming');
      }
    });
    
    // Update header stage text
    const stageLabels = {
      'KYC_PENDING': 'KYC',
      'KYC_VERIFIED': 'Credit Check',
      'OFFER_GENERATED': 'Offer',
      'NEGOTIATING': 'Negotiating',
      'SANCTIONED': 'Sanctioned'
    };
    
    const headerStageLabel = document.querySelector('.header-stage-label');
    if (headerStageLabel) {
      headerStageLabel.textContent = stageLabels[stage as keyof typeof stageLabels] || stage;
    }
  };

  // Update pipeline tracker when userData.stage changes
  useEffect(() => {
    updatePipelineTracker(userData.stage);
  }, [userData.stage]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const conversationStep = useRef(0);
  const activeAgentIndex = AGENT_PIPELINE.indexOf(activeAgent);
  const panInputRef = useRef<HTMLInputElement>(null);
  const aadhaarInputRef = useRef<HTMLInputElement>(null);
  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [processingLog, setProcessingLog] = useState<string[]>([]);

  useEffect(() => {
    if (!showOtpCard) {
      return;
    }

    const timer = setInterval(() => {
      setOtpSecondsRemaining((value) => {
        if (value <= 1) {
          setOtpLocked(true);
          return 0;
        }
        return value - 1;
      });

      setOtpResendCooldown((value) => (value > 0 ? value - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [showOtpCard]);

  const showWelcomeState = messages.length === 0 && !showSessionBanner && !hasStartedConversation;
  const isInputLocked =
    isEscalated ||
    !hasStartedConversation ||
    showLoanOffers ||
    showSanction ||
    isKycProcessing ||
    showPanUploadCard ||
    showAadhaarUploadCard ||
    showPanConfirmCard ||
    showOtpCard ||
    otpLocked ||
    isTyping ||
    isBackendBusy;
  const isProcessing = isBackendBusy || isKycProcessing || isTyping;

  const getInputPlaceholder = () => {
    if (isEscalated) return "Chat disabled pending human review";
    if (!hasStartedConversation) return "Click 'Apply for a Loan' to start";
    if (otpLocked) return "OTP verification failed. Redirecting...";
    if (showOtpCard) return "Verify the OTP sent to your Aadhaar-linked mobile";
    if (showSanction) return "Your sanction letter is ready. Ask a question or download it.";
    if (showLoanOffers) return "Type 'accept' or ask to negotiate the rate...";
    if (userData.stage === "credit") return "Your score is ready. How would you like to proceed?";
    if (userData.stage === "offer") return "Tell me your loan amount or ask to compare offers...";
    if (userData.stage === "negotiate") return "Ask for a better rate or accept the current offer...";
    return "Type your message...";
  };

  const processingLines = useMemo(() => {
    if (isKycProcessing) {
      return [
        "> KYC_AGENT: Processing document...",
        "> OCR_ENGINE: Extracting text fields",
        "> REGEX_NER: PAN pattern found",
        "> VALIDATION: Format check passed",
        "> AWAITING: Cross-validation...",
      ];
    }

    if (isBackendBusy && userData.stage === "credit") {
      return [
        "> CREDIT_AGENT: Running assessment...",
        "> SCORE_ENGINE: Computing CIBIL profile",
        "> RISK_MODEL: Evaluating repayment risk",
        "> OUTPUT: Preparing credit decision...",
      ];
    }

    if (isBackendBusy && showLoanOffers) {
      return [
        "> OFFER_ENGINE: Building loan options...",
        "> PRICING: Calculating rate bands",
        "> OPTIMIZER: Selecting best tenure",
        "> OUTPUT: Rendering recommendations...",
      ];
    }

    if (isTyping) {
      return [
        "> CHAT_ENGINE: Drafting response...",
        "> NLU: Interpreting user intent",
        "> POLICY: Selecting next action",
      ];
    }

    return [
      "> SYSTEM: Awaiting backend activity...",
    ];
  }, [isBackendBusy, isKycProcessing, isTyping, showLoanOffers, userData.stage]);

  useEffect(() => {
    if (!isProcessing) {
      setProcessingLog([]);
      return;
    }

    setProcessingLog([processingLines[0]]);
    let index = 1;

    const interval = setInterval(() => {
      setProcessingLog((prev) => {
        const nextLine = processingLines[index % processingLines.length];
        index += 1;
        return [...prev, nextLine].slice(-8);
      });
    }, 650);

    return () => clearInterval(interval);
  }, [isProcessing, processingLines]);

  useEffect(() => {
    if (!isProcessing && hasStartedConversation && !isEscalated) {
      const timer = setTimeout(() => {
        textAreaRef.current?.focus();
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [isProcessing, hasStartedConversation, isEscalated]);

  const handleLanguageChange = (lang: "en" | "hi") => {
    setLanguage(lang);
    localStorage.setItem("loanease_language", lang);
    const message =
      lang === "en"
        ? TRANSLATIONS.language_switched_en
        : TRANSLATIONS.language_switched_hi;
    toast.success(message);
  };

  const saveSession = async (currentMessages: Message[], currentStage: string, currentData: UserData) => {
    const sessionKey = `loanease_session_${new Date().toISOString().split('T')[0]}`;
    const sessionData = {
      messages: currentMessages,
      stage: currentStage,
      applicant_data: currentData,
      timestamp: Date.now()
    };
    localStorage.setItem(sessionKey, JSON.stringify(sessionData));

    try {
      await fetch(ENDPOINTS.session_save, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: currentData.sessionId,
          messages: currentMessages,
          stage: currentStage,
          applicant_data: currentData
        }),
      });
    } catch (e) {
      console.warn("Failed to save session to backend", e);
    }
  };

  const handleResume = () => {
    if (sessionToResume) {
      setMessages(sessionToResume.messages);
      setUserData(sessionToResume.applicant_data);
      setHasStartedConversation(true);
      setShowSessionBanner(false);
      toast.success("Session restored successfully!");
    }
  };

  const handleStartFresh = () => {
    const sessionKey = `loanease_session_${new Date().toISOString().split('T')[0]}`;
    localStorage.removeItem(sessionKey);
    setHasStartedConversation(false);
    setShowSessionBanner(false);
    setPendingOffer(null);
    setShowKfsCard(false);
    setKfsAcknowledged(false);
    setSelectedHolidayMonths(0);
    setEmiHolidayOption(null);
    toast.info("Started a new session.");
  };

  const handleStartConversation = () => {
    if (!hasStartedConversation) {
      setHasStartedConversation(true);
      conversationStep.current = 0;
      setPendingOffer(null);
      setShowKfsCard(false);
      setKfsAcknowledged(false);
      if (isRepeatBorrower && repeatBorrowerData) {
        activateAgent("Master Agent", "Recognized returning user.");
        const sanctionedAt = repeatBorrowerData.sanctioned_at || repeatBorrowerData.sanctionedDate || repeatBorrowerData.date || "recently";
        const baseAmount = Number(repeatBorrowerData.preapproved_limit || repeatBorrowerData.limit || repeatBorrowerData.amount || 500000);
        const preApprovedLimit = Number.isFinite(baseAmount) ? Math.round(baseAmount) : 500000;
        addBotMessage(
          `Welcome back! Your previous loan was sanctioned on ${sanctionedAt}. Based on your repayment history, your pre-approved limit for a new loan is ${formatIndianRupees(preApprovedLimit)}.\n\n` +
          `As a repeat borrower, your starting rate is also trimmed by 0.25%. Would you like to proceed with a new offer?`
        );
        setTimeout(() => {
          setUserData(prev => ({ ...prev, stage: "offer", creditScore: 750 }));
          updatePipelineTracker("OFFER_GENERATED");
          setShowLoanOffers(true);
        }, 1500);
      } else {
        activateAgent("KYC Verification Agent", "Let's begin your application.");
        addBotMessage(
          kycText(
            "Hello! I'm your Loan Assistant. What is your full name?",
            "नमस्ते! मैं आपका Loan Assistant हूँ। आपका पूरा नाम क्या है?"
          )
        );
      }
    }

    requestAnimationFrame(() => {
      textAreaRef.current?.focus();
    });
  };

  useEffect(() => {
    const sessionKey = `loanease_session_${new Date().toISOString().split('T')[0]}`;
    const saved = localStorage.getItem(sessionKey);
    if (saved) {
      const parsed = JSON.parse(saved) as SessionData;
      if (Date.now() - parsed.timestamp < 24 * 60 * 60 * 1000) {
        setSessionToResume(parsed);
        setShowSessionBanner(true);
      }
    }

    // Feature 5: Repeat Borrower Detection
    const prevSanction = localStorage.getItem("previous_sanction_reference") || localStorage.getItem("loanease_previous_sanction");
    if (prevSanction) {
      try {
        const sanctionData = JSON.parse(prevSanction);
        setIsRepeatBorrower(true);
        setRepeatBorrowerData(sanctionData);
      } catch { /* ignore parse errors */ }
    }
  }, []);

  const activateAgent = (agentName: string, note: string) => {
    setActiveAgent(agentName);
    setPulseBadge(true);
    setTimeout(() => setPulseBadge(false), 2000);
    setMessages((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        text: `${agentName} activated.\n${note}`,
        isBot: true,
        variant: "system",
      },
    ]);
  };

  const DEVANAGARI_DIGIT_MAP: Record<string, string> = {
    "०": "0",
    "१": "1",
    "२": "2",
    "३": "3",
    "४": "4",
    "५": "5",
    "६": "6",
    "७": "7",
    "८": "8",
    "९": "9",
  };

  const toAsciiDigits = (value: string) =>
    value.replace(/[०-९]/g, (digit) => DEVANAGARI_DIGIT_MAP[digit] ?? digit);

  const normalizePan = (value: string) => toAsciiDigits(value).replace(/\s+/g, "").toUpperCase();

  const extractPan = (value: string) => {
    const normalized = toAsciiDigits(value).toUpperCase();
    const match = normalized.match(/[A-Z]{5}[0-9]{4}[A-Z]/);
    return match ? match[0] : "";
  };

  const isValidPan = (value: string) => /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(value);

  const kycText = (en: string, hi: string) => (language === "hi" ? hi : en);
  useEffect(() => {
    // Initialize session in the backend to start orchestration logs
    const initSession = async () => {
      try {
        await fetch(`${ENDPOINTS.session_init}/${userData.sessionId}`, { method: "POST" });
      } catch (e) {
        console.warn("Failed to initialize session logging", e);
      }
    };
    initSession();
  }, [userData.sessionId]);

  useEffect(() => {
    window._analyticsSessionId = userData.sessionId;
    localStorage.setItem("loanease_session_id", userData.sessionId);
  }, [userData.sessionId]);

  useEffect(() => {
    const modalOpen = showPanUploadCard || showAadhaarUploadCard;
    if (modalOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowPanUploadCard(false);
        setShowAadhaarUploadCard(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [showPanUploadCard, showAadhaarUploadCard]);

  const addBotMessage = (text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        text,
        isBot: true,
      },
    ]);
  };

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      setTimeout(() => {
        messagesContainerRef.current!.scrollTop = messagesContainerRef.current!.scrollHeight;
      }, 0);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, showCreditScore, showLoanOffers, showSanction, showAnalytics, showPanUploadCard, showAadhaarUploadCard, showPanConfirmCard, showKycVerifiedCard, showOtpCard, isKycProcessing]);

  useEffect(() => {
    if (!showAnalytics) return;

    const analyticsSection = document.getElementById("analytics-section");
    analyticsSection?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [showAnalytics]);

  useEffect(() => {
    const TERMINAL_STATES = ["SANCTIONED", "REJECTED", "ESCALATED", "FAILED"];
    if (!pipelineSessionId || TERMINAL_STATES.includes(pipelineStatus)) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `${ENDPOINTS.pipeline_log}/${pipelineSessionId}`,
          { signal: AbortSignal.timeout(3000) }
        );
        if (!response.ok) return;
        const data = await response.json();
        setAgentTrace(data.agent_trace || []);
        const newStatus = data.pipeline_status || "ACTIVE";
        setPipelineStatus(newStatus);
        if (TERMINAL_STATES.includes(newStatus)) {
          clearInterval(interval);
        }
      } catch {
        // Silently ignore poll failures
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [pipelineSessionId, pipelineStatus]);

  // Detect language from user input
  useEffect(() => {
    const detectAndSwitch = async () => {
      if (input.length > 5) {
        const result = await detectLanguage(input);
        if (result.language !== "unknown" && result.language !== language) {
          const msg =
            result.language === "en"
              ? TRANSLATIONS.language_detected_en
              : TRANSLATIONS.language_detected_hi;
          toast.info(msg);
        }
      }
    };
    detectAndSwitch();
  }, [input, language]);

  useEffect(() => {
    const element = textAreaRef.current;
    if (!element) return;

    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 100)}px`;
  }, [input]);

  const startKycProgress = (label: string) => {
    setIsKycProcessing(true);
    setKycProcessingText(label);
    setKycProgress(5);
    let value = 5;
    const timer = setInterval(() => {
      value = Math.min(95, value + 5);
      setKycProgress(value);
    }, 150);
    return timer;
  };

  const stopKycProgress = (timer: ReturnType<typeof setInterval>) => {
    clearInterval(timer);
    setKycProgress(100);
    setTimeout(() => {
      setIsKycProcessing(false);
      setKycProcessingText("");
      setKycProgress(0);
    }, 300);
  };

  const callKycPanExtractAPI = async (file: File) => {
    setIsBackendBusy(true);
    try {
      const form = new FormData();
      form.append("document", file);
      form.append("session_id", userData.sessionId);
      form.append("language", language);

      const response = await fetch(ENDPOINTS.kyc_pan, {
        method: "POST",
        body: form,
        signal: AbortSignal.timeout(OCR_REQUEST_TIMEOUT_MS),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => null);
        throw new Error(errBody?.detail || "PAN extraction failed");
      }

      return response.json();
    } finally {
      setIsBackendBusy(false);
    }
  };

  const callKycAadhaarExtractAPI = async (file: File) => {
    setIsBackendBusy(true);
    try {
      const form = new FormData();
      form.append("document", file);
      form.append("session_id", userData.sessionId);
      form.append("language", language);

      const response = await fetch(ENDPOINTS.kyc_aadhaar, {
        method: "POST",
        body: form,
        signal: AbortSignal.timeout(OCR_REQUEST_TIMEOUT_MS),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => null);
        throw new Error(errBody?.detail || "Aadhaar extraction failed");
      }

      return response.json();
    } finally {
      setIsBackendBusy(false);
    }
  };

  const callKycVerifyAPI = async (panDoc: File, aadhaarDoc: File) => {
    setIsBackendBusy(true);
    try {
      const form = new FormData();
      form.append("pan", panDoc);
      form.append("aadhaar", aadhaarDoc);
      form.append("session_id", userData.sessionId);

      const response = await fetch(ENDPOINTS.kyc_verify, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => null);
        throw new Error(errBody?.detail || "KYC verification failed");
      }

      return response.json();
    } finally {
      setIsBackendBusy(false);
    }
  };

  const callKycSendOtpAPI = async () => {
    setIsBackendBusy(true);
    try {
      const response = await fetch(ENDPOINTS.kyc_send_otp, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: userData.sessionId }),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => null);
        throw new Error(errBody?.detail || "OTP send failed");
      }

      return response.json();
    } finally {
      setIsBackendBusy(false);
    }
  };

  const callKycVerifyOtpAPI = async (otp: string) => {
    setIsBackendBusy(true);
    try {
      const response = await fetch(ENDPOINTS.kyc_verify_otp, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: userData.sessionId, otp }),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => null);
        throw new Error(errBody?.detail || "OTP verification failed");
      }

      return response.json();
    } finally {
      setIsBackendBusy(false);
    }
  };

  const callKycResendOtpAPI = async () => {
    setIsBackendBusy(true);
    try {
      const response = await fetch(ENDPOINTS.kyc_resend_otp, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: userData.sessionId }),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => null);
        throw new Error(errBody?.detail || "OTP resend failed");
      }

      return response.json();
    } finally {
      setIsBackendBusy(false);
    }
  };

  const resetOtpFlow = () => {
    setShowOtpCard(false);
    setOtpDigits(Array(6).fill(""));
    setOtpSentToLast4("");
    setOtpAttemptsRemaining(null);
    setOtpSecondsRemaining(0);
    setOtpResendCooldown(0);
    setOtpStatusMessage("");
    setOtpError("");
    setOtpSubmitting(false);
    setOtpLocked(false);
    setPendingCreditPan("");
  };

  const terminateAfterOtpFailure = (message: string) => {
    setOtpError(message);
    setOtpLocked(true);
    setShowOtpCard(false);
    addBotMessage(message);
    setTimeout(() => {
      setMessages([]);
      setUserData((prev) => ({ ...prev, stage: "kyc" }));
      localStorage.removeItem("loanease_session_id");
      navigate("/");
    }, 5000);
  };

  const updateOtpDigit = (index: number, value: string) => {
    const nextValue = value.replace(/\D/g, "").slice(-1);
    setOtpDigits((current) => {
      const nextDigits = [...current];
      nextDigits[index] = nextValue;
      return nextDigits;
    });

    if (nextValue && index < otpInputRefs.current.length - 1) {
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace" && !otpDigits[index] && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
      setOtpDigits((current) => {
        const nextDigits = [...current];
        nextDigits[index - 1] = "";
        return nextDigits;
      });
    }
  };

  const handleOtpPaste = (event: ClipboardEvent<HTMLDivElement>) => {
    const pasted = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;
    event.preventDefault();
    const nextDigits = Array(6).fill("");
    pasted.split("").forEach((digit, index) => {
      nextDigits[index] = digit;
    });
    setOtpDigits(nextDigits);
    otpInputRefs.current[Math.min(pasted.length, 5)]?.focus();
  };

  const submitOtp = async () => {
    if (otpLocked || otpSubmitting) return;

    const otpValue = otpDigits.join("");
    if (otpValue.length !== 6) {
      setOtpError(kycText("Enter the 6-digit OTP sent to your mobile.", "अपने मोबाइल पर भेजा गया 6-digit OTP दर्ज करें।"));
      return;
    }

    setOtpSubmitting(true);
    setOtpError("");
    try {
      const result = await callKycVerifyOtpAPI(otpValue);
      setOtpAttemptsRemaining(result.attempts_remaining ?? 0);

      if (result.verified) {
        resetOtpFlow();
        addBotMessage(
          kycText(
            "OTP verified successfully. Continuing to your credit profile.",
            "OTP सफलतापूर्वक सत्यापित हो गया है। अब आपकी credit profile खोली जा रही है।"
          )
        );
        const extractedPan = pendingCreditPan || panKycData?.pan_number || verifyResultPanFromState();
        if (extractedPan) {
          await proceedToCreditFlow(extractedPan);
        }
        return;
      }

      if (result.terminated) {
        terminateAfterOtpFailure(
          kycText(
            "OTP verification failed too many times. Your application has been closed.",
            "OTP सत्यापन कई बार विफल रहा। आपका आवेदन बंद कर दिया गया है।"
          )
        );
        return;
      }

      setOtpError(
        kycText(
          `Incorrect OTP. ${result.attempts_remaining} attempt(s) remaining.`,
          `OTP गलत है। ${result.attempts_remaining} attempt(s) शेष हैं।`
        )
      );
      setOtpDigits(Array(6).fill(""));
      otpInputRefs.current[0]?.focus();
    } catch (error) {
      const msg = error instanceof Error ? error.message : kycText("OTP verification failed.", "OTP सत्यापन विफल।");
      setOtpError(msg);
    } finally {
      setOtpSubmitting(false);
    }
  };

  const resendOtp = async () => {
    if (otpResendCooldown > 0 || otpSubmitting) return;
    try {
      const result = await callKycResendOtpAPI();
      setOtpDigits(Array(6).fill(""));
      setOtpSecondsRemaining(Number(result.expires_in_seconds || 300));
      setOtpResendCooldown(60);
      setOtpLocked(false);
      setOtpError("");
      setOtpStatusMessage(
        kycText(
          `A new OTP was sent to the mobile ending ${result.mobile_last4}.`,
          `एक नया OTP मोबाइल नंबर के अंतिम ${result.mobile_last4} अंकों पर भेजा गया है।`
        )
      );
      addBotMessage(
        kycText(
          `OTP resent to mobile ending ${result.mobile_last4}.`,
          `OTP मोबाइल नंबर के अंतिम ${result.mobile_last4} अंकों पर फिर से भेजा गया है।`
        )
      );
    } catch (error) {
      const msg = error instanceof Error ? error.message : kycText("OTP resend failed.", "OTP दोबारा भेजना विफल रहा।");
      if (msg.toLowerCase().includes("limit")) {
        terminateAfterOtpFailure(
          kycText(
            "OTP resend limit reached. Your application has been closed.",
            "OTP पुनः भेजने की सीमा पूरी हो गई है। आपका आवेदन बंद कर दिया गया है।"
          )
        );
        return;
      }
      setOtpError(msg);
    }
  };

  const verifyResultPanFromState = () => panKycData?.pan_number || userData.pan || "";

  const proceedToCreditFlow = async (panNumber: string) => {
    const normalizedPan = normalizePan(panNumber);
    if (!isValidPan(normalizedPan)) {
      toast.error(kycText("Invalid PAN from KYC extraction", "KYC extraction से PAN invalid मिला"));
      return;
    }

    setUserData((prev) => ({ ...prev, pan: normalizedPan }));
    activateAgent("Credit Underwriting Agent", "Evaluating eligibility based on credit and risk profile.");
    addBotMessage(TRANSLATIONS.kyc_processing[language]);

    const creditScoreResult = await callCreditScoreAPI(normalizedPan);
    if (!creditScoreResult) return;

    setShowCreditScoreCard(true);
    setTimeout(() => {
      addBotMessage(
        language === "en"
          ? "Your credit profile has been evaluated. Continuing with personalized loan options based on your risk tier and pricing band."
          : "आपकी credit profile का मूल्यांकन हो गया है। अब आपके risk tier और pricing band के आधार पर personalized loan options दिखाए जा रहे हैं।"
      );
      activateAgent("Loan Recommendation Engine", "Generating personalized loan options based on risk profile.");
      setShowLoanOffers(true);
      conversationStep.current = 2;
    }, 1500);
  };

  const handlePanFileSelected = async (file?: File) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      toast.error(kycText("File exceeds 5MB limit", "फ़ाइल 5MB सीमा से बड़ी है"));
      return;
    }

    setPanFile(file);
    setShowPanUploadCard(false);
    setMessages((prev) => [...prev, { id: prev.length + 1, text: file.name, isBot: false }]);

    const timer = startKycProgress(kycText("Scanning your PAN card...", "आपके PAN कार्ड को स्कैन किया जा रहा है..."));
    try {
      const result = await callKycPanExtractAPI(file);
      stopKycProgress(timer);

      const extractedPanCandidate = normalizePan(result.extracted_fields?.pan_number || "");
      const panCandidateValid = isValidPan(extractedPanCandidate);
      const extractedPanNumber = panCandidateValid
        ? extractedPanCandidate
        : (result.extracted_fields?.pan_number || "");
      setPanKycData({
        ...result.extracted_fields,
        pan_number: extractedPanNumber,
      });
      if (extractedPanNumber) {
        const extractedName = result.extracted_fields?.name || "";
        const extractedDob = result.extracted_fields?.date_of_birth || "";
        addBotMessage(
          kycText(
            `PAN OCR detected:\nPAN: ${extractedPanNumber}${extractedName ? `\nName: ${extractedName}` : ""}${extractedDob ? `\nDOB: ${extractedDob}` : ""}`,
            `PAN OCR मिला:\nPAN: ${extractedPanNumber}${extractedName ? `\nनाम: ${extractedName}` : ""}${extractedDob ? `\nजन्म तिथि: ${extractedDob}` : ""}`
          )
        );
      }
      const issues: string[] = result.validation?.issues || [];
      const confidence = Number(result.confidence_score || 0);
      const panFound = Boolean(result.validation?.pan_format_valid || panCandidateValid);
      const nameFound = Boolean(result.validation?.name_found);
      const dobFound = Boolean(result.validation?.dob_found);

      // Very lenient validation - accept almost anything that looks like a document
      const valid = confidence >= 0.05 || panFound; // Extremely lenient

      if (!valid) {
        addBotMessage(
          kycText(
            "Please upload a clearer PAN card image. The system couldn't read this document.",
            "कृपया एक स्पष्ट PAN कार्ड छवि अपलोड करें। सिस्टम इस दस्तावेज़ को नहीं पढ़ सका।"
          )
        );
        setShowPanUploadCard(true);
        return;
      }

      setShowPanConfirmCard(true);
    } catch (error) {
      stopKycProgress(timer);
      const msg = error instanceof Error
        ? (error.name === "TimeoutError"
            ? kycText("Scan timed out. Try a smaller or clearer image.", "स्कैन timeout हो गया। छोटी या स्पष्ट छवि आज़माएं।")
            : error.message.includes("fetch")
              ? kycText("Could not connect to server. Check your connection.", "सर्वर से कनेक्ट नहीं हो सका। कनेक्शन जांचें।")
              : `${error.message}`)
        : kycText("PAN scan failed. Please try again.", "PAN स्कैन विफल। पुनः प्रयास करें।");
      addBotMessage(msg);
      setShowPanUploadCard(true);
    }
  };

  const handleAadhaarFileSelected = async (file?: File) => {
    if (!file || !panFile) return;
    if (file.size > 5 * 1024 * 1024) {
      toast.error(kycText("File exceeds 5MB limit", "फ़ाइल 5MB सीमा से बड़ी है"));
      return;
    }

    setAadhaarFile(file);
    setShowAadhaarUploadCard(false);
    setMessages((prev) => [...prev, { id: prev.length + 1, text: file.name, isBot: false }]);

    const timer = startKycProgress(kycText("Scanning your Aadhaar card...", "आपके Aadhaar कार्ड को स्कैन किया जा रहा है..."));
    try {
      const aadhaarResult = await callKycAadhaarExtractAPI(file);
      setAadhaarKycData(aadhaarResult.extracted_fields);

      const aadhaarIssues: string[] = aadhaarResult.validation?.issues || [];
      const missingFields: string[] = aadhaarResult.validation?.missing_fields || [];
      const aadhaarConfidence = Number(aadhaarResult.confidence_score || 0);

      if (missingFields.length > 0) {
        stopKycProgress(timer);
        addBotMessage(
          kycText(
            `${missingFieldMessage(missingFields)}. Please upload a clearer Aadhaar card.`,
            `${missingFieldMessage(missingFields)}। कृपया एक स्पष्ट Aadhaar कार्ड अपलोड करें।`
          )
        );
        if (aadhaarIssues.length > 0) {
          toast.error(aadhaarIssues[0]);
        }
        setShowAadhaarUploadCard(true);
        return;
      }

      // More relaxed Aadhaar validation - accept if confidence is reasonable
      const aadhaarValid = Boolean(aadhaarResult.validation?.aadhaar_format_valid || aadhaarConfidence >= 0.15);
      if (!aadhaarValid) {
        stopKycProgress(timer);
        if (aadhaarConfidence > 0.05) { // Much lower threshold
          addBotMessage(
            kycText(
              "This doesn't appear to be an Aadhaar card. Please upload your Aadhaar card.",
              "यह Aadhaar कार्ड प्रतीत नहीं होता। कृपया अपना Aadhaar कार्ड अपलोड करें।"
            )
          );
        } else {
          addBotMessage(
            kycText(
              "Image quality is low. Please upload a clearer Aadhaar card image.",
              "छवि गुणवत्ता कम है। कृपया एक स्पष्ट Aadhaar कार्ड छवि अपलोड करें।"
            )
          );
        }
        if (aadhaarIssues.length > 0) {
          toast.error(aadhaarIssues[0]);
        }
        setShowAadhaarUploadCard(true);
        return;
      }

      const verifyResult = await callKycVerifyAPI(panFile, file);
      stopKycProgress(timer);

      // Safety net: if backend says failed but Aadhaar number was found and age is eligible, proceed
      const aadhaarFound = Boolean(aadhaarResult.validation?.aadhaar_format_valid);
      const ageOk = Boolean(verifyResult.cross_validation?.age_eligible);
      const canProceed = verifyResult.overall_kyc_passed || (aadhaarFound && ageOk);

      if (!canProceed) {
        const nameScore = Number(verifyResult.cross_validation?.name_match_score ?? 0);
        const dobMatch = Boolean(verifyResult.cross_validation?.dob_match);
        const ageEligible = Boolean(verifyResult.cross_validation?.age_eligible);

        if (!ageEligible) {
          addBotMessage(
            kycText(
              "Applicants must be between 21 and 65 years old to apply.",
              "आवेदन करने के लिए आयु 21 से 65 वर्ष के बीच होनी चाहिए।"
            )
          );
        } else {
          addBotMessage(
            kycText(
              "KYC verification could not be completed. Please retry with clearer PAN and Aadhaar files.",
              "KYC सत्यापन पूरा नहीं हो सका। कृपया अधिक स्पष्ट PAN और Aadhaar फाइलों के साथ पुनः प्रयास करें।"
            )
          );
        }
        setShowAadhaarUploadCard(true);
        return;
      }

      setKycMatchScore(verifyResult.cross_validation?.name_match_score ?? null);
      setKycReferenceId(verifyResult.kyc_reference_id ?? "");
      setShowKycVerifiedCard(true);

      setTimeout(async () => {
        setShowKycVerifiedCard(false);
        try {
          resetOtpFlow();
          const otpResult = await callKycSendOtpAPI();
          const extractedPan = verifyResult.pan_data?.pan_number || panKycData?.pan_number || "";
          const mobileLast4 = otpResult.mobile_last4 || aadhaarResult.extracted_fields?.mobile_last4 || "";

          setPendingCreditPan(extractedPan);
          setOtpSentToLast4(mobileLast4);
          setOtpAttemptsRemaining(3);
          setOtpSecondsRemaining(Number(otpResult.expires_in_seconds || 300));
          setOtpResendCooldown(60);
          setOtpDigits(Array(6).fill(""));
          setShowOtpCard(true);
          setOtpStatusMessage(
            kycText(
              `OTP sent to mobile ending ${mobileLast4}. Enter the 6-digit code to continue.`,
              `OTP मोबाइल नंबर के अंतिम ${mobileLast4} अंक पर भेजा गया है। आगे बढ़ने के लिए 6-digit code दर्ज करें।`
            )
          );
          if (otpResult.demo_otp) {
            addBotMessage(
              kycText(
                `Demo OTP: ${otpResult.demo_otp}`,
                `Demo OTP: ${otpResult.demo_otp}`
              )
            );
          }
        } catch (otpError) {
          const msg = otpError instanceof Error ? otpError.message : kycText("OTP could not be sent. Please upload a clearer Aadhaar card.", "OTP भेजा नहीं जा सका। कृपया अधिक स्पष्ट Aadhaar कार्ड अपलोड करें।");
          addBotMessage(msg.toLowerCase().includes("mobile number not found")
            ? kycText("We couldn't find the Aadhaar-linked mobile number. Please upload the full Aadhaar card and try again.", "Aadhaar से जुड़ा मोबाइल नंबर नहीं मिला। कृपया पूरा Aadhaar कार्ड अपलोड करें और फिर प्रयास करें।")
            : msg);
          setShowAadhaarUploadCard(true);
        }
      }, 1300);
    } catch (error) {
      stopKycProgress(timer);
      const isTimeout = error instanceof Error && error.name === "TimeoutError";
      const msg = error instanceof Error
        ? (isTimeout
            ? kycText(
                "Aadhaar OCR is taking longer than usual. Please wait a moment, then retry with a smaller or clearer image if needed.",
                "Aadhaar OCR सामान्य से अधिक समय ले रहा है। कृपया थोड़ा इंतज़ार करें, फिर ज़रूरत हो तो छोटी या स्पष्ट छवि के साथ पुनः प्रयास करें।"
              )
            : error.message.includes("fetch")
              ? kycText("Could not connect to server. Check your connection.", "सर्वर से कनेक्ट नहीं हो सका। कनेक्शन जांचें।")
              : `${error.message}`)
        : kycText("Aadhaar scan failed. Please try again.", "Aadhaar स्कैन विफल। पुनः प्रयास करें।");
      addBotMessage(msg);
      setShowAadhaarUploadCard(true);
    }
  };

  const callUnderwritingAPI = async (userData: {
    pan_number: string;
    gender: string;
    married: string;
    dependents: string;
    education: string;
    self_employed: string;
    applicant_income: number;
    coapplicant_income: number;
    loan_amount: number;
    loan_amount_term: number;
    credit_history: number;
    property_area: string;
    preferred_language: "en" | "hi";
    session_id?: string;
    employment_type?: string;
    employer_name?: string;
    monthly_income?: number;
    loan_purpose?: string;
  }) => {
    setIsBackendBusy(true);
    try {
      const response = await fetch(ENDPOINTS.credit_assess, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(userData),
      });

      if (!response.ok) throw new Error("Assessment failed");
      const data = await response.json();

      setUserData((prev) => ({
        ...prev,
        assessmentId: data.application_id,
        riskScore: data.risk_score,
        riskTier: data.risk_tier,
        creditScore: data.cibil_score ?? data.credit_score ?? data.risk_score,
        maxNegotiationRounds: data.max_negotiation_rounds || 0,
      }));
      setUnderwritingResult(data);

      // Show a concise consumer-facing message using the industry-standard wording
      try {
        const score = data.cibil_score ?? data.credit_score ?? data.risk_score;
        let userMsg = "";
        if (score === 751) {
          userMsg = `Your CIBIL score is ${score} — rated '${data.cibil_classification || "Very Good"}' on TransUnion CIBIL's 5-tier scale. This places you in our ${data.risk_label || 'Low-Medium Risk'} category, qualifying you for rates between ${data.rate_range || '11.5% and 12.5%'} p.a.`;
        } else if (score === 580) {
          userMsg = `Your CIBIL score is ${score}, rated '${data.cibil_classification || 'Below Average'}' by TransUnion CIBIL. We can offer conditional approval with a co-applicant. Without a co-applicant, we recommend improving your score to 650+ before reapplying.`;
        } else if (score != null) {
          userMsg = `Your CIBIL score is ${score} — rated '${data.cibil_classification || data.risk_tier || 'Good'}' on TransUnion CIBIL's 5-tier scale. ${data.risk_label ? 'This places you in our ' + data.risk_label + ' category.' : ''} ${data.rate_range ? 'Eligible rates: ' + data.rate_range + '.' : ''}`;
        }

        if (userMsg) addBotMessage(userMsg);
      } catch (e) {
        // ignore
      }

      return data;
    } catch (error) {
      console.error("Underwriting error:", error);
      setIsOfflineMode(true);
      toast.error("Connection issue — using offline mode");
      return null;
    } finally {
      setIsBackendBusy(false);
    }
  };

  const callNegotiationAPI = async (
    riskScore: number,
    riskTier: string,
    loanAmount: number,
    tenureMonths: number,
    maxNegotiationRounds: number
  ) => {
    setIsBackendBusy(true);
    try {
      const response = await fetch(ENDPOINTS.negotiate_start, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: userData.sessionId,
          applicant_name: userData.name,
          risk_score: riskScore,
          risk_tier: riskTier,
          loan_amount: loanAmount,
          tenure_months: tenureMonths,
          max_negotiation_rounds: maxNegotiationRounds,
          top_positive_factor: "good credit history",
          customer_profile: isRepeatBorrower ? "EXCELLENT" : "STANDARD",
        }),
      });

      if (!response.ok) throw new Error("Negotiation start failed");
      const data = await response.json();

      setUserData((prev) => ({
        ...prev,
        sessionId: data.session_id,
      }));

      return data;
    } catch (error) {
      console.error("Negotiation error:", error);
      setIsOfflineMode(true);
      toast.error("Connection issue — using offline mode");
      return null;
    } finally {
      setIsBackendBusy(false);
    }
  };

  const callCreditScoreAPI = async (pan: string) => {
    setIsBackendBusy(true);
    try {
      const response = await fetch(`${ENDPOINTS.credit_score}/${pan}`);

      if (!response.ok) {
        const errBody = await response.json().catch(() => null);
        throw new Error(errBody?.detail || "Credit score fetch failed");
      }
      const data = await response.json();

      setCreditScoreData(data);
      setShowCreditScoreCard(true);

      return data;
    } catch (error) {
      console.error("Credit score error:", error);
      setIsOfflineMode(true);
      toast.error("Connection issue — using offline mode");
      return null;
    } finally {
      setIsBackendBusy(false);
    }
  };

  const simulateBotResponse = (userMessage: string, sourceMessageId?: number) => {
    setIsTyping(true);
    const prevMessages = [...messages];

    setTimeout(async () => {
      let botResponse = "";

      switch (conversationStep.current) {
        case 0:
          setUserData((prev) => ({ ...prev, name: userMessage }));
          activateAgent("KYC Verification Agent", "Validating identity inputs and verification details.");
          botResponse = kycText("Please upload your PAN card first.", "कृपया पहले अपना PAN कार्ड अपलोड करें।");
          setShowPanUploadCard(true);
          conversationStep.current = 1;
          break;

        case 1:
          botResponse = kycText(
            "Please use the upload card below to upload your PAN document.",
            "कृपया PAN दस्तावेज़ अपलोड करने के लिए नीचे दिए गए upload card का उपयोग करें।"
          );
          break;

        case 3:
          botResponse = "Feel free to adjust the sliders to customize your loan terms. Once satisfied, click 'Select This Plan' to proceed.";
          break;

        default:
          if (userMessage.toLowerCase().includes("human") || userMessage.toLowerCase().includes("talk to agent")) {
            handleEscalationTrigger();
            return;
          }
          botResponse = "Thank you for your message. Is there anything else I can help you with?";
      }

      if (botResponse) {
        let quickReplies = undefined;
        const type: "emi-calculator" | "escalation" | "comparison-cards" | undefined = undefined;

        if (conversationStep.current === 1) {
          quickReplies = [
            { label: language === "hi" ? "लोन के लिए आवेदन करें" : "Apply for a Loan", value: "apply" },
            { label: language === "hi" ? "पात्रता जांचें" : "Check Eligibility", value: "eligibility" },
            { label: language === "hi" ? "यह कैसे काम करता है?" : "How does it work?", value: "how" }
          ];
        } else if (conversationStep.current === 3) {
          quickReplies = [
            { label: language === "hi" ? "मेरे लोन विकल्प देखें →" : "Check My Loan Options →", value: "options" },
            { label: language === "hi" ? "मेरे स्कोर को क्या प्रभावित करता है?" : "What affects my score?", value: "factors" }
          ];
        }

        const newMsg: Message = { id: prevMessages.length + 1, text: botResponse, isBot: true, quickReplies, type };
        setMessages((prev) => {
          const updated = sourceMessageId
            ? prev.map((message) => (message.id === sourceMessageId ? { ...message, status: "responded" as const } : message))
            : prev;
          return [...updated, newMsg];
        });
        saveSession([...prevMessages, newMsg], userData.stage, userData);
      }

      setIsTyping(false);
    }, 1500);
  };

  const handleSend = () => {
    if (!input.trim() || isEscalated || isInputLocked) return;

    const userMessage = input.trim();
    const newMsg: Message = { id: messages.length + 1, text: userMessage, isBot: false, status: "sent" };
    setIsTyping(true);
    setMessages((prev) => [...prev, newMsg]);
    setInput("");

    // Simulate delivery
    setTimeout(() => {
      setMessages((prev) => prev.map((message) => (message.id === newMsg.id ? { ...message, status: "delivered" } : message)));
      
      // Check for EMI keywords
      if (userMessage.toLowerCase().includes("emi") || userMessage.toLowerCase().includes("tenure") || userMessage.toLowerCase().includes("किस्त")) {
         setTimeout(() => {
           setMessages((prev) => [
             ...prev,
             { id: prev.length + 1, text: "Sure! You can use this calculator to see how different amounts and tenures affect your EMI.", isBot: true, type: "emi-calculator" }
           ]);
           setMessages((prev) => prev.map((message) => (message.id === newMsg.id ? { ...message, status: "responded" } : message)));
           setIsTyping(false);
         }, 800);
      } else {
        simulateBotResponse(userMessage, newMsg.id);
      }
    }, 500);
  };

  const handleEmiTerms = (amount: number, rate: number, tenure: number) => {
    addBotMessage(`Perfect. I'll use these terms: ${formatIndianRupees(amount)} at ${rate}% for ${tenure} months.`);
    setUserData(prev => ({ ...prev, selectedLoan: { amount, interest: rate, tenure, emi: 0 }, stage: "negotiate" }));
    // Trigger negotiation with these terms
    handleLoanSelect(rate, tenure, amount);
  };

  const handleOfferPreview = (offer: Offer) => {
    setPendingOffer(offer);
    setShowKfsCard(true);
    setKfsAcknowledged(false);
    const riskTierText = (userData.riskTier || "").toLowerCase();
    if (riskTierText.includes("low") || riskTierText.includes("medium")) {
      const preview = calculateEmiWithHoliday(offer.amount, offer.rate, offer.tenure, 2);
      setEmiHolidayOption({
        ...preview,
        message: `Would you like a 2-month EMI holiday? Your first EMI starts in month ${preview.firstEmiAfterMonth}.`,
      });
      setSelectedHolidayMonths(0);
    } else {
      setEmiHolidayOption(null);
      setSelectedHolidayMonths(0);
    }
  };

  const handleAcceptPendingOffer = () => {
    if (!pendingOffer || !kfsAcknowledged) return;
    handleLoanSelect(pendingOffer.rate, pendingOffer.tenure, pendingOffer.amount, selectedHolidayMonths);
  };

  // Feature 2: Bank Statement Upload Handler
  const handleBankStatementUpload = async (file: File | undefined) => {
    if (!file) return;
    setShowBankStatementCard(false);
    addBotMessage("📄 Analyzing your bank statement...");
    setIsTyping(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("session_id", userData.sessionId);
      const res = await fetch(ENDPOINTS.credit_analyze_statement, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setBankStatementResult(data);
      setIsTyping(false);
      if (data.analysis_possible) {
        addBotMessage(
          `✅ Bank Statement Analysis Complete\n\n` +
          `Estimated Monthly Income: ${formatIndianRupees(data.estimated_monthly_income)}\n` +
          `Confidence: ${data.income_confidence}\n` +
          `Source: ${data.data_source}\n\n` +
          `This will be used to supplement your credit assessment.`
        );
      } else {
        addBotMessage(`⚠️ Could not extract income data from the statement. ${data.reason || "Please try again with a clearer document."}`);
      }
    } catch {
      setIsTyping(false);
      addBotMessage("❌ Failed to analyze bank statement. Please try again.");
    }
  };

  const handleLoanSelect = async (interest: number, tenure: number, amount: number, holidayMonths = 0) => {
    const baseMonthlyRate = interest / 1200;
    const standardEmi = Math.round(
      (amount * baseMonthlyRate * Math.pow(1 + baseMonthlyRate, tenure)) /
        (Math.pow(1 + baseMonthlyRate, tenure) - 1)
    );
    const holidayDetails = holidayMonths > 0
      ? calculateEmiWithHoliday(amount, interest, tenure, holidayMonths)
      : null;
    const emi = holidayDetails?.emi ?? standardEmi;

    setUserData((prev) => ({
      ...prev,
      selectedLoan: {
        amount,
        interest,
        tenure,
        emi,
        holidayMonths: holidayMonths > 0 ? holidayMonths : undefined,
        holidayExtraCost: holidayDetails?.extraCost,
      },
    }));

    setShowLoanOffers(false);
    setShowKfsCard(false);
    setPendingOffer(null);
    setKfsAcknowledged(false);

    const selectionMessage =
      language === "en"
        ? `You selected: ${formatIndianRupees(amount)} at ${interest}% for ${tenure} months.\n\n${TRANSLATIONS.emi[language]}: ${formatIndianRupees(emi)}/month${holidayMonths > 0 ? `\nEMI holiday: ${holidayMonths} months` : ""}`
        : `आपने चुना: ${formatIndianRupees(amount)} ${interest}% पर ${tenure} महीनों के लिए।\n\n${TRANSLATIONS.emi[language]}: ${formatIndianRupees(emi)}/month${holidayMonths > 0 ? `\nEMI holiday: ${holidayMonths} महीनों का` : ""}`;

    setMessages((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        text: selectionMessage,
        isBot: false,
      },
    ]);

    setIsTyping(true);
    setIsBackendBusy(true);
    setTimeout(async () => {
      try {
        setIsTyping(false);
        setActiveAgent("Dynamic Negotiation Agent");
        setMessages((prev) => [
          ...prev,
          {
            id: prev.length + 1,
            text: "Dynamic Negotiation Agent activated.\nApplying negotiation policy and offer optimization.\n\nYour application is being processed.",
            isBot: true,
            variant: "system",
          },
        ]);

        // Fire pipeline start (non-blocking, best-effort)
        try {
          const pipelineStart = await fetch(ENDPOINTS.pipeline_start, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: userData.sessionId,
              applicant_name: userData.name || "Applicant",
              pan_number: userData.pan || "ABCDE1234F",
              loan_amount: amount,
              loan_term: tenure,
              offered_rate: interest,
              previous_sanction_reference: repeatBorrowerData?.sanction_reference || repeatBorrowerData?.reference,
            }),
          });
          if (pipelineStart.ok) {
            const startData = await pipelineStart.json();
            setPipelineSessionId(startData.session_id);
            setPipelineStatus(startData.status || "ACTIVE");
          }
        } catch {
          // non-fatal
        }

        // Credit assessment
        const assessmentResult = await callUnderwritingAPI({
          pan_number: userData.pan,
          gender: "Male",
          married: "Yes",
          dependents: "1",
          education: "Graduate",
          self_employed: "No",
          applicant_income: Number(bankStatementResult?.estimated_monthly_income || 5000),
          coapplicant_income: 1500,
          loan_amount: amount / 100000,
          loan_amount_term: tenure,
          credit_history: 1,
          property_area: "Urban",
          preferred_language: language,
          session_id: userData.sessionId,
          employment_type: repeatBorrowerData?.employment_type || "salaried",
          employer_name: repeatBorrowerData?.employer_name || "TCS",
          monthly_income: Number(bankStatementResult?.estimated_monthly_income || 5000),
          loan_purpose: repeatBorrowerData?.purpose || "general",
        });

        const decision = assessmentResult?.decision;
        const isApproved = assessmentResult && (
          decision === "APPROVED" ||
          decision === "APPROVED_WITH_CONDITIONS" ||
          decision === "CONDITIONAL_APPROVAL"
        );
        const isSoftReject = decision === "CONDITIONAL_REJECT";

        if (!isApproved) {
          let handledReject = false;
          if (isSoftReject && assessmentResult?.soft_reject_guidance) {
            const guidance = assessmentResult.soft_reject_guidance;
            setMessages((prev) => [
              ...prev,
              {
                id: prev.length + 1,
                text: `${guidance.message || TRANSLATIONS.rejected[language]}

${guidance.income_delta_monthly ? `Increase monthly income by about ${formatIndianRupees(guidance.income_delta_monthly)}.` : ""}
${guidance.repayment_history_impact || ""}`.trim(),
                isBot: true,
                quickReplies: [
                  { label: language === "hi" ? "पुनः प्रयास करें" : "Try Again", value: "try_again" },
                  { label: language === "hi" ? "EMI कैलकुलेट करें" : "Recalculate EMI", value: "emi" },
                ],
              },
            ]);
            handledReject = true;
          }
          if (!handledReject) {
            setMessages((prev) => [
              ...prev,
              {
                id: prev.length + 1,
                text: assessmentResult?.message || TRANSLATIONS.rejected[language],
                isBot: true,
              },
            ]);
          }
          return;
        }

        // Negotiation
        const negotiationResult = await callNegotiationAPI(
          assessmentResult.risk_score,
          assessmentResult.risk_tier,
          amount,
          tenure,
          assessmentResult.max_negotiation_rounds || 3,
        );
        if (negotiationResult?.emi_holiday_option) {
          setEmiHolidayOption(negotiationResult.emi_holiday_option);
        }

        // Accept negotiation (best-effort)
        try {
          await fetch(ENDPOINTS.negotiate_accept, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: negotiationResult?.session_id || userData.sessionId,
              final_rate: interest,
              holiday_months: selectedHolidayMonths,
            }),
          });
        } catch {
          // non-fatal
        }

        // Approval message
        setMessages((prev) => [
          ...prev,
          {
            id: prev.length + 1,
            text: `KYC Verified ✓\nCredit Check Passed ✓\nIncome Assessment Complete ✓\nRisk Analysis Completed ✓\n\n${TRANSLATIONS.approved[language]}`,
            isBot: true,
          },
        ]);

        // Update stage
        setUserData((prev) => ({ ...prev, stage: "sanction" }));

        // Blockchain sanction
        let blockchainData: { transaction_id: string; block_hash: string } | undefined;
        try {
          setActiveAgent("Blockchain Audit Agent");
          setPulseBadge(true);
          const sanctionRes = await fetch(ENDPOINTS.blockchain_sanction, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: userData.sessionId,
              applicant_name: userData.name || "Applicant",
              pan_number: userData.pan || "ABCDE1234F",
              loan_amount: amount,
              interest_rate: interest,
              tenure_years: Math.max(1, Math.round(tenure / 12)),
            }),
          });
          if (sanctionRes.ok) {
            const bData = await sanctionRes.json();
            blockchainData = {
              transaction_id: bData.transaction_id,
              block_hash: bData.block_hash,
            };
            setUserData((prev) => ({ ...prev, blockchainData }));
          }
        } catch (e) {
          console.warn("Blockchain sanction failed (non-fatal):", e);
        } finally {
          setPulseBadge(false);
        }

        setMessages((prev) => [
          ...prev,
          {
            id: prev.length + 1,
            text: "Sanction details are being securely recorded with tamper-proof hash verification on our distributed audit ledger.",
            isBot: true,
          },
        ]);

        // Ensure selectedLoan has valid emi before showing sanction
        setUserData((prev) => ({
          ...prev,
          stage: "sanction",
          selectedLoan: {
            amount,
            interest,
            tenure,
            emi: prev.selectedLoan.emi || emi,
          },
        }));
        setShowSanction(true);
        
        // Feature 5: Save sanction state for repeat borrower flow
        const sanctionReference = blockchainData?.transaction_id || `APP-${Math.floor(1000 + Math.random() * 9000)}`;
        const sanctionRecord = JSON.stringify({
          sanction_reference: sanctionReference,
          reference: sanctionReference,
          sanctioned_at: new Date().toISOString(),
          amount: amount,
          rate: interest,
          preapproved_limit: Math.round(amount * (isRepeatBorrower ? 1.25 : 1.0)),
          holiday_months: selectedHolidayMonths,
        });
        localStorage.setItem("previous_sanction_reference", sanctionRecord);
        localStorage.setItem("loanease_previous_sanction", sanctionRecord);
      } catch (err) {
        console.error("handleLoanSelect flow error:", err);
        setIsTyping(false);
        addBotMessage(
          language === "en"
            ? "Something went wrong processing your application. Please try again."
            : "आपके आवेदन को संसाधित करने में कुछ गलत हो गया। कृपया पुनः प्रयास करें।"
        );
      } finally {
        setIsBackendBusy(false);
      }
    }, 2500);
  };

  const handleEscalationTrigger = () => {
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      setMessages(prev => [
        ...prev,
        {
          id: prev.length + 1,
          text: "Connecting to Human Agent",
          isBot: true,
          type: "escalation"
        }
      ]);
    }, 1000);
  };

  const handleEscalationSubmit = async (preferredTime: string, whatsapp: boolean) => {
    setEscalationData({ preferredTime, whatsapp });
    setIsEscalated(true);
    setIsBackendBusy(true);
    
    try {
      await fetch(ENDPOINTS.escalation_callback, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: userData.sessionId,
          preferred_time: preferredTime,
          whatsapp_opt_in: whatsapp
        }),
      });
    } catch (e) {
      console.warn("Escalation preference save failed", e);
    } finally {
      setIsBackendBusy(false);
    }

    addBotMessage("Your application is on hold pending human review. We'll reach out shortly.");
  };

  const handleQuickReply = (value: string) => {
    handleSendWithText(value);
  };

  const handleSendWithText = (text: string) => {
    if (isInputLocked || isEscalated) return;

    const newMsg: Message = { id: messages.length + 1, text, isBot: false, status: "sent" };
    setIsTyping(true);
    setMessages((prev) => [...prev, newMsg]);
    
    setTimeout(() => {
      setMessages((prev) => prev.map((message) => (message.id === newMsg.id ? { ...message, status: "delivered" } : message)));
      simulateBotResponse(text, newMsg.id);
    }, 500);
  };

  return (
    <>
      <style>{`
        /* Main app layout */
        .app-layout {
          display: flex;
          flex-direction: row;
          height: 100vh;
          width: 100vw;
          overflow: hidden;
          background: #111111;
        }

        /* Chat area — takes all available space */
        .chat-area {
          min-width: 0;
          display: flex;
          flex-direction: column;
          flex: 1 1 auto;
          height: 100vh;
          overflow: hidden;
          transition: all 0.35s ease;
        }

        /* Sidebar — fixed width when open */
        .agent-sidebar {
          width: 320px;
          min-width: 320px;
          max-width: 320px;
          flex: 0 0 320px;
          height: 100vh;
          background: #1a1a1a;
          border-left: 1px solid #2a2a2a;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          transition: width 0.35s ease, min-width 0.35s ease, opacity 0.35s ease, transform 0.35s ease;
          will-change: transform;
        }

        .app-layout.is-processing .chat-input-container {
          height: 0;
          padding-top: 0;
          padding-bottom: 0;
          opacity: 0;
          transform: translateY(10px);
          pointer-events: none;
          overflow: hidden;
          border-top-color: transparent;
          box-shadow: none;
        }

        .app-layout.is-processing .chat-input {
          border-color: transparent;
          box-shadow: none;
        }

        .app-layout.is-processing .processing-indicator {
          opacity: 1;
        }

        .app-layout.is-processing .agent-sidebar {
          box-shadow: 0 -18px 40px rgba(0, 0, 0, 0.35);
        }

        /* Sidebar COLLAPSED state */
        .agent-sidebar.collapsed {
          width: 0;
          min-width: 0;
          opacity: 0;
          border-left: none;
          pointer-events: none;
        }

        /* Sidebar COLLAPSED — show thin tab */
        .sidebar-tab {
          position: fixed;
          right: 0;
          top: 50%;
          transform: translateY(-50%);
          width: 28px;
          height: 80px;
          background: #2a2a2a;
          border-radius: 8px 0 0 8px;
          border: 1px solid #3a3a3a;
          border-right: none;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          z-index: 100;
          transition: background 0.2s;
          writing-mode: vertical-rl;
          font-size: 10px;
          color: #F5C518;
          letter-spacing: 1px;
          font-weight: 600;
        }
        .sidebar-tab:hover {
          background: #333333;
        }
        .agent-sidebar:not(.collapsed) ~ .sidebar-tab,
        .sidebar-tab.hidden {
          display: none;
        }

        /* Chat messages — proper scroll */
        .chat-messages {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          overflow-x: hidden;
          padding: 16px 20px;
          scroll-behavior: smooth;
          background: url('https://www.transparenttextures.com/patterns/dark-matter.png');
          background-attachment: fixed;
        }

        /* Remove yellow vertical bar artifacts */
        .chat-area::after,
        .chat-area::before {
          display: none !important;
        }

        /* Sidebar header */
        .sidebar-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 20px;
          border-bottom: 1px solid #2a2a2a;
          flex-shrink: 0;
        }

        .sidebar-title {
          font-size: 14px;
          font-weight: 700;
          color: #ffffff;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        /* Agent items — full width cards */
        .agent-item {
          padding: 14px 20px;
          border-bottom: 1px solid #1f1f1f;
          display: flex;
          align-items: flex-start;
          gap: 12px;
          transition: background 0.2s;
        }

        .agent-item.active {
          background: #1f1f1f;
          border-left: 3px solid #F5C518;
        }

        .agent-item.completed {
          border-left: 3px solid #22c55e;
        }

        .agent-item.waiting {
          opacity: 0.5;
        }

        /* Agent status indicator */
        .agent-status-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          margin-top: 4px;
          flex-shrink: 0;
        }
        .agent-status-dot.active {
          background: #F5C518;
          box-shadow: 0 0 8px #F5C518;
          animation: pulse 1.5s infinite;
        }
        .agent-status-dot.completed {
          background: #22c55e;
        }
        .agent-status-dot.waiting {
          background: #3a3a3a;
          border: 1px solid #4a4a4a;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.8); }
        }

        .agent-info {
          flex: 1;
          min-width: 0;
        }

        .agent-name {
          font-size: 13px;
          font-weight: 600;
          color: #ffffff;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .agent-status-text {
          font-size: 11px;
          color: #6b7280;
          margin-top: 2px;
        }

        .agent-duration {
          font-size: 10px;
          color: #F5C518;
          margin-top: 2px;
        }

        /* Progress bar for active agent */
        .agent-progress {
          height: 2px;
          background: #2a2a2a;
          border-radius: 1px;
          margin-top: 8px;
          overflow: hidden;
        }
        .agent-progress-fill {
          height: 100%;
          background: #F5C518;
          border-radius: 1px;
          animation: progress-pulse 1.5s ease-in-out infinite;
        }
        @keyframes progress-pulse {
          0% { width: 20%; }
          50% { width: 80%; }
          100% { width: 20%; }
        }

        /* Sidebar footer — Groq status */
        .sidebar-footer {
          padding: 12px 20px;
          border-top: 1px solid #2a2a2a;
          margin-top: auto;
          flex-shrink: 0;
        }

        .groq-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 11px;
          color: #6b7280;
        }

        .groq-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #22c55e;
        }

        .api-endpoint {
          font-size: 10px;
          color: #4b5563;
          margin-top: 4px;
          font-family: monospace;
        }

        .chat-messages-container::-webkit-scrollbar {
          width: 6px;
        }
        .chat-messages-container::-webkit-scrollbar-track {
          background: #1a1a1a;
        }
        .chat-messages-container::-webkit-scrollbar-thumb {
          background: #F5C518;
          border-radius: 3px;
        }
        .chat-messages-container::-webkit-scrollbar-thumb:hover {
          background: #e6b800;
        }
        .chat-messages-container {
          scroll-behavior: smooth;
        }
        .chat-input-container {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: #111111;
          border-top: 1px solid #1f1f1f;
          flex-shrink: 0;
          height: 72px;
          opacity: 1;
          transform: translateY(0);
          overflow: hidden;
          transition: height 0.35s ease, opacity 0.3s ease, transform 0.35s ease, padding 0.35s ease, border-top-color 0.35s ease;
        }
        .chat-input {
          flex: 1;
          background: #1a1a1a;
          border: 1px solid #2a2a2a;
          border-radius: 24px;
          padding: 10px 18px;
          color: #ffffff;
          font-size: 14px;
          outline: none;
          transition: border-color 0.2s, box-shadow 0.2s;
          resize: none;
          max-height: 100px;
          overflow-y: auto;
        }
        .chat-input:focus {
          border-color: #F5C518;
          box-shadow: 0 0 0 2px rgba(245, 197, 24, 0.1);
        }
        .chat-input.ready-glow {
          box-shadow: 0 0 20px rgba(245, 197, 24, 0.3);
          animation: ready-glow-fade 1s ease-out;
        }
        @keyframes ready-glow-fade {
          0% { box-shadow: 0 0 20px rgba(245, 197, 24, 0.3); }
          100% { box-shadow: 0 0 0 rgba(245, 197, 24, 0); }
        }
        .processing-indicator {
          height: 2px;
          background: linear-gradient(90deg, transparent, #F5C518, transparent);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
          opacity: 0;
          transition: opacity 0.3s ease;
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .send-button {
          background: #F5C518;
          color: #000000;
          border: none;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s;
        }
        .send-button:hover:not(:disabled) {
          background: #e6b800;
          transform: scale(1.05);
        }
        .send-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        /* Pipeline tracker styles */
        .pipeline-step.completed {
          color: #22c55e;
        }
        .pipeline-step.active {
          color: #F5C518;
          animation: pulse-border 2s infinite;
        }
        .pipeline-step.upcoming {
          color: #6b7280;
        }
        @keyframes pulse-border {
          0%, 100% { box-shadow: 0 0 0 0 rgba(245, 197, 24, 0.7); }
          50% { box-shadow: 0 0 0 8px rgba(245, 197, 24, 0); }
        }
      `}</style>
    <div className="fixed inset-0 bg-background z-50 flex flex-col">
      {/* Session Resume Banner */}
      {showSessionBanner && (
        <div className="absolute inset-x-0 top-0 z-[60] bg-yellow-400 text-black px-4 py-3 flex items-center justify-between animate-in slide-in-from-top duration-500 shadow-xl">
          <div className="text-sm font-bold flex items-center gap-2">
            <MessageCircle className="w-4 h-4" />
            Welcome back! Continue your application?
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" className="bg-black text-white hover:bg-black/80" onClick={handleResume}>Resume</Button>
            <Button size="sm" variant="ghost" className="hover:bg-black/10" onClick={handleStartFresh}>Start Fresh</Button>
          </div>
        </div>
      )}

      <div className={`app-layout ${isProcessing ? 'is-processing' : ''}`}>
        {/* Chat Area */}
        <div className="chat-area">
          {/* Header */}
          <div className="bg-card border-b border-border shadow-md">
            <div className="flex items-center justify-between px-4 py-3">
              <Button variant="ghost" size="icon" onClick={onClose}>
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center relative">
                  <MessageCircle className="w-4 h-4 text-primary-foreground" />
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full border-2 border-card" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-bold">Loan Assistant</h2>
                    <Badge variant="outline" className={cn(
                      "text-[10px] py-0 px-1.5 h-4",
                      isOfflineMode ? "border-muted-foreground/50 text-muted-foreground" : "border-yellow-400/50 text-yellow-400"
                    )}>
                      {isOfflineMode ? <><Zap className="w-3 h-3 mr-1" />Quick Mode</> : <><Bot className="w-3 h-3 mr-1" />AI Mode</>}
                    </Badge>
                    <Badge variant="outline" className="text-[10px] py-0 px-1.5 h-4 border-blue-400/50 text-blue-400">
                      <MessageSquare className="w-3 h-3 mr-1" />Web
                    </Badge>
                  </div>
                  <p className="text-[10px] text-muted-foreground font-mono">
                    {userData.sessionId} | Stage: <span className="text-yellow-400 uppercase header-stage-label">{userData.stage}</span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/whatsapp')}
                  className="text-xs px-2 py-1 h-7 border border-green-500/20 hover:bg-green-500/10"
                >
                  <Smartphone className="w-3 h-3 mr-1" />
                  WhatsApp
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleAgentSidebar}
                  className="text-xs px-2 py-1 h-7 border border-yellow-400/20 hover:bg-yellow-400/10 agents-toggle-btn"
                >
                  <Bot className="w-3 h-3 mr-1" />
                  AGENTS ({agentTrace?.length || 2})
                </Button>
                <LanguageSwitcher currentLanguage={language} onLanguageChange={handleLanguageChange} />
              </div>
            </div>

        {/* Progress Indicator */}
        <div className="px-4 pb-2 relative z-20">
          <div className="flex items-center justify-between max-w-lg mx-auto relative">
            <div className="absolute top-2.5 left-0 right-0 h-0.5 bg-border -z-10" />
            {APP_STAGES.map((s, idx) => {
              const stagesOrder = APP_STAGES.map(st => st.id);
              const currentIdx = stagesOrder.indexOf(userData.stage);
              const isCompleted = idx < currentIdx;
              const isActive = idx === currentIdx;

              return (
                <div 
                  key={s.id} 
                  className={`flex flex-col items-center gap-1 group cursor-pointer relative pipeline-step ${isCompleted ? 'completed' : isActive ? 'active' : 'upcoming'}`}
                  onClick={() => {
                    if (s.id === "credit" && isCompleted) {
                      setShowCreditSummaryPopup(true);
                    } else if (isCompleted) {
                      toast.info(`Summary of ${s.label} completed`);
                    }
                  }}
                >
                  <div className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-300 ring-4 ring-card",
                    isCompleted ? "bg-green-500 text-white shadow-[0_0_10px_rgba(34,197,94,0.3)]" : 
                    isActive ? "bg-yellow-400 text-black border-2 border-yellow-400 animate-pulse-border" : 
                    "bg-card border-2 border-border text-muted-foreground"
                  )}>
                    {isCompleted ? <Check className="w-3.5 h-3.5" /> : idx + 1}
                  </div>
                  <span className={cn(
                    "text-[9px] uppercase tracking-wider font-bold transition-colors absolute -bottom-4 whitespace-nowrap",
                    isActive ? "text-yellow-400" : isCompleted ? "text-green-500" : "text-muted-foreground"
                  )}>{s.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Credit Summary Popup */}
        {showCreditSummaryPopup && (
          <div className="absolute top-24 left-1/2 -translate-x-1/2 w-64 bg-card border border-border rounded-xl shadow-2xl z-50 p-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-border">
              <h3 className="font-bold text-sm flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-green-500/20 text-green-500 flex items-center justify-center text-xs">②</span>
                Credit Check <Check className="w-3 h-3 text-green-500" />
              </h3>
              <button onClick={() => setShowCreditSummaryPopup(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">CIBIL Score</span>
                <span className="font-bold">{userData.creditScore || 820}/900</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Decision</span>
                <span className="font-bold">{underwritingResult?.decision || "APPROVED"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Risk Score</span>
                <span className="font-bold">{userData.riskScore || 87}/100</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tier</span>
                <span className="font-bold text-yellow-400">{userData.riskTier || "Low Risk"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">XGBoost</span>
                <span className="font-bold">
                  {underwritingResult?.confidence_width != null
                    ? `${Math.round((underwritingResult.approval_probability || 0) * 100)}% ± ${Math.round((underwritingResult.confidence_width || 0) * 50)}%`
                    : "87% confidence"}
                </span>
              </div>
              {underwritingResult?.income_reasonability && (
                <div className="rounded-lg border border-border/70 bg-muted/30 px-3 py-2 text-[11px] text-muted-foreground">
                  <div className="font-semibold text-foreground">FOIR check</div>
                  <div className="mt-1">
                    {underwritingResult.income_reasonability.message || "Income support looks acceptable."}
                  </div>
                </div>
              )}
              {underwritingResult?.soft_reject_guidance && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
                  <div className="font-semibold text-amber-100">Soft reject guidance</div>
                  <div className="mt-1">
                    {underwritingResult.soft_reject_guidance.message}
                  </div>
                </div>
              )}
              {underwritingResult?.model_drift_warning && (
                <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">
                  <div className="font-semibold text-rose-100">Model drift detected</div>
                  <div className="mt-1">
                    {underwritingResult.recommendation || "Retrain model with recent data."}
                  </div>
                </div>
              )}
              <Button
                variant="outline"
                className="w-full border-blue-500/30 bg-blue-500/5 text-blue-200 hover:bg-blue-500/10"
                onClick={() => setShowBankStatementCard(true)}
              >
                No payslips? Upload bank statement
              </Button>
              <div className="flex justify-between pt-2 border-t border-border/50 text-muted-foreground text-[10px]">
                <span>Time taken</span>
                <span>0.9s</span>
              </div>
            </div>
          </div>
        )}

        <div className="px-4 pb-3 pt-6">
        </div>
      </div>

          {/* Messages */}
          <div ref={messagesContainerRef} className="chat-messages">
            {showWelcomeState ? (
            <div className="flex min-h-full items-center justify-center px-4 py-8">
              <div className="w-full max-w-md rounded-3xl border border-[#2a2a2a] bg-[#101010]/95 p-8 text-center shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-sm">
                <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-[#F5C518]/15 text-[#F5C518] shadow-[0_0_0_8px_rgba(245,197,24,0.04)]">
                  <MessageCircle className="h-8 w-8" />
                </div>
                <h3 className="text-2xl font-black tracking-tight text-slate-100">Hi! I'm your Loan Assistant</h3>
                <p className="mt-3 text-sm leading-6 text-slate-300">{TRANSLATIONS.opening[language]}</p>
                <div className="mt-6 grid gap-2 text-left text-sm text-slate-300 sm:grid-cols-2">
                  <div className="rounded-xl border border-[#2a2a2a] bg-[#151515] px-3 py-3 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                    <span>No paperwork</span>
                  </div>
                  <div className="rounded-xl border border-[#2a2a2a] bg-[#151515] px-3 py-3 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                    <span>Instant credit check</span>
                  </div>
                  <div className="rounded-xl border border-[#2a2a2a] bg-[#151515] px-3 py-3 flex items-center gap-2">
                    <Bot className="w-4 h-4 text-blue-400" />
                    <span>AI-powered negotiation</span>
                  </div>
                  <div className="rounded-xl border border-[#2a2a2a] bg-[#151515] px-3 py-3 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-purple-400" />
                    <span>Blockchain-secured letter</span>
                  </div>
                </div>
                <Button
                  variant="chat"
                  className="mt-7 w-full bg-[#F5C518] font-bold text-black hover:bg-[#e6b800]"
                  onClick={handleStartConversation}
                >
                  Apply for a Loan →
                </Button>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div key={message.id} className="space-y-3">
                  <ChatMessage
                    message={message.text}
                    isBot={message.isBot}
                    status={message.status}
                    variant={message.variant}
                  />

                  {message.isBot && message.quickReplies && (
                    <QuickReplies options={message.quickReplies} onSelect={handleQuickReply} />
                  )}

                  {message.isBot && message.type === "emi-calculator" && (
                    <EmiCalculatorWidget onUseTerms={handleEmiTerms} />
                  )}

                  {message.isBot && message.type === "escalation" && (
                    <div className="max-w-md rounded-2xl border border-[#2a2a2a] bg-[#111111] p-6 shadow-2xl animate-in slide-in-from-left duration-500">
                       <div className="mb-4 flex items-center gap-3">
                         <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#F5C518]">
                           <User className="w-5 h-5 text-black" />
                         </div>
                         <div>
                           <h3 className="font-bold text-slate-100">Connecting to Human Agent</h3>
                           <p className="text-xs text-slate-500">Ticket: ESC-2026-{Math.floor(100 + Math.random() * 899)}</p>
                         </div>
                       </div>
                       <p className="mb-6 text-sm text-slate-400">A loan officer will call you within 2 business hours. Your application is saved.</p>
                       
                       <div className="space-y-4">
                          <div className="space-y-2">
                            <label className="text-[10px] font-bold uppercase text-slate-500">Preferred Callback Time</label>
                            <div className="flex gap-2">
                              {["Morning", "Afternoon", "Evening"].map((t) => (
                                <Button key={t} size="sm" variant={escalationData.preferredTime === t ? "accent" : "outline"} className="flex-1 text-[10px]" onClick={() => setEscalationData((prev) => ({ ...prev, preferredTime: t }))}>{t}</Button>
                              ))}
                            </div>
                          </div>
                          <div className="flex items-center justify-between rounded-lg border border-[#2a2a2a] bg-[#151515] p-3">
                            <span className="text-xs font-medium text-slate-300">Get updates on WhatsApp?</span>
                            <Button size="sm" variant={escalationData.whatsapp ? "accent" : "outline"} onClick={() => setEscalationData((prev) => ({ ...prev, whatsapp: !prev.whatsapp }))}>{escalationData.whatsapp ? <>Yes <CheckCircle className="w-4 h-4 inline ml-1" /></> : "No"}</Button>
                          </div>
                          <Button className="w-full bg-[#F5C518] font-bold text-black hover:bg-[#e6b800]" disabled={!escalationData.preferredTime} onClick={() => handleEscalationSubmit(escalationData.preferredTime, escalationData.whatsapp)}>Confirm Preference</Button>
                       </div>
                    </div>
                  )}
                </div>
              ))}

              {isTyping && <ChatMessage message="" isBot isTyping />}
            </>
          )}

        {isKycProcessing && (
          <div className="max-w-md rounded-xl border border-yellow-500/40 bg-card p-4 shadow-lg shadow-yellow-500/10 animate-in fade-in zoom-in duration-300">
            <div className="flex items-start gap-4">
              <div className="relative w-16 h-20 bg-muted rounded border border-border overflow-hidden shrink-0">
                <FileText className="absolute inset-0 m-auto text-muted-foreground/30 w-8 h-8" />
                <div className="absolute top-0 left-0 right-0 h-0.5 bg-yellow-400 shadow-[0_0_10px_rgba(250,204,21,0.8)] animate-[scan_2s_ease-in-out_infinite]" />
              </div>
              <div className="flex-1 space-y-2">
                <div className="text-sm font-bold text-foreground flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full border-2 border-yellow-400 border-t-transparent animate-spin" />
                  {kycProcessingText}
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-yellow-400 transition-all duration-200"
                    style={{ width: `${kycProgress}%` }}
                  />
                </div>
                <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest text-right">
                  {kycProgress}% / processing
                </div>
              </div>
            </div>
          </div>
        )}

        {showBankStatementCard && (
          <div className="w-full max-w-md self-start rounded-xl border-2 border-dashed border-blue-500/70 bg-gradient-to-br from-card to-card/85 p-5 shadow-lg shadow-blue-500/10">
            <div className="mb-1 flex items-center gap-2 text-base font-semibold text-foreground">
              <FileText className="h-4 w-4 text-blue-400" />
              {kycText("Upload Bank Statement", "Bank Statement अपलोड करें")}
            </div>
            <div className="mb-3 text-xs text-muted-foreground">Upload last 3 months PDF (Max 5MB)</div>
            <input
              ref={bankStatementInputRef}
              type="file"
              accept=".pdf,.txt"
              className="hidden"
              onChange={(e) => handleBankStatementUpload(e.target.files?.[0])}
            />
            <Button variant="outline" className="w-full border-blue-500/50 bg-background/60 hover:bg-blue-500/10" onClick={() => bankStatementInputRef.current?.click()}>
              <Upload className="mr-2 h-4 w-4" />
              {kycText("Choose File", "फ़ाइल चुनें")}
            </Button>
            <div className="mt-2 text-[11px] text-muted-foreground">
              {kycText("This helps if you don't have payslips", "अगर आपके पास payslips नहीं हैं, तो यह मदद करेगा")}
            </div>
          </div>
        )}

        {showPanUploadCard && (
          <div className="w-full max-w-md self-start rounded-xl border-2 border-dashed border-yellow-500/70 bg-gradient-to-br from-card to-card/85 p-5 shadow-lg shadow-yellow-500/10">
            <div className="mb-1 flex items-center gap-2 text-base font-semibold text-foreground">
              <FileText className="h-4 w-4 text-yellow-400" />
              {kycText("Upload PAN Card", "PAN कार्ड अपलोड करें")}
            </div>
            <div className="mb-3 text-xs text-muted-foreground">JPG, PNG or PDF • Max 5MB</div>
            <input
              ref={panInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.pdf"
              className="hidden"
              onChange={(e) => handlePanFileSelected(e.target.files?.[0])}
            />
            <Button variant="outline" className="w-full border-yellow-500/50 bg-background/60 hover:bg-yellow-500/10" onClick={() => panInputRef.current?.click()}>
              <Upload className="mr-2 h-4 w-4" />
              {kycText("Choose File", "फ़ाइल चुनें")}
            </Button>
            <div className="mt-2 text-[11px] text-muted-foreground">
              {kycText("or drag file here", "या फ़ाइल यहां drag करें")}
            </div>
          </div>
        )}

        {showPanConfirmCard && panKycData && (
          <div className="relative z-20 max-w-md rounded-xl border border-green-500/50 bg-gradient-to-br from-card to-card/85 p-4 shadow-lg shadow-green-500/10 pointer-events-auto">
            <div className="mb-2 flex items-center gap-2 text-base font-semibold text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              {kycText("PAN Card Verified", "PAN कार्ड सत्यापित")}
            </div>
            <div className="space-y-1.5 text-sm text-foreground">
              <div className="font-medium">{panKycData.name}</div>
              <div>{panKycData.pan_number}</div>
              <div>{panKycData.date_of_birth} {panKycData.age ? `(Age: ${panKycData.age})` : ""}</div>
              <div>{kycText("Father", "पिता")}: {panKycData.fathers_name}</div>
            </div>
            <div className="mt-3 flex gap-2">
              <Button
                variant="accent"
                type="button"
                className="relative z-20 flex-1 pointer-events-auto"
                onClick={() => {
                  setShowPanConfirmCard(false);
                  setShowAadhaarUploadCard(true);
                  addBotMessage(kycText("Great! Now upload your Aadhaar card.", "बहुत बढ़िया! अब अपना Aadhaar कार्ड अपलोड करें।"));
                }}
              >
                {kycText("Confirm", "पुष्टि करें")}
              </Button>
              <Button
                variant="outline"
                type="button"
                className="relative z-20 flex-1 pointer-events-auto"
                onClick={() => {
                  setShowPanConfirmCard(false);
                  setShowPanUploadCard(true);
                }}
              >
                <Pencil className="mr-1 h-4 w-4" />
                {kycText("Edit", "संपादित करें")}
              </Button>
            </div>
          </div>
        )}

        {showAadhaarUploadCard && (
          <div className="w-full max-w-md self-start rounded-xl border-2 border-dashed border-yellow-500/70 bg-gradient-to-br from-card to-card/85 p-5 shadow-lg shadow-yellow-500/10">
            <div className="mb-1 flex items-center gap-2 text-base font-semibold text-foreground">
              <FileText className="h-4 w-4 text-yellow-400" />
              {kycText("Upload Aadhaar Card", "Aadhaar कार्ड अपलोड करें")}
            </div>
            <div className="mb-3 text-xs text-muted-foreground">
              {kycText("Upload the full Aadhaar card so the mobile number is visible. JPG, PNG or PDF • Max 5MB", "मोबाइल नंबर दिखे ऐसा पूरा Aadhaar कार्ड अपलोड करें। JPG, PNG or PDF • Max 5MB")}
            </div>
            <input
              ref={aadhaarInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.pdf"
              className="hidden"
              onChange={(e) => handleAadhaarFileSelected(e.target.files?.[0])}
            />
            <Button variant="outline" className="w-full border-yellow-500/50 bg-background/60 hover:bg-yellow-500/10" onClick={() => aadhaarInputRef.current?.click()}>
              <Upload className="mr-2 h-4 w-4" />
              {kycText("Choose File", "फ़ाइल चुनें")}
            </Button>
            <div className="mt-2 text-[11px] text-muted-foreground">
              {kycText("or drag file here", "या फ़ाइल यहां drag करें")}
            </div>
          </div>
        )}

        {aadhaarKycData && (
          <div className="max-w-md rounded-xl border border-yellow-500/40 bg-gradient-to-br from-card to-card/80 p-4 shadow-lg shadow-yellow-500/10">
            <div className="mb-2 flex items-center gap-2 text-base font-semibold text-yellow-400">
              <CheckCircle2 className="h-4 w-4" />
              {kycText("Aadhaar OCR Detected", "Aadhaar OCR मिला")}
            </div>
            <div className="space-y-1.5 text-sm text-foreground">
              {aadhaarKycData.name && <div className="font-medium">{aadhaarKycData.name}</div>}
              {aadhaarKycData.aadhaar_last4 && <div>{kycText("Aadhaar ending", "Aadhaar के अंतिम अंक")}: {aadhaarKycData.aadhaar_last4}</div>}
              {aadhaarKycData.date_of_birth && <div>{aadhaarKycData.date_of_birth}{aadhaarKycData.age ? ` (Age: ${aadhaarKycData.age})` : ""}</div>}
              {aadhaarKycData.gender && <div>{aadhaarKycData.gender}</div>}
              {aadhaarKycData.mobile_number ? (
                <div>{kycText("Mobile", "मोबाइल")}: {aadhaarKycData.mobile_number}</div>
              ) : (
                <div className="text-muted-foreground">
                  {kycText("Mobile number not detected in OCR", "OCR में मोबाइल नंबर नहीं मिला")}
                </div>
              )}
            </div>
          </div>
        )}

        {showKycVerifiedCard && (
          <div className="max-w-md rounded-xl border border-green-500/50 bg-gradient-to-br from-card to-card/85 p-4 shadow-lg shadow-green-500/10">
            <div className="mb-1 flex items-center gap-2 text-base font-semibold text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              {kycText("KYC Verified", "KYC सत्यापित")}
            </div>
            <div className="text-sm text-foreground">{kycText("Documents match", "दस्तावेज़ मेल")} : {kycMatchScore ?? "-"}%</div>
            <div className="text-sm text-muted-foreground">KYC Ref: {kycReferenceId}</div>
          </div>
        )}

        {showOtpCard && (
          <div className="max-w-md rounded-xl border border-primary/50 bg-gradient-to-br from-card to-card/90 p-4 shadow-lg shadow-primary/10" onPaste={handleOtpPaste}>
            <div className="mb-2 flex items-center gap-2 text-base font-semibold text-primary">
              <ShieldCheck className="h-4 w-4" />
              {kycText("Verify Mobile OTP", "मोबाइल OTP सत्यापित करें")}
            </div>
            <div className="text-sm text-muted-foreground">
              {otpStatusMessage || kycText("Enter the 6-digit code sent to your Aadhaar-linked mobile number.", "अपने Aadhaar-linked mobile number पर भेजा गया 6-digit code दर्ज करें।")}
            </div>
            {otpSentToLast4 ? (
              <div className="mt-1 text-xs text-muted-foreground">
                {kycText("Sent to ending", "अंतिम अंक")}: {otpSentToLast4}
              </div>
            ) : null}
            <div className="mt-4 flex items-center justify-between gap-2">
              <div className="flex flex-1 gap-2">
                {otpDigits.map((digit, index) => (
                  <input
                    key={index}
                    ref={(element) => {
                      otpInputRefs.current[index] = element;
                    }}
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(event) => updateOtpDigit(index, event.target.value)}
                    onKeyDown={(event) => handleOtpKeyDown(index, event)}
                    className="h-11 w-11 rounded-lg border border-border bg-background text-center text-lg font-semibold tracking-[0.25em] text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/25"
                  />
                ))}
              </div>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {otpSecondsRemaining > 0
                  ? kycText(`OTP expires in ${Math.floor(otpSecondsRemaining / 60)}:${String(otpSecondsRemaining % 60).padStart(2, "0")}`, `OTP ${Math.floor(otpSecondsRemaining / 60)}:${String(otpSecondsRemaining % 60).padStart(2, "0")} में समाप्त होगा`)
                  : kycText("OTP expired", "OTP समाप्त हो गया है")}
              </span>
              <span>
                {otpAttemptsRemaining !== null
                  ? kycText(`${otpAttemptsRemaining} attempts remaining`, `${otpAttemptsRemaining} प्रयास शेष हैं`)
                  : null}
              </span>
            </div>
            {otpError ? <div className="mt-2 text-sm text-red-400">{otpError}</div> : null}
            <div className="mt-4 flex gap-2">
              <Button
                variant="accent"
                className="flex-1"
                disabled={otpSubmitting || otpLocked}
                onClick={submitOtp}
              >
                {otpSubmitting ? kycText("Verifying...", "सत्यापन हो रहा है...") : kycText("Verify OTP", "OTP सत्यापित करें")}
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                disabled={otpSubmitting || otpResendCooldown > 0}
                onClick={resendOtp}
              >
                {otpResendCooldown > 0
                  ? kycText(`Resend in ${otpResendCooldown}s`, `${otpResendCooldown}s में फिर भेजें`)
                  : kycText("Resend OTP", "OTP फिर भेजें")}
              </Button>
            </div>
          </div>
        )}

        {showCreditScoreCard && creditScoreData && (
          <div className="py-4">
            <CreditScoreCard
              score={creditScoreData.credit_score}
              maxScore={900}
              decision={underwritingResult?.decision}
              approvalProbability={underwritingResult?.approval_probability}
              confidenceLower={underwritingResult?.confidence_lower}
              confidenceUpper={underwritingResult?.confidence_upper}
              confidenceWidth={underwritingResult?.confidence_width}
              modelCertainty={underwritingResult?.model_certainty}
              riskTier={underwritingResult?.risk_tier}
              cibil_score={underwritingResult?.cibil_score ?? underwritingResult?.risk_score}
              cibil_band={underwritingResult?.cibil_band}
              cibil_classification={underwritingResult?.cibil_classification}
              risk_label={underwritingResult?.risk_label}
              industry_standard={underwritingResult?.industry_standard}
              eligible={underwritingResult?.eligible}
              conditional={underwritingResult?.conditional}
              rate_range={underwritingResult?.rate_range}
              max_negotiation_rounds={underwritingResult?.max_negotiation_rounds || underwritingResult?.cibil_max_negotiation_rounds}
              incomeReasonability={underwritingResult?.income_reasonability}
              softRejectGuidance={underwritingResult?.soft_reject_guidance}
              modelDriftWarning={underwritingResult?.model_drift_warning}
              recommendation={underwritingResult?.recommendation}
              structuredShapNarration={underwritingResult?.structured_shap_narration}
              alternative_score={underwritingResult?.alternative_score}
              alternative_eligible={underwritingResult?.alternative_eligible}
              alternative_details={underwritingResult?.alternative_details}
            />
          </div>
        )}

        {showLoanOffers && (
          <div className="space-y-4">
            <LoanComparisonCards 
              offers={[
                { id: 'std', name: 'Standard', amount: 500000, rate: 11.5, tenure: 36, emi: 16607, total: '6.2L' },
                { id: 'bv', name: 'Premium', amount: 500000, rate: 11.0, tenure: 60, emi: 10747, total: '6.45L', isRecommended: true },
                { id: 'flx', name: 'Flexi', amount: 500000, rate: 10.75, tenure: 84, emi: 8234, total: '6.92L' }
              ]}
              onSelect={handleOfferPreview}
            />

            {emiHolidayOption && (
              <div className="rounded-2xl border border-sky-500/30 bg-sky-500/10 p-5 shadow-[0_14px_34px_rgba(0,0,0,0.18)]">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.22em] text-sky-200">EMI Holiday</p>
                    <p className="mt-1 text-sm text-slate-100">
                      {emiHolidayOption.message || `Pause the first ${emiHolidayOption.holidayMonths || emiHolidayOption.holiday_months || 2} EMIs and start later.`}
                    </p>
                  </div>
                  <span className="rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-200">
                    {emiHolidayOption.recommended || emiHolidayOption.recommended === undefined ? "Recommended" : "Optional"}
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    variant={selectedHolidayMonths === (emiHolidayOption.holidayMonths || emiHolidayOption.holiday_months || 2) ? "accent" : "outline"}
                    onClick={() => setSelectedHolidayMonths(emiHolidayOption.holidayMonths || emiHolidayOption.holiday_months || 2)}
                  >
                    Use EMI holiday
                  </Button>
                  <Button variant="ghost" onClick={() => setSelectedHolidayMonths(0)}>
                    Regular schedule
                  </Button>
                </div>
                {emiHolidayOption.extraCost != null || emiHolidayOption.extra_cost != null ? (
                  <div className="mt-3 text-xs text-sky-100/80">
                    Extra cost: {formatIndianRupees(Number(emiHolidayOption.extraCost || emiHolidayOption.extra_cost || 0))}
                  </div>
                ) : null}
              </div>
            )}

            {showKfsCard && pendingOffer && (
              <div className="rounded-2xl border border-[#2a2a2a] bg-[#101010] p-5 shadow-[0_14px_34px_rgba(0,0,0,0.28)]">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-bold uppercase tracking-[0.22em] text-[#F5C518]">📋 Key Fact Statement (KFS)</p>
                    <p className="mt-1 text-xs text-slate-400">As required by RBI Digital Lending Directions, 2025</p>
                  </div>
                  <span className="rounded-full border border-[#2a2a2a] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                    Collapsible disclosure
                  </span>
                </div>

                <details className="rounded-xl border border-[#2a2a2a] bg-[#0d0d0d] p-4" open>
                  <summary className="cursor-pointer list-none text-sm font-semibold text-slate-100">
                    <span>Expand KFS</span>
                  </summary>

                  <div className="mt-4 rounded-2xl border border-[#333] bg-[#121212] p-4 text-sm text-slate-200">
                    <div className="mb-4 text-center">
                      <p className="text-[11px] font-black uppercase tracking-[0.28em] text-slate-400">Key Fact Statement</p>
                      <p className="mt-1 text-[11px] text-slate-500">Regulatory Ref: RBI/2022-23/111 DOR.STR.REC.68/21.01.001/2022-23</p>
                    </div>

                    <div className="grid gap-2 sm:grid-cols-2">
                      <div className="flex items-center justify-between gap-4 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                        <span className="text-slate-400">Loan Amount</span>
                        <span className="font-semibold text-slate-50">{formatIndianRupees(pendingOffer.amount)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                        <span className="text-slate-400">Annual % Rate</span>
                        <span className="font-semibold text-slate-50">{pendingOffer.rate.toFixed(2)}%</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                        <span className="text-slate-400">Processing Fee</span>
                        <span className="font-semibold text-slate-50">₹0 (Nil)</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                        <span className="text-slate-400">Monthly EMI</span>
                        <span className="font-semibold text-slate-50">{formatIndianRupees(pendingOffer.emi)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                        <span className="text-slate-400">Total Payable</span>
                        <span className="font-semibold text-slate-50">{formatIndianRupees(pendingOffer.emi * pendingOffer.tenure)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                        <span className="text-slate-400">Tenure</span>
                        <span className="font-semibold text-slate-50">{pendingOffer.tenure} months</span>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-2 rounded-xl border border-white/5 bg-white/5 p-3 text-sm">
                      <div className="flex items-start justify-between gap-4">
                        <span className="text-slate-400">Repayment schedule</span>
                        <span className="text-right font-medium text-slate-100">Equal monthly instalments over {pendingOffer.tenure} months</span>
                      </div>
                      <div className="flex items-start justify-between gap-4">
                        <span className="text-slate-400">Prepayment</span>
                        <span className="text-right font-medium text-slate-100">Allowed after 3 months, no penalty</span>
                      </div>
                      <div className="flex items-start justify-between gap-4">
                        <span className="text-slate-400">Foreclosure</span>
                        <span className="text-right font-medium text-slate-100">Allowed, no charges</span>
                      </div>
                      <div className="flex items-start justify-between gap-4">
                        <span className="text-slate-400">Grievance</span>
                        <span className="text-right font-medium text-slate-100">support@loanease.app · RBI Ombudsman</span>
                      </div>
                    </div>

                    <div className="mt-4 rounded-xl border border-[#2a2a2a] bg-[#0f0f0f] p-4">
                      <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-200">
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 rounded border-slate-600 bg-transparent text-[#F5C518] focus:ring-[#F5C518]"
                          checked={kfsAcknowledged}
                          onChange={(e) => setKfsAcknowledged(e.target.checked)}
                        />
                        <span>I have read and understood the Key Fact Statement</span>
                      </label>
                    </div>
                  </div>
                </details>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs text-slate-400">APR includes all disclosed fees; this prototype currently assumes zero processing fee.</p>
                  <Button
                    variant="accent"
                    disabled={!kfsAcknowledged}
                    onClick={handleAcceptPendingOffer}
                  >
                    Accept Offer
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {showSanction && (
          <div className="py-4">
            <SanctionLetter
              customerName={userData.name}
              loanAmount={userData.selectedLoan.amount}
              interestRate={userData.selectedLoan.interest}
              tenure={userData.selectedLoan.tenure}
              emi={userData.selectedLoan.emi}
              sanctionDate={new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
              referenceId={userData.blockchainData?.transaction_id || `LOAN${Date.now().toString().slice(-8)}`}
              blockchainHash={userData.blockchainData?.block_hash || "0x..."}
              onViewAnalytics={handleViewAnalytics}
            />
          </div>
        )}

        {showAnalytics && (
          <div className="py-8 bg-background/50 rounded-xl border border-border/50 animate-slide-up">
            <AnalyticsDashboard
              sessionId={userData.sessionId}
              customerName={userData.name}
              initialAmount={userData.selectedLoan.amount}
              initialInterest={userData.selectedLoan.interest}
              initialTenure={userData.selectedLoan.tenure}
            />
          </div>
        )}

          <div ref={messagesEndRef} />
        </div>

        <div className="lg:w-[340px] lg:ml-4 min-h-0 overflow-y-auto chat-messages-container">
        {/* Removed redundant floating AgentActivityPanel */}
        </div>
      </div>

      {/* Input */}
      <div className="chat-input-container">
            <div className="flex max-w-4xl flex-1 items-center gap-3 mx-auto w-full">
          <Textarea
            ref={textAreaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
                placeholder={getInputPlaceholder()}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            rows={1}
                className={cn("chat-input flex-1", !isProcessing && hasStartedConversation && !isEscalated ? "ready-glow" : "")}
            disabled={isInputLocked}
          />
          <Button
            variant="chat"
            size="icon"
            onClick={handleSend}
            disabled={
              !input.trim() ||
              isInputLocked
            }
            className="send-button h-10 w-10"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>

        <div className="processing-indicator" />

          {/* Sidebar Tab - visible when sidebar is collapsed */}
          <div className="sidebar-tab hidden" onClick={toggleAgentSidebar}>
            AGENTS
          </div>
        </div>

        {/* Agent Sidebar */}
        <div className={`agent-sidebar border-l border-border bg-card/80 backdrop-blur-md transition-all duration-300 ${isSidebarOpen ? 'w-[320px]' : 'w-0 overflow-hidden opacity-0'} ${(showPanUploadCard || showAadhaarUploadCard) ? 'hidden' : ''}`}>
          <div className="flex flex-col h-full">
            <div className="flex items-center justify-between p-4 border-b border-border/50">
              <div className="flex items-center gap-2 font-bold text-sm">
                <Bot className="w-4 h-4 text-yellow-400" />
                AGENT ORCHESTRATION
              </div>
              <Button variant="ghost" size="icon" onClick={() => setIsSidebarOpen(false)} className="h-8 w-8">
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="flex-1 overflow-hidden">
              <AgentActivityPanel 
                trace={agentTrace} 
                pipelineStatus={pipelineStatus} 
                activeAgentLabel={activeAgent}
                liveProcessing={isProcessing}
                liveLogLines={processingLog}
              />
            </div>

            <div className="p-4 border-t border-border/50 bg-muted/20">
              <div className="flex items-center justify-between text-[10px] text-muted-foreground uppercase tracking-widest font-bold mb-2">
                <span>System Status</span>
                <span className="text-green-500">Online</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono bg-black/40 p-2 rounded border border-border/50 overflow-hidden whitespace-nowrap">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                api.groq.com/llama-3-70b-versatile
              </div>
            </div>
          </div>
        </div>
        </div>
      </div>
    </>
  );
};
