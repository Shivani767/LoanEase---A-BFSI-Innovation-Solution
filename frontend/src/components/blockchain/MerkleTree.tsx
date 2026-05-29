import React from "react";
import { cn } from "@/lib/utils";

interface MerkleNode {
  hash: string;
  type: "root" | "intermediate" | "leaf";
  label?: string;
  data?: any;
}

interface MerkleTreeProps {
  treeData: {
    root: string;
    levels: string[][];
    transactions: any[];
  };
  blockIndex: number;
}

export const MerkleTree = ({ treeData, blockIndex }: MerkleTreeProps) => {
  if (!treeData || !treeData.levels) return null;

  const { levels, transactions } = treeData;
  const reversedLevels = [...levels].reverse(); // Root at top

  return (
    <div className="mt-8 p-6 bg-[hsl(0,0%,7%)] border border-[hsl(0,0%,15%)] rounded-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <span className="text-2xl">🌳</span> Merkle Tree — Block #{blockIndex}
          </h3>
          <p className="text-xs text-muted-foreground mt-1 uppercase tracking-widest font-mono">
            Cryptographic Integrity Proof
          </p>
        </div>
        <div className="px-3 py-1 bg-[hsl(47,100%,50%)]/10 border border-[hsl(47,100%,50%)]/20 rounded-full">
          <span className="text-[10px] font-bold text-[hsl(47,100%,50%)] uppercase tracking-tighter">
            Root: {treeData.root.slice(0, 12)}...
          </span>
        </div>
      </div>

      <div className="relative flex flex-col items-center gap-12 py-4 overflow-x-auto min-h-[400px]">
        {reversedLevels.map((level, levelIdx) => (
          <div key={levelIdx} className="flex gap-8 items-center justify-center min-w-max px-8">
            {level.map((hash, nodeIdx) => {
              const isRoot = levelIdx === 0;
              const isLeaf = levelIdx === reversedLevels.length - 1;
              const tx = isLeaf ? transactions[nodeIdx] : null;

              return (
                <div key={nodeIdx} className="relative group">
                  {/* Connectors to children */}
                  {!isLeaf && (
                    <div className="absolute top-full left-1/2 -translate-x-1/2 h-12 w-px bg-[hsl(0,0%,20%)] -z-10" />
                  )}
                  
                  <div
                    className={cn(
                      "w-32 p-3 border rounded-lg transition-all duration-300 flex flex-col items-center justify-center gap-1",
                      isRoot ? "border-[hsl(47,100%,50%)] bg-[hsl(47,100%,50%)]/5 shadow-[0_0_15px_rgba(245,197,24,0.1)]" : 
                      isLeaf ? "border-green-500/30 bg-green-500/5" :
                      "border-[hsl(0,0%,20%)] bg-[hsl(0,0%,10%)]"
                    )}
                  >
                    <span className="text-[9px] uppercase tracking-tighter opacity-50 font-mono">
                      {isRoot ? "Merkle Root" : isLeaf ? `TX #${nodeIdx}` : "Branch Node"}
                    </span>
                    <span className={cn(
                      "font-mono text-[11px] font-bold",
                      isRoot ? "text-[hsl(47,100%,50%)]" : "text-white"
                    )}>
                      {hash.slice(0, 8)}...
                    </span>
                    {isLeaf && tx && (
                      <span className="text-[9px] text-green-400 mt-1 font-medium max-w-full truncate">
                        {tx.type || tx.sanction_reference || "DATA"}
                      </span>
                    )}
                  </div>

                  {/* Tooltip-like details on hover */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-2 bg-black border border-white/10 rounded text-[10px] text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none font-mono">
                    Full Hash: {hash}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <div className="mt-8 pt-6 border-t border-[hsl(0,0%,15%)]">
        <p className="text-xs text-[hsl(0,0%,50%)] italic leading-relaxed text-center max-w-2xl mx-auto">
          "Each transaction is hashed individually. Pairs of hashes are combined and hashed again. 
          The root hash represents ALL transactions. Changing any single transaction changes 
          the root hash, invalidating the block."
        </p>
      </div>
    </div>
  );
};
