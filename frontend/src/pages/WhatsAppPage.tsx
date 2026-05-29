import { useEffect, useRef, useState } from "react";
import { ArrowLeft, MoreVertical, Phone, Video, Search, Paperclip, Smile, Mic } from "lucide-react";
import { WhatsAppChat } from "@/components";
import { useNavigate } from "react-router-dom";

const WhatsAppPage = () => {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[#0d1117] relative overflow-hidden">
      {/* WhatsApp Background Pattern */}
      <div 
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: `radial-gradient(circle, #ffffff 1px, transparent 1px)`,
          backgroundSize: '20px 20px'
        }}
      />

      {/* Header */}
      <div className="bg-[#1f2c34] px-4 py-3 flex items-center justify-between relative z-10">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate('/')}
            className="text-white hover:bg-white/10 p-2 rounded-full transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          
          <div className="w-10 h-10 bg-[#00a884] rounded-full flex items-center justify-center">
            <span className="text-white font-bold text-lg">₹</span>
          </div>
          
          <div className="flex-1">
            <h1 className="text-white font-semibold">LoanEase Loan Assistant</h1>
            <p className="text-[#8696a0] text-xs">online</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="text-white hover:bg-white/10 p-2 rounded-full transition-colors">
            <Video size={20} />
          </button>
          <button className="text-white hover:bg-white/10 p-2 rounded-full transition-colors">
            <Phone size={20} />
          </button>
          <button className="text-white hover:bg-white/10 p-2 rounded-full transition-colors">
            <MoreVertical size={20} />
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto relative z-10">
        <WhatsAppChat />
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default WhatsAppPage;
