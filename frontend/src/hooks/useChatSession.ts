import { useState, useCallback } from "react";
import { API_BASE_URL } from "@/config";

interface ChatResponse {
  content: string;
  type: string;
  data?: any;
}

export const useChatSession = (sessionId: string, channel: string = 'web') => {
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (message: string, file?: File): Promise<ChatResponse> => {
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('message', message);
      formData.append('session_id', sessionId);
      formData.append('channel', channel);
      
      if (file) {
        formData.append('file', file);
      }

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      return {
        content: data.content || data.message || 'Sorry, I could not process that.',
        type: data.type || 'text',
        data: data.data
      };

    } catch (error) {
      console.error('Chat session error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, channel]);

  return {
    sendMessage,
    isLoading
  };
};
