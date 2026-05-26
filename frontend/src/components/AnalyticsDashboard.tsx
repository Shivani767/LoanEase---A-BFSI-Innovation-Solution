import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Download, Info, TrendingUp, AlertCircle, CheckCircle2, BarChart3 } from "lucide-react";
import { formatIndianRupees } from "@/lib/languageUtils";
import { API_BASE_URL } from "@/config";
import { toast } from "sonner";

const ANALYTICS_DEMO_DATA = {
  success: true,
  session_found: false,
  loan_data: {
    amount: 500000,
    rate: 11.0,
    tenure_months: 60,
    emi: 10871,
    total_payable: 652260,
    total_interest: 152260,
    purpose: "medical",
  },
  credit_data: {
    credit_score: 750,
    risk_score: 80,
    risk_tier: "Low Risk",
    shap_factors: [
      { feature: "Credit History", value: 0.41, direction: "positive" },
      { feature: "Income Level", value: 0.28, direction: "positive" },
      { feature: "Loan Amount", value: -0.15, direction: "negative" },
      { feature: "Employment", value: 0.12, direction: "positive" },
      { feature: "Existing EMIs", value: -0.09, direction: "negative" },
    ],
  },
  negotiation_summary: {
    opening_rate: 11.5,
    final_rate: 11.0,
    rounds_taken: 2,
    total_savings: 8400,
  },
  loan_health: {
    loan_health_score: 82,
    health_label: "Good",
    factors: [
      { factor: "Comfortable EMI ratio", impact: 0, advice: "Excellent EMI-to-income ratio reduces default risk" },
      { factor: "Strong credit profile", impact: 0, advice: "Timely repayment can push your score toward 850+" },
    ],
    prepayment_advice: "Prepaying ₹10,000 in Month 6 saves ₹18,000 in total interest",
  },
  benchmark: {
    avg_credit_score: 720,
    avg_income_normalized: 70,
    avg_loan_to_income: 65,
    avg_employment: 75,
    avg_repayment: 80,
    avg_coapplicant: 60,
  },
  applicant_normalized: {
    credit_score: 75,
    income_norm: 80,
    loan_income: 65,
    employment: 75,
    repayment: 83,
    coapplicant: 60,
  },
};

const normalizeAnalyticsData = (raw: any) => {
  const safeLoan = raw?.loan_data || {};
  const safeCredit = raw?.credit_data || {};
  const safeSummary = raw?.negotiation_summary || {};
  const safeHealth = raw?.loan_health || {};

  return {
    success: raw?.success ?? true,
    session_found: raw?.session_found ?? Boolean(raw),
    loan_data: {
      amount: Number(safeLoan.amount ?? 500000),
      rate: Number(safeLoan.rate ?? 11.0),
      tenure_months: Number(safeLoan.tenure_months ?? 60),
      emi: Number(safeLoan.emi ?? 10871),
      total_payable: Number(safeLoan.total_payable ?? 652260),
      total_interest: Number(safeLoan.total_interest ?? 152260),
      purpose: raw?.purpose || safeLoan.purpose || "general",
    },
    credit_data: {
      credit_score: Number(safeCredit.credit_score ?? 750),
      risk_score: Number(safeCredit.risk_score ?? 80),
      risk_tier: safeCredit.risk_tier ?? "Low Risk",
      shap_factors: Array.isArray(safeCredit.shap_factors) && safeCredit.shap_factors.length > 0
        ? safeCredit.shap_factors
        : ANALYTICS_DEMO_DATA.credit_data.shap_factors,
    },
    negotiation_summary: {
      opening_rate: Number(safeSummary.opening_rate ?? 11.5),
      final_rate: Number(safeSummary.final_rate ?? 11.0),
      rounds_taken: Number(safeSummary.rounds_taken ?? 2),
      total_savings: Number(safeSummary.total_savings ?? 8400),
    },
    loan_health: {
      loan_health_score: Number(safeHealth.loan_health_score ?? 82),
      health_label: safeHealth.health_label ?? "Good",
      factors: Array.isArray(safeHealth.factors) && safeHealth.factors.length > 0
        ? safeHealth.factors
        : ANALYTICS_DEMO_DATA.loan_health.factors,
      prepayment_advice: safeHealth.prepayment_advice ?? ANALYTICS_DEMO_DATA.loan_health.prepayment_advice,
    },
    benchmark: raw?.benchmark || ANALYTICS_DEMO_DATA.benchmark,
    applicant_normalized: raw?.applicant_normalized || ANALYTICS_DEMO_DATA.applicant_normalized,
  };
};

interface AnalyticsDashboardProps {
  sessionId: string;
  customerName: string;
  initialAmount?: number;
  initialInterest?: number;
  initialTenure?: number;
}

declare global {
  interface Window {
    Chart: any;
    html2canvas: any;
    jspdf: any;
    _analyticsSessionId?: string;
  }
}

export const AnalyticsDashboard = ({ sessionId, customerName, initialAmount, initialInterest, initialTenure }: AnalyticsDashboardProps) => {
  const [analyticsData, setAnalyticsData] = useState<any>(ANALYTICS_DEMO_DATA);
  const [loading, setLoading] = useState(true);
  const [loanAmount, setLoanAmount] = useState(initialAmount || 500000);
  const [interestRate, setInterestRate] = useState(initialInterest || 11.0);
  const [tenure, setTenure] = useState(initialTenure || 60);
  const dashboardRef = useRef<HTMLDivElement>(null);

  const resolveAnalyticsSessionIds = () => {
    const querySession = new URLSearchParams(window.location.search).get("session");
    const storedSession = localStorage.getItem("loanease_session_id");
    const globalSession = window._analyticsSessionId;

    return [
      sessionId,
      querySession,
      globalSession,
      storedSession,
      sessionId?.split("-")[0],
      querySession?.split("-")[0],
      storedSession?.split("-")[0],
      "demo",
    ].filter((value, index, array) => Boolean(value) && array.indexOf(value) === index) as string[];
  };

  // Fetch analytics data from backend
  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const attempts = resolveAnalyticsSessionIds();
        let loaded = false;

        for (const candidateId of attempts) {
          try {
            const response = await fetch(`${API_BASE_URL}/analytics/${candidateId}`, {
              signal: AbortSignal.timeout(8000),
            });

            if (!response.ok) {
              continue;
            }

            const data = normalizeAnalyticsData(await response.json());
            setAnalyticsData(data);
            setLoanAmount(data.loan_data.amount);
            setInterestRate(data.loan_data.rate);
            setTenure(data.loan_data.tenure_months);
            loaded = true;
            break;
          } catch {
            continue;
          }
        }

        if (!loaded) {
          setAnalyticsData(ANALYTICS_DEMO_DATA);
          setLoanAmount(ANALYTICS_DEMO_DATA.loan_data.amount);
          setInterestRate(ANALYTICS_DEMO_DATA.loan_data.rate);
          setTenure(ANALYTICS_DEMO_DATA.loan_data.tenure_months);
        }
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
        setAnalyticsData(ANALYTICS_DEMO_DATA);
        setLoanAmount(ANALYTICS_DEMO_DATA.loan_data.amount);
        setInterestRate(ANALYTICS_DEMO_DATA.loan_data.rate);
        setTenure(ANALYTICS_DEMO_DATA.loan_data.tenure_months);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [sessionId]);

  // Refs for Chart instances
  const chartRefs = {
    risk: useRef<HTMLCanvasElement>(null),
    shap: useRef<HTMLCanvasElement>(null),
    emi: useRef<HTMLCanvasElement>(null),
    repayment: useRef<HTMLCanvasElement>(null),
    radar: useRef<HTMLCanvasElement>(null),
  };

  const chartInstances = useRef<{ [key: string]: any }>({});

  // Calculation logic
  const calculateEMI = (p: number, r: number, n: number) => {
    const monthlyRate = r / 12 / 100;
    return Math.round((p * monthlyRate * Math.pow(1 + monthlyRate, n)) / (Math.pow(1 + monthlyRate, n) - 1));
  };

  const emi = calculateEMI(loanAmount, interestRate, tenure);
  const totalPayable = emi * tenure;
  const totalInterest = totalPayable - loanAmount;

  const formatCurrency = (val: number) => {
    return formatIndianRupees(val);
  };

  // Amortization Schedule
  const getAmortizationData = () => {
    const data: { year: number; principal: number; interest: number }[] = [];
    let outstanding = loanAmount;
    const monthlyRate = interestRate / 12 / 100;

    for (let year = 1; year <= Math.ceil(tenure / 12); year++) {
      let yearlyPrincipal = 0;
      let yearlyInterest = 0;
      for (let month = 1; month <= 12 && (year - 1) * 12 + month <= tenure; month++) {
        const interestComp = outstanding * monthlyRate;
        const principalComp = emi - interestComp;
        yearlyPrincipal += principalComp;
        yearlyInterest += interestComp;
        outstanding -= principalComp;
      }
      data.push({ year, principal: Math.round(yearlyPrincipal), interest: Math.round(yearlyInterest) });
    }
    return data;
  };

  // Initialize and Update Charts
  useEffect(() => {
    if (!window.Chart) return;

    const Chart = window.Chart;
    const analytics = normalizeAnalyticsData(analyticsData || ANALYTICS_DEMO_DATA);

    // Destroy existing instances to prevent memory leaks
    Object.values(chartInstances.current).forEach((chart) => chart?.destroy());

    const riskScore = Number(analytics.credit_data.risk_score || 80);
    const shapFactors = Array.isArray(analytics.credit_data.shap_factors)
      ? analytics.credit_data.shap_factors
      : ANALYTICS_DEMO_DATA.credit_data.shap_factors;

    // 1. Risk Score Gauge
    try {
      if (chartRefs.risk.current) {
        chartInstances.current.risk = new Chart(chartRefs.risk.current, {
          type: 'doughnut',
          data: {
            datasets: [{
              data: [riskScore, Math.max(0, 100 - riskScore)],
              backgroundColor: [
                riskScore < 50 ? '#ef4444' : riskScore < 75 ? '#F5C518' : '#22c55e',
                '#3a3a3a'
              ],
              borderWidth: 0,
              circumference: 180,
              rotation: 270,
            }]
          },
          options: {
            cutout: '80%',
            plugins: { tooltip: { enabled: false }, legend: { display: false } },
            responsive: true,
            maintainAspectRatio: false,
          }
        });
      }
    } catch (error) {
      console.error('Risk chart failed:', error);
    }

    // 2. SHAP Factors (Horizontal Bar)
    try {
      if (chartRefs.shap.current) {
        chartInstances.current.shap = new Chart(chartRefs.shap.current, {
          type: 'bar',
          data: {
            labels: shapFactors.map((d: any) => d.feature),
            datasets: [{
              label: 'Impact Score',
              data: shapFactors.map((d: any) => Number(d.value ?? 0)),
              backgroundColor: shapFactors.map((d: any) => Number(d.value ?? 0) >= 0 ? '#F5C518' : '#ef4444'),
              borderRadius: 4,
            }]
          },
          options: {
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: {
              x: { grid: { color: '#3a3a3a' }, ticks: { color: '#9ca3af' } },
              y: { grid: { display: false }, ticks: { color: '#9ca3af' } }
            },
            responsive: true,
            maintainAspectRatio: false,
          }
        });
      }
    } catch (error) {
      console.error('SHAP chart failed:', error);
    }

    // 3. EMI Breakdown (Doughnut)
    try {
      if (chartRefs.emi.current) {
        chartInstances.current.emi = new Chart(chartRefs.emi.current, {
          type: 'doughnut',
          data: {
            labels: ['Principal Amount', 'Total Interest'],
            datasets: [{
              data: [loanAmount, totalInterest],
              backgroundColor: ['#F5C518', '#3a3a3a'],
              borderWidth: 0,
            }]
          },
          options: {
            cutout: '75%',
            plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af' } } },
            responsive: true,
            maintainAspectRatio: false,
          }
        });
      }
    } catch (error) {
      console.error('EMI chart failed:', error);
    }

    // 4. Yearly Repayment (Grouped Bar)
    const amortData = getAmortizationData();
    try {
      if (chartRefs.repayment.current) {
        chartInstances.current.repayment = new Chart(chartRefs.repayment.current, {
          type: 'bar',
          data: {
            labels: amortData.map(d => `Year ${d.year}`),
            datasets: [
              { label: 'Principal Paid', data: amortData.map(d => d.principal), backgroundColor: '#F5C518' },
              { label: 'Interest Paid', data: amortData.map(d => d.interest), backgroundColor: '#4a4a4a' }
            ]
          },
          options: {
            scales: {
              x: { stacked: false, grid: { display: false }, ticks: { color: '#9ca3af' } },
              y: { stacked: false, grid: { color: '#3a3a3a' }, ticks: { color: '#9ca3af' } }
            },
            plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af' } } },
            responsive: true,
            maintainAspectRatio: false,
          }
        });
      }
    } catch (error) {
      console.error('Repayment chart failed:', error);
    }

    // 5. Radar Chart
    try {
      if (chartRefs.radar.current && analytics.benchmark) {
        const benchmark = analytics.benchmark;
        const applicantData = [
          Number(analytics.credit_data.credit_score || 750),
          Number(analytics.applicant_normalized?.income_norm || 75),
          Number(analytics.applicant_normalized?.loan_income || 80),
          Number(analytics.applicant_normalized?.employment || 85),
          Number(analytics.applicant_normalized?.repayment || 90),
          Number(analytics.applicant_normalized?.coapplicant || 60),
        ];

        const benchmarkData = [
          Number(benchmark.avg_credit_score || 720),
          Number(benchmark.avg_income_normalized || 70),
          Number(benchmark.avg_loan_to_income || 65),
          Number(benchmark.avg_employment || 75),
          Number(benchmark.avg_repayment || 80),
          Number(benchmark.avg_coapplicant || 60),
        ];

        chartInstances.current.radar = new Chart(chartRefs.radar.current, {
          type: 'radar',
          data: {
            labels: ['Credit Score', 'Monthly Income', 'Loan-to-Income', 'Employment Stability', 'Repayment History', 'Co-applicant Support'],
            datasets: [
              {
                label: 'You',
                data: applicantData,
                borderColor: '#F5C518',
                backgroundColor: 'rgba(245, 197, 24, 0.3)',
                fill: true,
              },
              {
                label: 'Avg Approved Borrower',
                data: benchmarkData,
                borderColor: '#6b7280',
                backgroundColor: 'rgba(107, 114, 128, 0.2)',
                fill: true,
              }
            ]
          },
          options: {
            scales: {
              r: {
                angleLines: { color: '#3a3a3a' },
                grid: { color: '#3a3a3a' },
                pointLabels: { color: '#9ca3af', font: { size: 10 } },
                ticks: { display: false },
                suggestedMin: 0,
                suggestedMax: 100
              }
            },
            plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af' } } },
            responsive: true,
            maintainAspectRatio: false,
          }
        });
      }
    } catch (error) {
      console.error('Radar chart failed:', error);
    }

    return () => {
      Object.values(chartInstances.current).forEach((chart) => chart?.destroy());
    };
  }, [loanAmount, interestRate, tenure, analyticsData]);

  const handleDownloadPDF = async () => {
    try {
      // Check if libraries are loaded
      if (!window.html2canvas) {
        toast.error("HTML2Canvas library not loaded");
        return;
      }
      
      if (!window.jspdf) {
        toast.error("jsPDF library not loaded");
        return;
      }
      
      if (!dashboardRef.current) {
        toast.error("Dashboard content not available");
        return;
      }

      // Show loading state
      toast.loading("Generating PDF...");

      const canvas = await window.html2canvas(dashboardRef.current, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#1a1a1a',
        logging: false,
      });
      
      const imgData = canvas.toDataURL('image/png');
      const { jsPDF } = window.jspdf;
      const pdf = new jsPDF('p', 'mm', 'a4');
      
      const imgProps = pdf.getImageProperties(imgData);
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
      
      // Set dark background
      pdf.setFillColor(26, 26, 26);
      pdf.rect(0, 0, pdfWidth, pdf.internal.pageSize.getHeight(), 'F');
      
      // Add header text
      pdf.setTextColor(255, 255, 255);
      pdf.setFontSize(18);
      pdf.text("LoanEase Analytics Report", 20, 20);
      pdf.setFontSize(10);
      pdf.text(`Applicant: ${customerName || 'N/A'}`, 20, 28);
      pdf.text(`Date: ${new Date().toLocaleDateString('en-IN')}`, 20, 33);
      pdf.text(`Session ID: ${sessionId || 'N/A'}`, 20, 38);
      
      // Add the dashboard image
      pdf.addImage(imgData, 'PNG', 0, 45, pdfWidth, pdfHeight);
      
      // Save the PDF
      const fileName = `LoanEase_Report_${customerName?.replace(/\s+/g, '_') || 'Unknown'}_${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
      
      toast.success("PDF downloaded successfully!");
    } catch (error) {
      console.error('PDF generation error:', error);
      toast.error("Failed to generate PDF. Please try again.");
    }
  };

  if (loading) {
    return (
      <div className="w-full max-w-6xl mx-auto p-4 space-y-8 animate-slide-up" id="analytics-section">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
          <p className="text-muted-foreground">Loading your analytics...</p>
        </div>
      </div>
    );
  }

  const analytics = normalizeAnalyticsData(analyticsData || ANALYTICS_DEMO_DATA);
  const riskScore = Number(analytics.credit_data.risk_score || 80);
  const purpose = analytics.loan_data.purpose || "general";
  const loanHealth = analytics.loan_health || ANALYTICS_DEMO_DATA.loan_health;

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-8 animate-slide-up" id="analytics-section">
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-bold font-display text-white flex items-center justify-center gap-2">
        <BarChart3 className="w-8 h-8" />
        Your Loan Insights
        <span className="ml-2 text-sm bg-accent/20 text-accent px-3 py-1 rounded-full uppercase tracking-wider font-semibold">
          {purpose.replace("_", " ")}
        </span>
      </h2>
        <p className="text-muted-foreground">Complete breakdown of your loan and approval profile</p>
      </div>

      <Card className="bg-card border-none shadow-lg overflow-hidden">
        <div className="bg-gradient-primary h-1" />
        <CardHeader>
          <CardTitle className="text-xl flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-accent" />
            Loan Health
          </CardTitle>
          <CardDescription>Post-sanction repayment guidance and early-warning cues.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-[160px_minmax(0,1fr)] md:items-center">
            <div className="rounded-2xl border border-border/50 bg-secondary/30 p-5 text-center">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Health Score</p>
              <p className={`mt-2 text-5xl font-black ${Number(loanHealth.loan_health_score || 0) >= 80 ? "text-green-400" : Number(loanHealth.loan_health_score || 0) >= 60 ? "text-accent" : "text-red-400"}`}>
                {Math.round(Number(loanHealth.loan_health_score || 0))}
              </p>
              <p className="mt-1 text-xs uppercase tracking-[0.25em] text-muted-foreground">{loanHealth.health_label || "Moderate"}</p>
            </div>
            <div className="space-y-3">
              {(loanHealth.factors || []).map((factor: any, index: number) => (
                <div key={`${factor.factor || factor.advice || index}`} className="rounded-xl border border-border/50 bg-background/40 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-white">{factor.factor}</p>
                    <span className={factor.impact > 0 ? "text-green-400" : factor.impact < 0 ? "text-red-400" : "text-accent"}>
                      {factor.impact > 0 ? `+${factor.impact}` : factor.impact || 0}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{factor.advice}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-accent/20 bg-accent/10 p-4 text-sm text-accent-foreground">
            {loanHealth.prepayment_advice}
          </div>
        </CardContent>
      </Card>

      {/* Live EMI Calculator */}
      <Card className="bg-card border-none shadow-lg overflow-hidden">
        <div className="bg-gradient-primary h-1" />
        <CardHeader>
          <CardTitle className="text-xl">Adjust Your Loan Parameters</CardTitle>
          <CardDescription>See how changing your loan amount, rate, or tenure affects your repayment.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          <div className="text-center py-4 bg-secondary/30 rounded-lg border border-border/50">
            <p className="text-sm text-muted-foreground mb-1 uppercase tracking-wider">YOUR EMI</p>
            <p className="text-4xl font-bold text-accent">{formatCurrency(emi)}</p>
            <p className="text-xs text-muted-foreground">per month</p>
          </div>

          {/* Info Boxes */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-card rounded-lg border border-border/50">
              <p className="text-sm text-muted-foreground mb-1">Total Payable</p>
              <p className="text-xl font-bold text-white">{formatCurrency(totalPayable)}</p>
            </div>
            <div className="text-center p-4 bg-card rounded-lg border border-border/50">
              <p className="text-sm text-muted-foreground mb-1">Total Interest</p>
              <p className="text-xl font-bold text-accent">{formatCurrency(totalInterest)}</p>
            </div>
            <div className="text-center p-4 bg-card rounded-lg border border-border/50">
              <p className="text-sm text-muted-foreground mb-1">Interest %</p>
              <p className="text-xl font-bold text-white">{((totalInterest / totalPayable) * 100).toFixed(1)}%</p>
              <p className="text-xs text-muted-foreground">of total</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium">Loan Amount</label>
                <span className="text-accent font-bold">{formatCurrency(loanAmount)}</span>
              </div>
              <Slider
                value={[loanAmount]}
                min={100000}
                max={5000000}
                step={50000}
                onValueChange={(val) => setLoanAmount(val[0])}
                className="py-4"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>₹1L</span>
                <span>₹50L</span>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium">Interest Rate</label>
                <span className="text-accent font-bold">{interestRate}% p.a.</span>
              </div>
              <Slider
                value={[interestRate]}
                min={8}
                max={24}
                step={0.25}
                onValueChange={(val) => setInterestRate(val[0])}
                className="py-4"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>8%</span>
                <span>24%</span>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium">Tenure</label>
                <span className="text-accent font-bold">{tenure} Months</span>
              </div>
              <Slider
                value={[tenure]}
                min={12}
                max={84}
                step={6}
                onValueChange={(val) => setTenure(val[0])}
                className="py-4"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>12m</span>
                <span>84m</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div ref={dashboardRef} className="space-y-6">
        {/* Row 1: EMI Calculator (full width) - Already above */}
        
        {/* Row 2: Doughnut | Gauge */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="bg-[#1a1a1a] border-[#2a2a2a] rounded-2xl p-5">
            <CardTitle className="text-lg mb-4 text-center">EMI Breakdown</CardTitle>
            <div className="relative h-64">
              <canvas ref={chartRefs.emi}></canvas>
              {/* Center Text Overlay */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <p className="text-[10px] text-[#9ca3af] uppercase">Total Payable</p>
                <p className="text-lg font-bold text-white">{formatCurrency(totalPayable)}</p>
                <p className="text-xs text-[#F5C518] mt-1">{formatCurrency(emi)}/mo</p>
              </div>
            </div>
            {/* Legend */}
            <div className="flex justify-center gap-6 mt-4 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-[#F5C518] rounded"></div>
                <span className="text-[#9ca3af]">Principal {formatCurrency(loanAmount)} ({((loanAmount/totalPayable)*100).toFixed(1)}%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-[#2a2a2a] rounded"></div>
                <span className="text-[#9ca3af]">Interest {formatCurrency(totalInterest)} ({((totalInterest/totalPayable)*100).toFixed(1)}%)</span>
              </div>
            </div>
          </Card>

          <Card className="bg-[#1a1a1a] border-[#2a2a2a] rounded-2xl p-5">
            <CardTitle className="text-lg mb-4 text-center">Risk Score Gauge</CardTitle>
            <div className="relative h-64">
              <canvas ref={chartRefs.risk}></canvas>
              {/* Needle and Score */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <p className="text-5xl font-bold text-white">{riskScore}</p>
                <p className={`text-sm font-semibold uppercase tracking-widest ${
                  riskScore >= 75 ? 'text-green-500' : 
                  riskScore >= 50 ? 'text-yellow-500' : 'text-red-500'
                }`}>
                  {analytics.credit_data.risk_tier}
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* Row 3: Yearly Bar (full width) */}
        <Card className="bg-[#1a1a1a] border-[#2a2a2a] rounded-2xl p-5">
          <CardTitle className="text-lg mb-4 text-center">Yearly Amortization Breakdown</CardTitle>
          <div className="h-64">
            <canvas ref={chartRefs.repayment}></canvas>
          </div>
          <p className="text-[10px] text-[#9ca3af] mt-4 text-center">
            Interest dominates early years — this is why prepayment saves money.
          </p>
        </Card>

        {/* Row 4: SHAP bars | Radar */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="bg-[#1a1a1a] border-[#2a2a2a] rounded-2xl p-5">
            <CardTitle className="text-lg mb-2">What Influenced Your Approval</CardTitle>
            <CardDescription className="text-sm text-[#9ca3af] mb-4">Powered by SHAP Explainability</CardDescription>
            <div className="h-64">
              <canvas ref={chartRefs.shap}></canvas>
            </div>
          </Card>

          <Card className="bg-[#1a1a1a] border-[#2a2a2a] rounded-2xl p-5">
            <CardTitle className="text-lg mb-2">Applicant Benchmark Radar</CardTitle>
            <CardDescription className="text-sm text-[#9ca3af] mb-4">You vs Avg Approved Borrower</CardDescription>
            <div className="h-64">
              <canvas ref={chartRefs.radar}></canvas>
            </div>
          </Card>
        </div>
      </div>

      <div className="flex justify-center pb-12">
        <Button 
          variant="accent" 
          size="lg" 
          className="px-8 shadow-glow hover:scale-105 transition-all"
          onClick={handleDownloadPDF}
        >
          <Download className="mr-2 h-5 w-5" />
          Download Loan Report (PDF)
        </Button>
      </div>
    </div>
  );
};
