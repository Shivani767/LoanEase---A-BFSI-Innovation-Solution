import { cn } from "@/lib/utils";
import { Check, CircleDot } from "lucide-react";

interface Step {
  id: string;
  label: string;
}

interface StepIndicatorProps {
  steps: Step[];
  currentStep: number;
}

export const StepIndicator = ({ steps, currentStep }: StepIndicatorProps) => {
  return (
    <div className="flex items-center justify-center gap-2 py-4 px-6 bg-card/80 backdrop-blur-sm border-b border-border">
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300",
                index < currentStep
                  ? "bg-success text-success-foreground"
                  : index === currentStep
                  ? "bg-accent text-accent-foreground animate-pulse-soft"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {index < currentStep ? (
                <Check className="w-4 h-4" />
              ) : index === currentStep ? (
                <CircleDot className="w-4 h-4" />
              ) : (
                index + 1
              )}
            </div>
            <span
              className={cn(
                "text-xs font-medium hidden sm:block transition-colors",
                index <= currentStep ? "text-foreground" : "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={cn(
                "w-8 h-0.5 mx-2 transition-colors duration-300",
                index < currentStep ? "bg-success" : "bg-border"
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
};
