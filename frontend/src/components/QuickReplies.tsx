import { Button } from "./ui/button";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface QuickReply {
  label: string;
  value: string;
}

interface QuickRepliesProps {
  options: QuickReply[];
  onSelect: (value: string) => void;
}

export const QuickReplies = ({ options, onSelect }: QuickRepliesProps) => {
  const [selectedValue, setSelectedValue] = useState<string | null>(null);
  const [isHidden, setIsHidden] = useState(false);

  const handleSelect = (value: string) => {
    if (selectedValue || isHidden) return;

    setSelectedValue(value);
    setTimeout(() => {
      setIsHidden(true);
      onSelect(value);
    }, 180);
  };

  if (isHidden) {
    return null;
  }

  return (
    <div className={cn(
      "mt-2 flex flex-nowrap gap-2 overflow-x-auto overflow-y-hidden pb-3 pl-[44px] pr-2 scrollbar-hide transition-all duration-300",
      selectedValue && "opacity-0 translate-y-1 pointer-events-none"
    )}>
      {options.map((option) => (
        <Button
          key={option.value}
          variant="outline"
          size="sm"
          onClick={() => handleSelect(option.value)}
          className={cn(
            "shrink-0 rounded-full border-[1.5px] border-[#F5C518] bg-transparent px-4 py-2 text-xs font-semibold tracking-[0.3px] text-[#F5C518] transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#F5C518] hover:text-black active:translate-y-0",
            selectedValue === option.value && "bg-[#F5C518] text-black shadow-[0_0_0_1px_rgba(245,197,24,0.2)]"
          )}
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
};
