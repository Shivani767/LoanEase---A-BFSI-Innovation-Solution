import { useCallback, useRef, useState } from "react";

export type LoanStage = "kyc" | "credit" | "negotiate" | "sanction" | "complete";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  quickReplies?: QuickReply[];
};

export type XaiTrace = {
  stage: LoanStage;
  decision?: string;
  credit_score?: number;
  primary_driver?: string;
  counterfactual?: string;
  [key: string]: unknown;
};

export type QuickReply = {
  label: string;
  value: string;
};

type SseEventPayload = {
  type?: string;
  content?: string;
  trace?: unknown;
  session_id?: string;
  stage?: string;
  message?: string;
  quick_replies?: QuickReply[];
  meta?: Record<string, unknown>;
};

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const toLoanStage = (value: string | undefined): LoanStage => {
  const normalized = (value ?? "").toLowerCase().trim();
  if (normalized === "kyc") return "kyc";
  if (normalized === "credit") return "credit";
  if (normalized === "negotiate" || normalized === "negotiation") return "negotiate";
  if (normalized === "sanction") return "sanction";
  if (normalized === "complete") return "complete";
  return "kyc";
};

const createId = (): string => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

const parseSseEventBlocks = (rawBlock: string): SseEventPayload[] => {
  const events: SseEventPayload[] = [];
  const lines = rawBlock
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("data:"));

  for (const line of lines) {
    const dataPart = line.slice(5).trim();
    if (!dataPart) continue;
    try {
      const parsed = JSON.parse(dataPart) as SseEventPayload;
      events.push(parsed);
    } catch {
      // Ignore malformed SSE data lines and continue parsing.
    }
  }

  return events;
};

export const useGroqChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [stage, setStage] = useState<LoanStage>("kyc");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [xaiTraces, setXaiTraces] = useState<XaiTrace[]>([]);
  const [quickReplies, setQuickReplies] = useState<QuickReply[]>([]);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const lastNudgeRef = useRef<string | null>(null);

  const appendToAssistantMessage = useCallback((assistantId: string, token: string) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantId ? { ...msg, content: `${msg.content}${token}` } : msg,
      ),
    );
  }, []);

  const markAssistantFinished = useCallback((assistantId: string) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === assistantId ? { ...msg, isStreaming: false } : msg)),
    );
  }, []);

  const setAssistantError = useCallback((assistantId: string, message: string) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantId
          ? {
              ...msg,
              content: message,
              isStreaming: false,
            }
          : msg,
      ),
    );
  }, []);

  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const next = [...prev];
      const last = next[next.length - 1];
      if (last.role === "assistant" && last.isStreaming) {
        next[next.length - 1] = { ...last, isStreaming: false };
      }
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setMessages([]);
    setIsStreaming(false);
    setStage("kyc");
    setSessionId(null);
    setXaiTraces([]);
    setQuickReplies([]);
    setError(null);
    lastNudgeRef.current = null;
  }, []);

  const overrideStage = useCallback((s: LoanStage) => {
    setStage(s);
  }, []);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/ai/session/${sessionId}/nudge`);
        if (!response.ok) {
          return;
        }

        const data = (await response.json()) as {
          should_nudge?: boolean;
          message?: string;
          quick_replies?: QuickReply[];
          stage?: string;
        };

        if (!data.should_nudge || !data.message) {
          return;
        }

        const signature = `${data.stage ?? stage}:${data.message}`;
        if (lastNudgeRef.current === signature) {
          return;
        }

        lastNudgeRef.current = signature;
        setMessages((prev) => [
          ...prev,
          {
            id: createId(),
            role: "assistant",
            content: data.message ?? "",
            timestamp: new Date(),
            quickReplies: data.quick_replies ?? [],
          },
        ]);
        if (Array.isArray(data.quick_replies) && data.quick_replies.length > 0) {
          setQuickReplies(data.quick_replies);
        }
      } catch {
        // Best-effort nudge polling only.
      }
    };

    poll();
    const intervalId = window.setInterval(poll, 30000);
    return () => window.clearInterval(intervalId);
  }, [sessionId, stage]);

  const sendMessage = useCallback(
    async (userText: string, context: Record<string, unknown> = {}) => {
      const text = userText.trim();
      if (!text) return;

      if (abortRef.current) {
        abortRef.current.abort();
      }

      const controller = new AbortController();
      abortRef.current = controller;

      setError(null);
      setQuickReplies([]);

      const userMessage: ChatMessage = {
        id: createId(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      const assistantId = createId();
      const assistantPlaceholder: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
      setIsStreaming(true);

      try {
        const response = await fetch(`${API_BASE}/ai/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            session_id: sessionId ?? undefined,
            stage,
            context,
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        const headerSessionId = response.headers.get("X-Session-Id");
        if (headerSessionId) {
          setSessionId(headerSessionId);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() ?? "";

          for (const block of blocks) {
            const events = parseSseEventBlocks(block);
            for (const event of events) {
              const eventType = event.type;
              if (eventType === "token") {
                appendToAssistantMessage(assistantId, event.content ?? "");
                continue;
              }

              if (eventType === "xai" && event.trace && typeof event.trace === "object") {
                const trace = event.trace as Record<string, unknown>;
                const suggestions = Array.isArray(trace.quick_replies) ? (trace.quick_replies as QuickReply[]) : [];
                if (suggestions.length > 0) {
                  setQuickReplies(suggestions);
                }
                setXaiTraces((prev) => [
                  ...prev,
                  {
                    stage,
                    ...trace,
                  },
                ]);
                continue;
              }

              if (eventType === "done") {
                const doneSessionId = event.session_id;
                if (doneSessionId) {
                  setSessionId(doneSessionId);
                }
                setStage(toLoanStage(event.stage));
                if (Array.isArray(event.quick_replies)) {
                  setQuickReplies(event.quick_replies as QuickReply[]);
                } else if (event.meta && Array.isArray(event.meta.quick_replies)) {
                  setQuickReplies(event.meta.quick_replies as QuickReply[]);
                }
                markAssistantFinished(assistantId);
                continue;
              }

              if (eventType === "error") {
                const friendlyMessage =
                  "Thoda network ya server issue aa gaya. Please ek baar phir try karein.";
                setAssistantError(assistantId, friendlyMessage);
                setError(event.message ?? "Unknown streaming error");
              }
            }
          }
        }

        // Flush any final buffered SSE chunk after stream end.
        if (buffer.trim().length > 0) {
          const events = parseSseEventBlocks(buffer);
          for (const event of events) {
            if (event.type === "token") {
              appendToAssistantMessage(assistantId, event.content ?? "");
            } else if (event.type === "done") {
              if (event.session_id) {
                setSessionId(event.session_id);
              }
              setStage(toLoanStage(event.stage));
              if (Array.isArray(event.quick_replies)) {
                setQuickReplies(event.quick_replies as QuickReply[]);
              } else if (event.meta && Array.isArray(event.meta.quick_replies)) {
                setQuickReplies(event.meta.quick_replies as QuickReply[]);
              }
              markAssistantFinished(assistantId);
            } else if (event.type === "xai" && event.trace && typeof event.trace === "object") {
              const trace = event.trace as Record<string, unknown>;
              const suggestions = Array.isArray(trace.quick_replies) ? (trace.quick_replies as QuickReply[]) : [];
              if (suggestions.length > 0) {
                setQuickReplies(suggestions);
              }
              setXaiTraces((prev) => [
                ...prev,
                {
                  stage,
                  ...trace,
                },
              ]);
            } else if (event.type === "error") {
              const friendlyMessage =
                "Thoda network ya server issue aa gaya. Please ek baar phir try karein.";
              setAssistantError(assistantId, friendlyMessage);
              setError(event.message ?? "Unknown streaming error");
            }
          }
        }

        markAssistantFinished(assistantId);
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }

        const friendlyMessage =
          "Abhi response nahi aa paya. Kripya thodi der baad dobara try karein.";
        setAssistantError(assistantId, friendlyMessage);
        setError(err instanceof Error ? err.message : "Unknown chat error");
      } finally {
        setIsStreaming(false);
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
      }
    },
    [
      appendToAssistantMessage,
      markAssistantFinished,
      sessionId,
      setAssistantError,
      stage,
    ],
  );

  return {
    messages,
    isStreaming,
    stage,
    sessionId,
    xaiTraces,
    error,
    quickReplies,
    sendMessage,
    cancelStream,
    reset,
    overrideStage,
  };
};

