import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

interface CreditScoreCardProps {
  score: number;
  maxScore?: number;
  decision?: string;
  approvalProbability?: number | null;
  confidenceLower?: number | null;
  confidenceUpper?: number | null;
  confidenceWidth?: number | null;
  modelCertainty?: string | null;
  riskTier?: string | null;
  incomeReasonability?: {
    flag?: string;
    foir?: number;
    message?: string;
    suggested_amount?: number;
    required_monthly_income?: number;
    emi?: number;
  } | null;
  softRejectGuidance?: {
    message?: string;
    income_delta_monthly?: number;
    repayment_history_months?: number;
    repayment_history_impact?: string;
    suggested_approved_amount?: number;
    threshold_gap_points?: number;
  } | null;
  modelDriftWarning?: boolean;
  driftedFeatures?: string[];
  recommendation?: string | null;
  structuredShapNarration?: string | null;
  // New CIBIL-focused props
  cibil_score?: number | null;
  cibil_band?: string | null;
  cibil_classification?: string | null;
  risk_label?: string | null;
  industry_standard?: string | null;
  eligible?: boolean | null;
  conditional?: boolean | null;
  rate_range?: string | null;
  max_negotiation_rounds?: number | null;
  alternative_score?: number | null;
  alternative_eligible?: boolean | null;
  alternative_details?: any | null;
}

interface StructuredNarrationPayload {
  summary?: string;
  positive_factors?: Array<{ feature?: string; label?: string; shap_value?: number; actual_value?: string }>;
  negative_factors?: Array<{ feature?: string; label?: string; shap_value?: number; actual_value?: string }>;
}

interface ShapFactor {
  label: string;
  value: number;
  positive: boolean;
}

export const CreditScoreCard = ({
  score,
  maxScore = 900,
  decision,
  approvalProbability,
  confidenceLower,
  confidenceUpper,
  confidenceWidth,
  modelCertainty,
  riskTier,
  incomeReasonability,
  softRejectGuidance,
  modelDriftWarning,
  driftedFeatures,
  recommendation,
  structuredShapNarration,
  cibil_score = null,
  cibil_band = null,
  cibil_classification = null,
  risk_label = null,
  industry_standard = null,
  eligible = null,
  conditional = null,
  rate_range = null,
  max_negotiation_rounds = null,
  alternative_score = null,
  alternative_eligible = null,
  alternative_details = null,
}: CreditScoreCardProps) => {
  const [step, setStep] = useState(1);
  const [displayScore, setDisplayScore] = useState(300);
  const [arcReady, setArcReady] = useState(false);
  const [detailsReady, setDetailsReady] = useState(false);
  const [barsReady, setBarsReady] = useState(false);

  useEffect(() => {
    const timers: number[] = [];
    const targetScore = Math.max(300, Math.min(score, maxScore));
    const duration = 1800;
    let frameId = 0;
    const startTime = performance.now();

    const animateScore = (now: number) => {
      const progress = Math.min(1, (now - startTime) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(300 + (targetScore - 300) * eased));

      if (progress < 1) {
        frameId = window.requestAnimationFrame(animateScore);
      }
    };

    timers.push(window.setTimeout(() => setStep(2), 450));
    timers.push(window.setTimeout(() => setArcReady(true), 525));
    timers.push(window.setTimeout(() => setDetailsReady(true), 1050));
    timers.push(window.setTimeout(() => setBarsReady(true), 1400));
    timers.push(
      window.setTimeout(() => {
        frameId = window.requestAnimationFrame(animateScore);
      }, 500)
    );

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      window.cancelAnimationFrame(frameId);
    };
  }, [score, maxScore]);

  const normalizedScore = Math.max(300, Math.min(displayScore, maxScore));
  const gaugeProgress = Math.max(0, Math.min(1, (normalizedScore - 300) / (maxScore - 300)));
  const radius = 72;
  const circumference = 2 * Math.PI * radius;
  const dashLength = circumference * gaugeProgress;
  const bandPosition = Math.max(0, Math.min(100, ((score - 300) / (maxScore - 300)) * 100));

  const referenceScore = cibil_score ?? score;

  const getScoreTone = () => {
    if (referenceScore >= 700) return "text-[#22c55e]";
    if (referenceScore >= 550) return "text-[#F5C518]";
    return "text-[#ef4444]";
  };

  const getTierLabel = () => {
    if (risk_label) return risk_label.toUpperCase();
    if (referenceScore >= 700) return "LOW RISK TIER";
    if (referenceScore >= 550) return "MEDIUM RISK TIER";
    return "HIGH RISK TIER";
  };

  const getRateBand = () => {
    if (rate_range) return rate_range + (eligible === false ? ' (subject to conditions)' : '');
    if (referenceScore >= 700) return "10.5% – 12.5% p.a. eligible";
    if (referenceScore >= 550) return "12.5% – 15.0% p.a. eligible";
    return "15.5%+ p.a. likely";
  };

  const getFactors = (): ShapFactor[] => {
    if (score >= 700) {
      return [
        { label: "Credit History", value: 0.42, positive: true },
        { label: "Income Level", value: 0.28, positive: true },
        { label: "Employment", value: 0.12, positive: true },
        { label: "Loan Amount", value: -0.15, positive: false },
        { label: "Existing EMIs", value: -0.09, positive: false },
      ];
    }

    return [
      { label: "Credit History", value: 0.22, positive: true },
      { label: "Income Level", value: 0.16, positive: true },
      { label: "Employment", value: 0.11, positive: true },
      { label: "Loan Amount", value: -0.31, positive: false },
      { label: "Existing EMIs", value: -0.24, positive: false },
    ];
  };

  const parsedNarration = (() => {
    if (!structuredShapNarration) return null;
    try {
      const parsed = JSON.parse(structuredShapNarration) as StructuredNarrationPayload;
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch {
      return null;
    }
  })();

  const formatNarrationLabel = (value?: string) => {
    if (!value) return "Factor";
    const normalized = value.replace(/_/g, " ").trim();
    return normalized.charAt(0).toUpperCase() + normalized.slice(1).toLowerCase();
  };

  if (step === 1) {
    return (
      <div className="flex min-h-[320px] flex-col items-center justify-center rounded-2xl border border-[#2a2a2a] bg-gradient-to-br from-[#161616] via-[#111111] to-[#0d0d0d] p-6 shadow-[0_20px_60px_rgba(0,0,0,0.35)]">
        <Loader2 className="mb-4 h-12 w-12 animate-spin text-[#F5C518]" />
        <p className="text-lg font-medium text-slate-300 animate-pulse">Checking your CIBIL score...</p>
      </div>
    );
  }

  const factors = getFactors();
  const maxAbsValue = Math.max(...factors.map((factor) => Math.abs(factor.value)));

  return (
    <div className="relative overflow-hidden rounded-2xl border border-[#2a2a2a] bg-gradient-to-br from-[#161616] via-[#111111] to-[#0d0d0d] p-6 shadow-[0_20px_60px_rgba(0,0,0,0.35)] animate-slide-up">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(245,197,24,0.06),transparent_40%)]" />

      <div className="relative text-center">
        <p className="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-400">Your Credit Score</p>

        <div className="relative mx-auto mt-5 inline-flex items-center justify-center">
          <svg className="h-[220px] w-[220px] -rotate-90 transform" viewBox="0 0 220 220" aria-hidden="true">
            <defs>
              <linearGradient id="credit-score-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#ef4444" />
                <stop offset="50%" stopColor="#F5C518" />
                <stop offset="100%" stopColor="#22c55e" />
              </linearGradient>
            </defs>
            <circle
              cx="110"
              cy="110"
              r={radius}
              fill="none"
              stroke="rgba(255,255,255,0.08)"
              strokeWidth="14"
            />
            <circle
              cx="110"
              cy="110"
              r={radius}
              fill="none"
              stroke="url(#credit-score-gradient)"
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray={`${arcReady ? dashLength : 0} ${circumference}`}
              style={{ transition: "stroke-dasharray 2s ease-in-out" }}
            />
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={cn("text-[48px] font-black leading-none tracking-tight", getScoreTone())}>
              {cibil_score ?? displayScore}
            </span>
            <span className="mt-1 text-xs font-semibold tracking-[0.3em] text-slate-400">/ {maxScore}</span>
          </div>
        </div>

        <div
          className={cn(
            "mx-auto mt-4 inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold tracking-[0.25em] uppercase transition-all duration-500",
            referenceScore >= 700
              ? "border-[#22c55e]/30 bg-[#22c55e]/10 text-[#22c55e]"
              : referenceScore >= 550
                ? "border-[#F5C518]/30 bg-[#F5C518]/10 text-[#F5C518]"
                : "border-[#ef4444]/30 bg-[#ef4444]/10 text-[#ef4444]",
            detailsReady ? "translate-y-0 opacity-100" : "translate-y-1 opacity-0"
          )}
        >
          <CheckCircle2 className="h-4 w-4" />
          {getTierLabel()}
        </div>
      </div>

      {alternative_score != null && (
        <div className={cn(
          "relative mt-6 rounded-2xl border border-blue-500/30 bg-blue-500/10 p-5 shadow-lg transition-all duration-500",
          detailsReady ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"
        )}>
          <div className="flex items-start gap-3">
            <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-blue-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-blue-300">Alternative Assessment</p>
              <p className="mt-1 text-sm text-blue-100">
                {alternative_details?.message || `Your alternative profile score is ${alternative_score}/100.`}
              </p>
              {alternative_details?.components && (
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {Object.entries(alternative_details.components).map(([key, comp]: [string, any]) => (
                    <div key={key} className="rounded-lg border border-blue-500/20 bg-blue-950/30 px-3 py-2 text-xs">
                      <span className="font-semibold text-blue-300">+{comp.score}</span>{" "}
                      <span className="text-blue-200/80">{comp.reason}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="relative mt-6 rounded-2xl border border-[#2a2a2a] bg-[#0f0f0f]/90 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.02)]">
        <div className="mb-2 flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
          <span>300</span>
          <span>550</span>
          <span>700</span>
          <span>{maxScore}</span>
        </div>

        <div className="relative h-4 overflow-hidden rounded-full bg-[#262626]">
          <div className="absolute inset-y-0 left-0 w-[40%] bg-[#ef4444]" />
          <div className="absolute inset-y-0 left-[40%] w-[25%] bg-[#F5C518]" />
          <div className="absolute inset-y-0 left-[65%] w-[35%] bg-[#22c55e]" />

          <div
            className="absolute -top-1.5 h-7 w-7 -translate-x-1/2 transition-[left] duration-1000 ease-out"
            style={{ left: `${bandPosition}%` }}
          >
            <div className="mx-auto h-0 w-0 border-l-[8px] border-r-[8px] border-t-[11px] border-l-transparent border-r-transparent border-t-[#F5C518] drop-shadow-[0_2px_6px_rgba(245,197,24,0.35)]" />
          </div>
        </div>

        {cibil_band ? (
          <div className="mt-2 text-[12px] font-bold uppercase tracking-[0.08em] text-slate-200">
            {industry_standard ? `${industry_standard} · ` : ''}{cibil_band} · {cibil_classification}
          </div>
        ) : (
          <div
            className="mt-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-[#F5C518] transition-all duration-700"
            style={{ marginLeft: `calc(${bandPosition}% - 2.5rem)` }}
          >
            Your score: HERE ↑
          </div>
        )}

        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-300">
          <div className="rounded-xl border border-[#3a1f1f] bg-[#1a1212] px-2 py-3">
            <div className="text-[#ef4444]">300-549</div>
            <div className="mt-1 text-slate-100">High Risk</div>
            <div className="mt-2 h-2 rounded-full bg-[#351515]">
              <div className="h-full w-[72%] rounded-full bg-[#ef4444]" />
            </div>
          </div>
          <div className="rounded-xl border border-[#4b3b13] bg-[#1b170d] px-2 py-3">
            <div className="text-[#F5C518]">550-699</div>
            <div className="mt-1 text-slate-100">Medium Risk</div>
            <div className="mt-2 h-2 rounded-full bg-[#272218]">
              <div className="h-full w-[84%] rounded-full bg-[#F5C518]" />
            </div>
          </div>
          <div className="rounded-xl border border-[#16381f] bg-[#0d1710] px-2 py-3">
            <div className="text-[#22c55e]">700-900</div>
            <div className="mt-1 text-slate-100">Low Risk</div>
            <div className="mt-2 h-2 rounded-full bg-[#17261b]">
              <div className="h-full w-[92%] rounded-full bg-[#22c55e]" />
            </div>
          </div>
        </div>
      </div>

      <div className={cn("relative mt-6 space-y-4 transition-all duration-500", detailsReady ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0") }>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-[#2a2a2a] bg-[#101010] px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">Decision</p>
            <p className="mt-2 text-sm font-semibold text-slate-100">{decision || (score >= 700 ? "APPROVED" : "APPROVED_WITH_CONDITIONS")}</p>
            <p className="mt-1 text-xs text-slate-400">
              {riskTier || getTierLabel().replace(" TIER", "")}
            </p>
          </div>
          <div className="rounded-2xl border border-[#2a2a2a] bg-[#101010] px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">Confidence</p>
            <p className="mt-2 text-sm font-semibold text-slate-100">
              {approvalProbability != null ? `${Math.round(approvalProbability * 100)}% approval probability` : "Model-backed estimate"}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              {confidenceLower != null && confidenceUpper != null
                ? `Range ${Math.round(confidenceLower * 100)}% - ${Math.round(confidenceUpper * 100)}%`
                : confidenceWidth != null
                  ? `Width ${Math.round(confidenceWidth * 100)} pts`
                  : modelCertainty || "Confidence bounds unavailable"}
            </p>
          </div>
        </div>

        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">Why you were approved</p>
          <div className="space-y-3">
            {factors.map((factor, index) => {
              const width = (Math.abs(factor.value) / maxAbsValue) * 100;

              return (
                <div
                  key={factor.label}
                  className="grid grid-cols-[120px_minmax(0,1fr)_56px] items-center gap-3 text-sm sm:grid-cols-[140px_minmax(0,1fr)_64px]"
                  style={{ transitionDelay: `${index * 90}ms` }}
                >
                  <span className="text-slate-300">{factor.label}</span>
                  <div className="relative h-2 overflow-hidden rounded-full bg-[#2a2a2a]">
                    <div className="absolute inset-y-0 left-1/2 w-px bg-white/10" />
                    <div
                      className={cn(
                        "absolute inset-y-0 rounded-full transition-all duration-700 ease-out",
                        factor.positive ? "bg-[#22c55e]" : "bg-[#ef4444]"
                      )}
                      style={{
                        width: barsReady ? `${width}%` : "0%",
                        left: factor.positive ? 0 : `calc(50% - ${barsReady ? width : 0}%)`,
                      }}
                    />
                  </div>
                  <span className={cn("text-right text-xs font-semibold", factor.positive ? "text-[#22c55e]" : "text-[#ef4444]") }>
                    {factor.value > 0 ? "+" : ""}{factor.value.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-2xl border border-[#2f2608] bg-[#111111] px-4 py-4 shadow-[0_10px_30px_rgba(0,0,0,0.25)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#F5C518]">What this means for your rate</p>
          <p className="mt-2 text-sm text-slate-200">{getRateBand()}</p>
          {max_negotiation_rounds != null && (
            <p className="mt-1 text-xs text-slate-400">Max negotiation rounds: {max_negotiation_rounds}</p>
          )}
        </div>

        {incomeReasonability && (
          <div className="rounded-2xl border border-[#2a2a2a] bg-[#101010] px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">FOIR check</p>
            <p className="mt-2 text-sm text-slate-200">{incomeReasonability.message || "Income support is acceptable."}</p>
            {incomeReasonability.foir != null && (
              <p className="mt-1 text-xs text-slate-400">FOIR: {Math.round(incomeReasonability.foir * 100)}%</p>
            )}
          </div>
        )}

        {softRejectGuidance && (
          <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-amber-200">Soft reject guidance</p>
            <p className="mt-2 text-sm text-amber-50">{softRejectGuidance.message}</p>
            {softRejectGuidance.repayment_history_impact && (
              <p className="mt-1 text-xs text-amber-100/80">{softRejectGuidance.repayment_history_impact}</p>
            )}
          </div>
        )}

        {modelDriftWarning && (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-rose-200">Model drift warning</p>
            <p className="mt-2 text-sm text-rose-50">{recommendation || "Recent applicant patterns differ from training data."}</p>
            {driftedFeatures && driftedFeatures.length > 0 && (
              <p className="mt-1 text-xs text-rose-100/80">Affected features: {driftedFeatures.join(", ")}</p>
            )}
          </div>
        )}

        <div className="rounded-2xl border border-[#2a2a2a] bg-[#101010] px-4 py-4">
          <div className="flex items-start gap-2 text-xs text-slate-300">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#22c55e]" />
            <p>Green bars = helped your application. Red bars = reduced your score.</p>
          </div>
        </div>

        {parsedNarration && (
          <div className="rounded-2xl border border-[#2a2a2a] bg-[#101010] px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">Narration</p>
            {parsedNarration.summary && (
              <p className="mt-2 text-sm text-slate-200">
                {parsedNarration.summary}
              </p>
            )}
            {!parsedNarration.summary && (
              <p className="mt-2 text-sm text-slate-200">
                Here’s a plain-English breakdown of what influenced your score.
              </p>
            )}

            {parsedNarration.positive_factors?.length ? (
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[#22c55e]">What helped you</p>
                <ul className="mt-2 space-y-2 text-sm text-slate-200">
                  {parsedNarration.positive_factors.map((factor, index) => (
                    <li key={`${factor.feature || factor.label || "positive"}-${index}`} className="flex items-start gap-2">
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-[#22c55e]" />
                      <span>
                        <span className="font-medium">{formatNarrationLabel(factor.label || factor.feature)}</span>
                        {typeof factor.shap_value === "number" ? ` (${factor.shap_value.toFixed(3)})` : ""}
                        {factor.actual_value ? ` · ${factor.actual_value}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {parsedNarration.negative_factors?.length ? (
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[#ef4444]">What pulled you down</p>
                <ul className="mt-2 space-y-2 text-sm text-slate-200">
                  {parsedNarration.negative_factors.map((factor, index) => (
                    <li key={`${factor.feature || factor.label || "negative"}-${index}`} className="flex items-start gap-2">
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-[#ef4444]" />
                      <span>
                        <span className="font-medium">{formatNarrationLabel(factor.label || factor.feature)}</span>
                        {typeof factor.shap_value === "number" ? ` (${factor.shap_value.toFixed(3)})` : ""}
                        {factor.actual_value ? ` · ${factor.actual_value}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};
