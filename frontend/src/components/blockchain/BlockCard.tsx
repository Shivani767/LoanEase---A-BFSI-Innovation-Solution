import React from "react";
import { cn } from "@/lib/utils";
import { ArrowRight, Clock, Hash, ShieldCheck, Box } from "lucide-react";

interface BlockData {
  index: number;
  timestamp: string;
  transaction_data: any;
  previous_hash: string;
  hash: string;
  merkle_root: string;
  nonce: number;
  block_type?: string;
  transaction_count?: number;
}

interface BlockCardProps {
  block: BlockData;
  isValid: boolean;
  onDetailsClick: (block: BlockData) => void;
  isLast?: boolean;
}

export const BlockCard = ({ block, isValid, onDetailsClick, isLast }: BlockCardProps) => {
  const isGenesis = block.index === 0;

  return (
    <div className="flex items-center">
      <div 
        className={cn(
          "w-72 flex-shrink-0 p-5 rounded-2xl border-2 transition-all duration-500 relative group overflow-hidden",
          isValid 
            ? "bg-[hsl(0,0%,7%)] border-[hsl(0,0%,15%)] hover:border-[hsl(47,100%,50%)]/40" 
            : "bg-red-500/5 border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.2)]"
        )}
      >
        {/* Background Accent */}
        <div className={cn(
          "absolute -right-4 -top-4 w-24 h-24 opacity-10 blur-2xl rounded-full -z-10",
          isValid ? "bg-[hsl(47,100%,50%)]" : "bg-red-500"
        )} />

        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center gap-2">
            <div className={cn(
              "p-1.5 rounded-lg",
              isValid ? "bg-[hsl(47,100%,50%)]/10 text-[hsl(47,100%,50%)]" : "bg-red-500/10 text-red-500"
            )}>
              <Box size={16} />
            </div>
            <span className="text-sm font-bold text-white uppercase tracking-widest">
              Block #{block.index}
            </span>
          </div>
          <span className={cn(
            "text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-tighter",
            isGenesis ? "bg-blue-500/20 text-blue-400" : 
            block.block_type === "SANCTION" ? "bg-green-500/20 text-green-400" : 
            "bg-purple-500/20 text-purple-400"
          )}>
            {block.block_type || (isGenesis ? "GENESIS" : "TRANSACTION")}
          </span>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-[9px] text-[hsl(0,0%,40%)] uppercase tracking-widest font-bold flex items-center gap-1 mb-1">
              <Hash size={10} /> Hash
            </label>
            <div className="font-mono text-[11px] break-all">
              <span className="text-[hsl(47,100%,50%)] font-bold">{block.hash.slice(0, 3)}</span>
              <span className="text-[hsl(0,0%,70%)]">{block.hash.slice(3, 16)}...</span>
            </div>
          </div>

          {!isGenesis && (
            <div>
              <label className="text-[9px] text-[hsl(0,0%,40%)] uppercase tracking-widest font-bold mb-1 block">
                Previous Hash
              </label>
              <div className="font-mono text-[11px] text-[hsl(0,0%,50%)] break-all">
                {block.previous_hash.slice(0, 3)}...{block.previous_hash.slice(-8)}
              </div>
            </div>
          )}

          <div className="flex justify-between items-center pt-2">
            <div>
              <label className="text-[9px] text-[hsl(0,0%,40%)] uppercase tracking-widest font-bold mb-1 block">
                Nonce
              </label>
              <span className="text-xs text-white font-mono">{block.nonce}</span>
            </div>
            <button 
              onClick={() => onDetailsClick(block)}
              className="px-3 py-1 bg-white/5 hover:bg-white/10 border border-white/10 rounded-md text-[10px] text-white font-bold uppercase tracking-widest transition-colors"
            >
              Details
            </button>
          </div>
        </div>
      </div>

      {!isLast && (
        <div className="mx-4 flex flex-col items-center">
          <ArrowRight className={cn(
            "w-8 h-8 transition-colors duration-500",
            isValid ? "text-[hsl(0,0%,20%)]" : "text-red-500"
          )} />
          <span className={cn(
            "text-[9px] font-bold uppercase mt-1",
            isValid ? "text-[hsl(0,0%,30%)]" : "text-red-500"
          )}>
            {isValid ? "Valid Link" : "Broken Link"}
          </span>
        </div>
      )}
    </div>
  );
};
