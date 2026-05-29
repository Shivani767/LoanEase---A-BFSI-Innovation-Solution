import { useState } from "react";
import { Button } from "./ui/button";
import { formatIndianRupees } from "@/lib/languageUtils";
import { Check, Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface Offer {
  id: string;
  name: string;
  amount: number;
  rate: number;
  tenure: number;
  emi: number;
  total: string;
  isRecommended?: boolean;
}

export type { Offer };

interface LoanComparisonCardsProps {
  offers: Offer[];
  onSelect: (offer: Offer) => void;
}

export const LoanComparisonCards = ({ offers, onSelect }: LoanComparisonCardsProps) => {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleSelect = (offer: Offer) => {
    setSelectedId(offer.id);
    setTimeout(() => {
      onSelect(offer);
    }, 300);
  };

  return (
    <div className="space-y-4 animate-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col gap-4 overflow-x-visible py-2 md:flex-row md:items-stretch">
        {offers.map((offer, index) => {
          const isSelected = selectedId === offer.id;
          const isFaded = selectedId !== null && !isSelected;
          const totalPayable = offer.emi * offer.tenure;
          const totalInterest = totalPayable - offer.amount;
          const principalPct = Math.max(0, Math.min(100, (offer.amount / totalPayable) * 100));
          const interestPct = Math.max(0, 100 - principalPct);
          
          return (
            <div
              key={offer.id}
              className={cn(
                "group relative flex min-w-[280px] flex-1 flex-col overflow-visible rounded-2xl border bg-card p-6 transition-all duration-300 animate-slide-up fill-mode-both hover:-translate-y-1 hover:shadow-[0_8px_24px_rgba(0,0,0,0.4)]",
                offer.isRecommended ? "order-first md:order-none" : "",
                offer.isRecommended && !selectedId
                  ? "z-10 border-2 border-[#F5C518] shadow-[0_0_20px_rgba(245,197,24,0.18)] md:-translate-y-2"
                  : "border-[#2a2a2a] hover:border-white/20",
                isSelected && "border-2 border-[#F5C518] bg-[#F5C518]/5 shadow-[0_0_24px_rgba(245,197,24,0.18)]",
                isFaded && "pointer-events-none opacity-35"
              )}
              style={{ animationDelay: `${index * 150}ms` }}
            >
              {offer.isRecommended && !isSelected && (
                <div className="absolute -top-3 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full bg-[#F5C518] px-3 py-1 text-[10px] font-black uppercase tracking-[0.28em] text-black shadow-lg">
                  <Star className="h-3 w-3 fill-black" /> Recommended
                </div>
              )}
              
              {isSelected && (
                <div className="absolute -top-3 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full bg-[#F5C518] px-3 py-1 text-[10px] font-black uppercase tracking-[0.28em] text-black shadow-lg">
                  <Check className="h-3 w-3" /> Selected
                </div>
              )}

              <div className="flex flex-1 flex-col space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-lg font-bold uppercase tracking-[0.24em] text-slate-100">{offer.name}</h4>
                    <p className="mt-1 text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">{offer.tenure} mo.</p>
                  </div>
                  <p className="text-right text-2xl font-black text-[#F5C518]">{formatIndianRupees(offer.amount)}</p>
                </div>

                <div className="space-y-3 border-y border-[#2a2a2a] py-4 text-sm">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-400">Interest Rate</span>
                    <span className="font-semibold text-slate-100">{offer.rate}% p.a.</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-400">Monthly EMI</span>
                    <span className="text-xl font-bold text-[#F5C518]">{formatIndianRupees(offer.emi)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-400">Total Payable</span>
                    <span className="font-semibold text-slate-100">{formatIndianRupees(totalPayable)}</span>
                  </div>
                  <div className="group/interest relative flex items-center justify-between gap-4 pt-1 text-xs text-slate-400">
                    <span>Total Interest</span>
                    <span className="font-semibold text-slate-100">{formatIndianRupees(totalInterest)}</span>
                    <div className="pointer-events-none absolute left-1/2 top-0 z-20 -translate-x-1/2 -translate-y-full opacity-0 transition-opacity duration-200 group-hover/interest:opacity-100">
                      <div className="max-w-[210px] rounded-lg border border-[#2a2a2a] bg-[#111111] px-3 py-2 text-[11px] text-slate-300 shadow-xl">
                        This is how much you pay to the bank above your principal amount
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                    <span>Principal</span>
                    <span>Interest</span>
                  </div>
                  <div className="flex h-3 overflow-hidden rounded-full bg-[#2a2a2a]">
                    <div
                      className="h-full bg-[#8a6a00] transition-all duration-700"
                      style={{ width: `${principalPct}%` }}
                    />
                    <div
                      className="h-full bg-[#4b5563] transition-all duration-700"
                      style={{ width: `${interestPct}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>{formatIndianRupees(offer.amount)}</span>
                    <span>{formatIndianRupees(totalInterest)}</span>
                  </div>
                </div>

                <Button
                  onClick={() => handleSelect(offer)}
                  disabled={selectedId !== null}
                  className={cn(
                    "mt-auto w-full font-bold transition-all duration-200",
                    isSelected
                      ? "bg-[#F5C518] text-black hover:bg-[#e6b800]"
                      : offer.isRecommended
                        ? "bg-[#F5C518] text-black shadow-lg shadow-[#F5C518]/20 hover:bg-[#e6b800]"
                        : "border border-[#2a2a2a] bg-transparent text-slate-100 hover:bg-white/5"
                  )}
                >
                  {isSelected ? "Selected ✓" : offer.isRecommended ? "Select ⭐" : "Select"}
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
