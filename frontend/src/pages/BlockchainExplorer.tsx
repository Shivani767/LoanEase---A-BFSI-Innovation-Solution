import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Database, Activity, Lock, Layers, Info, X, ExternalLink, ShieldCheck, Link as LinkIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { BlockCard } from "@/components/blockchain/BlockCard";
import { MerkleTree } from "@/components/blockchain/MerkleTree";
import { TamperDemo } from "@/components/blockchain/TamperDemo";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/config";

export default function BlockchainExplorer() {
  // Helper function to format block timestamps
  const formatBlockTime = (timestamp: string | undefined): string => {
    if (!timestamp) return 'Unknown'
    try {
      const d = new Date(timestamp)
      if (isNaN(d.getTime())) {
        // Try parsing as ISO string
        return timestamp.split('T')[0] || 'Invalid Date'
      }
      return d.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      }) + ' ' + d.toLocaleTimeString('en-IN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    } catch {
      return 'Unknown'
    }
  }
  const [data, setData] = useState<any>(null);
  const [selectedBlock, setSelectedBlock] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tamperResult, setTamperResult] = useState<any>(null);
  const [isBroken, setIsBroken] = useState(false);

  const fetchData = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/blockchain/explorer-data`);
      const json = await response.json();
      setData(json);
      if (json.blocks.length > 0 && !selectedBlock) {
        setSelectedBlock(json.blocks[json.blocks.length - 1]);
      }
      setLoading(false);
    } catch (error) {
      console.error("Failed to fetch explorer data", error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTamper = (result: any) => {
    setTamperResult(result);
    setIsBroken(true);
  };

  const handleReset = () => {
    setTamperResult(null);
    setIsBroken(false);
    fetchData();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Activity className="w-12 h-12 text-[hsl(47,100%,50%)] animate-pulse" />
          <p className="text-[hsl(47,100%,50%)] font-mono text-sm tracking-widest uppercase">Initializing Ledger Explorer...</p>
        </div>
      </div>
    );
  }

  const stats = data?.chain_stats || {};
  const blocks = data?.blocks || [];
  const merkleTrees = data?.merkle_trees || {};

  // Find the latest sanction reference for the tamper demo
  const latestSanction = blocks.slice().reverse().find((b: any) => 
    b.block_type === "SANCTION" || 
    (b.transaction_data && (b.transaction_data.type === "SANCTION_LETTER" || b.transaction_data.sanction_reference))
  );
  const sanctionRef = latestSanction?.transaction_data?.sanction_reference || latestSanction?.transaction_data?.transaction_id;

  return (
    <div className="min-h-screen bg-black text-white font-sans selection:bg-[hsl(47,100%,50%)] selection:text-black">
      {/* Header */}
      <header className="border-b border-[hsl(0,0%,15%)] bg-black/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-[1400px] mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="p-2 hover:bg-white/5 rounded-full transition-colors group">
              <ChevronLeft className="group-hover:-translate-x-1 transition-transform" />
            </Link>
            <div>
              <h1 className="text-2xl font-black flex items-center gap-3 uppercase tracking-tighter">
                <span className="text-3xl"><LinkIcon className="w-8 h-8" /></span> LoanEase Audit Ledger
              </h1>
              <p className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-bold">
                Tamper-evident blockchain record of all sanctioned loans
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-widest",
              !isBroken ? "bg-green-500/10 border-green-500/20 text-green-400" : "bg-red-500/10 border-red-500/20 text-red-400"
            )}>
              <div className={cn("w-1.5 h-1.5 rounded-full", !isBroken ? "bg-green-500 animate-pulse" : "bg-red-500")} />
              {isBroken ? "Chain Invalid" : "System Synchronized"}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-6 py-12 space-y-12">
        {/* Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { label: "Total Blocks", value: stats.total_blocks || 0, icon: Database, color: "text-blue-400" },
            { label: "Active Sanctions", value: stats.active_sanctions || 0, icon: Lock, color: "text-[hsl(47,100%,50%)]" },
            { label: "Chain Status", value: stats.chain_valid ? "VERIFIED" : "INVALID", icon: ShieldCheck, color: stats.chain_valid ? "text-green-500" : "text-red-500" },
            { label: "PoW Difficulty", value: `Level ${stats.pow_difficulty || 2}`, icon: Activity, color: "text-purple-400" }
          ].map((stat, i) => (
            <Card key={i} className="bg-[hsl(0,0%,7%)] border-[hsl(0,0%,15%)] hover:border-[hsl(0,0%,25%)] transition-colors">
              <CardContent className="p-6 flex items-center gap-4">
                <div className={cn("p-3 rounded-xl bg-white/5", stat.color)}>
                  <stat.icon size={24} />
                </div>
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">{stat.label}</p>
                  <p className="text-2xl font-black tracking-tight">{stat.value}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Blockchain Visualizer */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Layers className="text-[hsl(47,100%,50%)]" size={24} />
              Immutable Chain Visualization
            </h2>
            <div className="text-[10px] text-muted-foreground uppercase tracking-widest">
              Scroll horizontally to explore
            </div>
          </div>

          <div className="bg-[hsl(0,0%,5%)] border border-[hsl(0,0%,15%)] rounded-3xl p-10 overflow-x-auto custom-scrollbar">
            {blocks.length === 0 ? (
              <div className="flex items-center justify-center h-32 text-gray-400">
                <div className="text-center">
                  <Database className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="text-sm">No blocks yet. Complete a loan to see the chain.</p>
                </div>
              </div>
            ) : (
              <div className="flex min-w-max pb-4">
                {blocks.map((block: any, idx: number) => {
                  // If chain is broken at this index or after
                  const blockValid = !isBroken || idx < (latestSanction?.index || 0);
                  return (
                    <BlockCard 
                      key={idx}
                      block={block}
                      isValid={blockValid}
                      onDetailsClick={setSelectedBlock}
                      isLast={idx === blocks.length - 1}
                    />
                  );
                })}
              </div>
            )}
          </div>
        </section>

        {/* Selected Block Details & Merkle Tree */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Details Sidebar */}
          <div className="lg:col-span-1 space-y-8">
            <Card className="bg-[hsl(0,0%,7%)] border-[hsl(0,0%,15%)] overflow-hidden">
              <div className="bg-[hsl(47,100%,50%)] h-1" />
              <CardContent className="p-8">
                <h3 className="text-lg font-bold mb-6 flex items-center justify-between">
                  Block Details
                  <span className="text-xs font-mono text-muted-foreground">#{selectedBlock?.index}</span>
                </h3>
                
                <div className="space-y-6">
                  {[
                    { label: "Timestamp", value: formatBlockTime(selectedBlock?.timestamp) },
                    { label: "Block Type", value: selectedBlock?.block_type || (selectedBlock?.index === 0 ? "GENESIS" : "TRANSACTION") },
                    { label: "Transactions", value: selectedBlock?.transaction_count || (selectedBlock?.index === 0 ? "3 (Simulated)" : "1") },
                    { label: "Nonce", value: selectedBlock?.nonce || 0 },
                    { label: "Merkle Root", value: (selectedBlock?.merkle_root || "").slice(0, 16) + "..." || "—" },
                  ].map((row, i) => (
                    <div key={i} className="border-b border-white/5 pb-4 last:border-0">
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1">{row.label}</p>
                      <p className="text-sm font-mono text-white">{row.value}</p>
                    </div>
                  ))}
                  
                  <div className="pt-4">
                    <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3">Transaction Content</p>
                    <pre className="bg-black p-4 rounded-xl border border-white/5 text-[10px] text-[hsl(47,100%,50%)] overflow-x-auto">
                      {JSON.stringify(selectedBlock?.transaction_data, null, 2)}
                    </pre>
                  </div>
                </div>
              </CardContent>
            </Card>

            <TamperDemo 
              sanctionReference={sanctionRef}
              onTamper={handleTamper}
              onReset={handleReset}
            />
          </div>

          {/* Merkle Tree Main View */}
          <div className="lg:col-span-2">
            {selectedBlock && (
              <MerkleTree 
                blockIndex={selectedBlock.index}
                treeData={merkleTrees[selectedBlock.index.toString()]}
              />
            )}
            
            {/* Legend/Info */}
            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex gap-4">
                <div className="p-2 bg-[hsl(47,100%,50%)]/10 rounded-lg h-fit">
                  <Info className="text-[hsl(47,100%,50%)]" size={20} />
                </div>
                <div>
                  <h4 className="text-sm font-bold mb-1">How it works</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    This ledger uses SHA-256 hashing and ECDSA signatures. 
                    Each block "seals" the previous one, creating a chain 
                    where tampering is mathematically impossible without 
                    re-calculating every subsequent hash.
                  </p>
                </div>
              </div>
              <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex gap-4">
                <div className="p-2 bg-blue-500/10 rounded-lg h-fit">
                  <ExternalLink className="text-blue-400" size={20} />
                </div>
                <div>
                  <h4 className="text-sm font-bold mb-1">Verify Manually</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    You can verify any sanction letter by entering its 
                    Transaction ID on this page. The system will locate 
                    the block and verify the cryptographic signature.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer Info */}
      <footer className="border-t border-[hsl(0,0%,15%)] py-12 px-6">
        <div className="max-w-[1400px] mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">
            LoanEase Audit Explorer v1.2 • Distributed Ledger Technology
          </p>
          <div className="flex gap-8">
            {["Protocol", "Consensus", "Cryptography", "Nodes"].map(item => (
              <span key={item} className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold hover:text-white cursor-help">
                {item}
              </span>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}

