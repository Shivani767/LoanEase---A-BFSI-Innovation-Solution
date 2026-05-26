import { Check, CheckCheck, Paperclip } from "lucide-react";

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

interface WhatsAppMessageProps {
  message: Message;
}

export const WhatsAppMessage = ({ message }: WhatsAppMessageProps) => {
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
                <Paperclip className="w-4 h-4" />
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
