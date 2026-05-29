import { cn } from "@/lib/utils";
import { Bot, Check, CheckCheck } from "lucide-react";

interface ChatMessageProps {
  message: string;
  isBot: boolean;
  isTyping?: boolean;
  status?: "sent" | "delivered" | "responded";
  variant?: "normal" | "system";
}

export const ChatMessage = ({
  message,
  isBot,
  isTyping,
  status = "responded",
  variant = "normal",
}: ChatMessageProps) => {
  const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  if (variant === "system") {
    return (
      <div className="flex w-full animate-slide-up justify-start">
        <div className="max-w-[60%] rounded-xl border border-[#2a2a2a] border-l-[3px] border-l-[#F5C518] bg-[#111111] px-4 py-2.5 text-xs italic text-slate-400 shadow-sm">
          <p className="whitespace-pre-wrap leading-relaxed">{message}</p>
          <span className="mt-1 block text-[10px] not-italic text-slate-500">{timestamp}</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex w-full gap-2 animate-slide-up",
        isBot ? "justify-start" : "justify-end"
      )}
    >
      {isBot && (
        <div className="z-10 mb-1 mt-auto flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border-2 border-background bg-[#F5C518] shadow-[0_4px_12px_rgba(245,197,24,0.2)]">
          <Bot className="w-4 h-4 text-black" />
        </div>
      )}
      
      <div className={cn(
        "relative flex max-w-[85%] flex-col group",
        isBot ? "items-start" : "items-end"
      )}>
        <div
          className={cn(
            "relative px-4 py-3 text-sm shadow-lg transition-all duration-200",
            isBot
              ? "rounded-[18px] rounded-bl-[4px] border border-[#2a2a2a] bg-[#1e1e1e] text-white"
              : "rounded-[18px] rounded-br-[4px] bg-[#F5C518] text-black shadow-[0_2px_8px_rgba(245,197,24,0.2)]"
          )}
        >
          {isTyping ? (
            <div className="typing-indicator">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          ) : (
            <p className="whitespace-pre-wrap leading-relaxed">{message}</p>
          )}

          {!isTyping && (
            <div className={cn(
              "mt-1 flex items-center gap-1 text-[10px] leading-none",
              isBot ? "justify-start text-slate-500" : "justify-end text-slate-500"
            )}>
              <span>{timestamp}</span>
              {!isBot && (
                <div className="-mr-1 flex">
                  {status === "sent" && <Check className="w-3.5 h-3.5 text-slate-500" />}
                  {status === "delivered" && <CheckCheck className="w-3.5 h-3.5 text-slate-500" />}
                  {status === "responded" && <CheckCheck className="w-3.5 h-3.5 text-[#F5C518]" />}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
