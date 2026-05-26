import { useState, useRef } from "react";
import { Smile, Paperclip, Mic, Send } from "lucide-react";

interface WhatsAppInputProps {
  onSendMessage: (message: string, file?: File) => void;
  disabled?: boolean;
}

export const WhatsAppInput = ({ onSendMessage, disabled = false }: WhatsAppInputProps) => {
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
      // Clear the input
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
      // Stop recording
      setIsRecording(false);
      // In a real implementation, this would handle voice recording
      onSendMessage("Voice message (simulated)");
    } else {
      // Start recording
      setIsRecording(true);
      // In a real implementation, this would start voice recording
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        {/* Emoji Button */}
        <button
          type="button"
          className="text-[#8696a0] hover:text-white p-2 rounded-full transition-colors"
          disabled={disabled}
        >
          <Smile size={20} />
        </button>

        {/* Attachment Button */}
        <button
          type="button"
          className="text-[#8696a0] hover:text-white p-2 rounded-full transition-colors"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
        >
          <Paperclip size={20} />
        </button>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept="image/*,.pdf,.doc,.docx"
          onChange={handleFileSelect}
          disabled={disabled}
        />

        {/* Text Input */}
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

        {/* Send/Mic Button */}
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

      {/* Recording Indicator */}
      {isRecording && (
        <div className="absolute bottom-full left-4 right-4 mb-2 bg-red-500 text-white px-3 py-1 rounded-full text-xs flex items-center gap-2">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
          Recording... Tap to stop
        </div>
      )}
    </>
  );
};
