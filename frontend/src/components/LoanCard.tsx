import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import { Check, Sparkles } from "lucide-react";

interface LoanCardProps {
  amount: number;
  minInterest: number;
  maxInterest: number;
  minTenure: number;
  maxTenure: number;
  isRecommended?: boolean;
  onSelect: (interest: number, tenure: number) => void;
}

export const LoanCard = ({
  amount,
  minInterest,
  maxInterest,
  minTenure,
  maxTenure,
  isRecommended,
  onSelect,
}: LoanCardProps) => {
  const [tenure, setTenure] = useState(minTenure);
  const interest = minInterest;

  const emi = Math.round(
    (amount * (interest / 1200) * Math.pow(1 + interest / 1200, tenure)) /
      (Math.pow(1 + interest / 1200, tenure) - 1)
  );

  return (
    <Card className={`relative overflow-hidden transition-all duration-300 hover:shadow-lg ${isRecommended ? 'border-accent shadow-glow' : ''}`}>
      {isRecommended && (
        <div className="absolute top-0 right-0">
          <Badge className="rounded-none rounded-bl-lg bg-accent text-accent-foreground">
            <Sparkles className="w-3 h-3 mr-1" />
            Recommended
          </Badge>
        </div>
      )}
      <CardHeader className="pb-3">
        <div className="text-center">
          <p className="text-sm text-muted-foreground mb-1">Loan Amount</p>
          <p className="text-3xl font-bold font-display text-foreground">
            ₹{amount.toLocaleString('en-IN')}
          </p>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Interest Rate</span>
          <span className="font-semibold text-foreground">{interest.toFixed(1)}% p.a.</span>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Tenure</span>
            <span className="font-semibold text-foreground">{tenure} months</span>
          </div>
          <Slider
            value={[tenure]}
            onValueChange={(val) => setTenure(val[0])}
            min={minTenure}
            max={maxTenure}
            step={1}
            className="w-full"
          />
        </div>

        <div className="bg-secondary/50 rounded-xl p-4 text-center">
          <p className="text-xs text-muted-foreground mb-1">Monthly EMI</p>
          <p className="text-2xl font-bold text-accent">
            ₹{emi.toLocaleString('en-IN')}
          </p>
        </div>

        <Button 
          variant={isRecommended ? "accent" : "default"}
          className="w-full"
          onClick={() => onSelect(interest, tenure)}
        >
          <Check className="w-4 h-4 mr-2" />
          Select This Plan
        </Button>
      </CardContent>
    </Card>
  );
};
