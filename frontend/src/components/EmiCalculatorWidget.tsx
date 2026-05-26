import { useState, useEffect } from "react";
import { Slider } from "./ui/slider";
import { Button } from "./ui/button";
import { formatIndianRupees } from "@/lib/languageUtils";
import { DollarSign } from "lucide-react";

interface EmiCalculatorWidgetProps {
  initialAmount?: number;
  initialRate?: number;
  initialTenure?: number;
  onUseTerms: (amount: number, rate: number, tenure: number) => void;
}

export const EmiCalculatorWidget = ({
  initialAmount = 500000,
  initialRate = 11,
  initialTenure = 60,
  onUseTerms,
}: EmiCalculatorWidgetProps) => {
  const [amount, setAmount] = useState(initialAmount);
  const [rate, setRate] = useState(initialRate);
  const [tenure, setTenure] = useState(initialTenure);
  const [emi, setEmi] = useState(0);

  useEffect(() => {
    const monthlyRate = rate / 12 / 100;
    const emiVal =
      (amount * monthlyRate * Math.pow(1 + monthlyRate, tenure)) /
      (Math.pow(1 + monthlyRate, tenure) - 1);
    setEmi(Math.round(emiVal));
  }, [amount, rate, tenure]);

  const totalInterest = emi * tenure - amount;
  const totalPayable = emi * tenure;

  return (
    <div className="p-4 bg-card rounded-xl border border-border shadow-lg max-w-sm space-y-6 animate-in zoom-in-95 duration-300 my-4">
      <div className="flex items-center gap-2 mb-2">
        <DollarSign className="w-5 h-5" />
        <h3 className="font-semibold text-lg">EMI Calculator</h3>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Amount:</span>
            <span className="font-mono text-yellow-400 font-bold">{formatIndianRupees(amount)}</span>
          </div>
          <Slider
            value={[amount]}
            min={100000}
            max={5000000}
            step={50000}
            onValueChange={([val]) => setAmount(val)}
          />
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Rate:</span>
            <span className="font-mono text-yellow-400 font-bold">{rate.toFixed(1)}%</span>
          </div>
          <Slider
            value={[rate]}
            min={8}
            max={18}
            step={0.1}
            onValueChange={([val]) => setRate(val)}
          />
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Tenure:</span>
            <span className="font-mono text-yellow-400 font-bold">{tenure} months</span>
          </div>
          <Slider
            value={[tenure]}
            min={12}
            max={84}
            step={12}
            onValueChange={([val]) => setTenure(val)}
          />
        </div>
      </div>

      <div className="pt-4 border-t border-border/50 space-y-2">
        <div className="flex justify-between items-baseline">
          <span className="text-sm text-muted-foreground">Your EMI:</span>
          <span className="text-xl font-bold text-yellow-400">{formatIndianRupees(emi)}/month</span>
        </div>
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Total Interest:</span>
          <span>{formatIndianRupees(totalInterest)}</span>
        </div>
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Total Payable:</span>
          <span>{formatIndianRupees(totalPayable)}</span>
        </div>
      </div>

      <Button
        onClick={() => onUseTerms(amount, rate, tenure)}
        className="w-full bg-yellow-400 hover:bg-yellow-500 text-black font-bold"
      >
        Use These Terms →
      </Button>
    </div>
  );
};
