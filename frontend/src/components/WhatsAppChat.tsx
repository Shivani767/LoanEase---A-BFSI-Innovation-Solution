import { useState, useEffect, useRef } from "react";
import { Smile, Paperclip, Mic, Send, FileText, CheckCircle, HelpCircle, Check, CheckCheck } from "lucide-react";
import { ENDPOINTS } from "@/config";

interface Message {
  id: string;
  content: string;
  type: 'user' | 'assistant';
  timestamp: Date;
  status?: 'sent' | 'delivered' | 'read';
  attachment?: {
    name: string;
    type: string;
  };
}

// Simplified Message Component
const SimpleMessage = ({ message }: { message: Message }) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-IN', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'sent':
        return <Check className="w-4 h-4" />;
      case 'delivered':
        return <CheckCheck className="w-4 h-4" />;
      case 'read':
        return <CheckCheck className="w-4 h-4 text-blue-400" />;
      default:
        return null;
    }
  };

  const isUser = message.type === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2`}>
      <div className={`max-w-[70%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Message Bubble */}
        <div
          className={`
            relative px-4 py-2 rounded-2xl
            ${isUser 
              ? 'bg-[#005c4b] text-white rounded-tr-none' 
              : 'bg-[#1f2c34] text-white rounded-tl-none'
            }
          `}
        >
          {/* Attachment */}
          {message.attachment && (
            <div className="flex items-center gap-2 mb-1 pb-2 border-b border-white/20">
              <div className="w-8 h-8 bg-white/20 rounded flex items-center justify-center">
                <Paperclip className="w-4 h-4 text-white" />
              </div>
              <span className="text-sm">{message.attachment.name}</span>
            </div>
          )}
          
          {/* Message Content */}
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </p>
          
          {/* Tail */}
          <div
            className={`
              absolute w-0 h-0
              ${isUser 
                ? 'right-0 top-0 border-l-[8px] border-l-[#005c4b] border-t-[6px] border-t-transparent' 
                : 'left-0 top-0 border-r-[8px] border-r-[#1f2c34] border-t-[6px] border-t-transparent'
              }
            `}
          />
        </div>
        
        {/* Timestamp and Status */}
        <div className={`flex items-center gap-1 mt-1 text-xs text-[#8696a0] ${isUser ? 'justify-end' : 'justify-start'}`}>
          <span>{formatTime(message.timestamp)}</span>
          {isUser && getStatusIcon(message.status)}
        </div>
      </div>
    </div>
  );
};

// Simplified Input Component
const SimpleInput = ({ onSendMessage, disabled }: { onSendMessage: (message: string, file?: File) => void, disabled?: boolean }) => {
  const [message, setMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && !disabled) {
      onSendMessage("", file);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleMicClick = () => {
    if (disabled) return;
    
    if (isRecording) {
      setIsRecording(false);
      onSendMessage("Voice message (simulated)");
    } else {
      setIsRecording(true);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <button
          type="button"
          className="text-[#8696a0] hover:text-white p-2 rounded-full transition-colors"
          disabled={disabled}
        >
          <Smile size={20} />
        </button>

        <button
          type="button"
          className="text-[#8696a0] hover:text-white p-2 rounded-full transition-colors"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
        >
          <Paperclip size={20} />
        </button>

        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept="image/*,.pdf,.doc,.docx"
          onChange={handleFileSelect}
          disabled={disabled}
        />

        <div className="flex-1 relative">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message"
            className="w-full bg-[#2a3942] text-white placeholder-[#8696a0] rounded-full px-4 py-2 pr-12 focus:outline-none focus:ring-1 focus:ring-[#00a884] disabled:opacity-50"
            disabled={disabled}
          />
        </div>

        <button
          type={message.trim() ? "submit" : "button"}
          onClick={!message.trim() ? handleMicClick : undefined}
          className={`
            p-2 rounded-full transition-all
            ${message.trim() 
              ? 'bg-[#00a884] text-white hover:bg-[#008069]' 
              : isRecording 
                ? 'bg-red-500 text-white animate-pulse' 
                : 'text-[#8696a0] hover:text-white'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
          disabled={disabled}
        >
          {message.trim() ? (
            <Send size={20} />
          ) : (
            <Mic size={20} />
          )}
        </button>
      </form>

      {isRecording && (
        <div className="absolute bottom-full left-4 right-4 mb-2 bg-red-500 text-white px-3 py-1 rounded-full text-xs flex items-center gap-2">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
          Recording... Tap to stop
        </div>
      )}
    </>
  );
};

export const WhatsAppChat = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: 'Hello! I\'m your LoanEase assistant. How can I help you today?\n\nReply:\n[File] Apply for Loan\n[Check] Check Eligibility\n[Help] How it works',
      type: 'assistant',
      timestamp: new Date(),
      status: 'read'
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId] = useState(() => `WA-${Date.now()}`);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const toAsciiDigits = (value: string) =>
    value.replace(/[०-९]/g, (digit) => ({
      "०": "0",
      "१": "1",
      "२": "2",
      "३": "3",
      "४": "4",
      "५": "5",
      "६": "6",
      "७": "7",
      "८": "8",
      "९": "9",
    }[digit] ?? digit));

  const normalizePan = (value: string) => toAsciiDigits(value).replace(/\s+/g, "").toUpperCase();

  const isValidPan = (value: string) => /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(value);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (content: string, attachment?: File) => {
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      type: 'user',
      timestamp: new Date(),
      status: 'sent',
      ...(attachment && {
        attachment: {
          name: attachment.name,
          type: attachment.type
        }
      })
    };

    setMessages(prev => [...prev, userMessage]);

    // Show typing indicator
    setIsTyping(true);

    try {
      if (attachment) {
        const formData = new FormData();
        formData.append("document", attachment);
        formData.append("session_id", sessionId);
        formData.append("language", "en");

        const panResponse = await fetch(ENDPOINTS.kyc_pan, {
          method: "POST",
          body: formData,
        });

        if (panResponse.ok) {
          const panData = await panResponse.json();
          const extractedPanCandidate = normalizePan(panData?.extracted_fields?.pan_number || "");
          const extractedPan = isValidPan(extractedPanCandidate)
            ? extractedPanCandidate
            : (panData?.extracted_fields?.pan_number || "");

          if (extractedPan) {
            const extractedName = panData?.extracted_fields?.name || "";
            const extractedDob = panData?.extracted_fields?.date_of_birth || "";
            const ocrMessage: Message = {
              id: (Date.now() + 2).toString(),
              content: `PAN OCR detected:\nPAN: ${extractedPan}${extractedName ? `\nName: ${extractedName}` : ""}${extractedDob ? `\nDOB: ${extractedDob}` : ""}`,
              type: 'assistant',
              timestamp: new Date(),
              status: 'delivered'
            };
            setMessages(prev => [...prev, ocrMessage]);
          }
        }
      }

      // Send to backend with channel parameter
      const formData = new FormData();
      formData.append('message', content);
      formData.append('session_id', sessionId);
      formData.append('channel', 'whatsapp');
      
      if (attachment) {
        formData.append('file', attachment);
      }

      const response = await fetch(`http://localhost:8000/chat`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.content || data.message || 'Sorry, I could not process that.',
        type: 'assistant',
        timestamp: new Date(),
        status: 'delivered'
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Update user message status to delivered then read
      setTimeout(() => {
        setMessages(prev => prev.map(msg => 
          msg.id === userMessage.id ? { ...msg, status: 'delivered' } : msg
        ));
      }, 500);

      setTimeout(() => {
        setMessages(prev => prev.map(msg => 
          msg.id === userMessage.id ? { ...msg, status: 'read' } : msg
        ));
      }, 1000);

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I had trouble processing that. Please try again.',
        type: 'assistant',
        timestamp: new Date(),
        status: 'delivered'
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
        {messages.map((message) => (
          <SimpleMessage
            key={message.id}
            message={message}
          />
        ))}
        
        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex items-start gap-2">
            <div className="bg-[#1f2c34] rounded-2xl rounded-tl-none px-4 py-2 max-w-[70%]">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-[#8696a0] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-[#8696a0] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-[#8696a0] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-[#2a3942] px-4 py-2">
        <SimpleInput
          onSendMessage={handleSendMessage}
          disabled={isTyping}
        />
      </div>
    </div>
  );
};
