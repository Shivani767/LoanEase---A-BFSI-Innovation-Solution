import { useState } from "react";
import { Button } from "@/components/ui/button";
import { MessageCircle, Smartphone, MessageSquare } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface ChannelSelectorProps {
  onWebChat: () => void;
}

export const ChannelSelector = ({ onWebChat }: ChannelSelectorProps) => {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleWebChat = () => {
    setSelectedChannel('web');
    setTimeout(() => {
      onWebChat();
    }, 300);
  };

  const handleWhatsApp = () => {
    setSelectedChannel('whatsapp');
    setTimeout(() => {
      navigate('/whatsapp');
    }, 300);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-semibold text-foreground mb-2">
          Choose your preferred channel:
        </h2>
        <p className="text-muted-foreground">
          Get the same great service on your preferred platform
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto">
        {/* Web Chat Option */}
        <div
          className={`relative p-6 rounded-2xl border-2 transition-all duration-300 cursor-pointer
            ${selectedChannel === 'web' 
              ? 'border-accent bg-accent/5 shadow-lg shadow-accent/20' 
              : 'border-border bg-card hover:border-accent/50 hover:shadow-md'
            }`}
          onClick={handleWebChat}
        >
          <div className="text-center space-y-4">
            <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center transition-colors
              ${selectedChannel === 'web' ? 'bg-accent text-accent-foreground' : 'bg-muted text-foreground'}`}
            >
              <MessageCircle className="w-8 h-8" />
            </div>
            
            <div>
              <h3 className="text-xl font-semibold text-foreground mb-2 flex items-center justify-center gap-2">
                <MessageSquare className="w-5 h-5" />
                Web Chat
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Chat directly on our website
              </p>
            </div>

            <Button 
              variant={selectedChannel === 'web' ? "default" : "outline"}
              className="w-full"
              disabled={selectedChannel !== null && selectedChannel !== 'web'}
            >
              {selectedChannel === 'web' ? 'Opening...' : 'Start Chat'}
            </Button>
          </div>

          {selectedChannel === 'web' && (
            <div className="absolute top-2 right-2">
              <div className="w-2 h-2 bg-accent rounded-full animate-pulse"></div>
            </div>
          )}
        </div>

        {/* WhatsApp Option */}
        <div
          className={`relative p-6 rounded-2xl border-2 transition-all duration-300 cursor-pointer
            ${selectedChannel === 'whatsapp' 
              ? 'border-[#00a884] bg-[#00a884]/5 shadow-lg shadow-[#00a884]/20' 
              : 'border-border bg-card hover:border-[#00a884]/50 hover:shadow-md'
            }`}
          onClick={handleWhatsApp}
        >
          <div className="text-center space-y-4">
            <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center transition-colors
              ${selectedChannel === 'whatsapp' ? 'bg-[#00a884] text-white' : 'bg-muted text-foreground'}`}
            >
              <Smartphone className="w-8 h-8" />
            </div>
            
            <div>
              <h3 className="text-xl font-semibold text-foreground mb-2 flex items-center justify-center gap-2">
                <Smartphone className="w-5 h-5" />
                WhatsApp
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Simulated WhatsApp UI
              </p>
            </div>

            <Button 
              variant={selectedChannel === 'whatsapp' ? "default" : "outline"}
              className="w-full"
              style={selectedChannel === 'whatsapp' ? { 
                backgroundColor: '#00a884', 
                borderColor: '#00a884' 
              } : {}}
              disabled={selectedChannel !== null && selectedChannel !== 'whatsapp'}
            >
              {selectedChannel === 'whatsapp' ? 'Opening...' : 'Open WhatsApp'}
            </Button>
          </div>

          {selectedChannel === 'whatsapp' && (
            <div className="absolute top-2 right-2">
              <div className="w-2 h-2 bg-[#00a884] rounded-full animate-pulse"></div>
            </div>
          )}
        </div>
      </div>

      <div className="text-center">
        <p className="text-xs text-muted-foreground">
          Both channels offer the same AI-powered loan assistance
        </p>
      </div>
    </div>
  );
};
