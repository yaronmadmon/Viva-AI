"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useGuidanceNext } from "@/hooks/use-guidance";
import { useAvatarChat, useAvatarHistory, avatarSpeak } from "@/hooks/use-avatar-chat";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** Default teaching tips when not in a project or guidance unavailable */
const DEFAULT_TIPS = [
  "I\u2019m here to challenge your thinking and help you reach doctoral level.",
  "Add artifacts and link claims to evidence \u2014 I\u2019ll question your reasoning.",
  "Use Guidance to see what to do next. Mastery unlocks AI help when you\u2019re ready.",
];

/** Human-readable mode labels */
const MODE_LABELS: Record<string, string> = {
  PROBE: "Questioning",
  HINT: "Hinting",
  EXPLAIN: "Explaining",
  EXAMINER: "Examining",
  REFLECTION: "Reflecting",
};

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  teachingMode?: string;
}

export function TeachingAvatar({
  message,
  projectId,
  className,
}: {
  message?: string;
  projectId?: string | null;
  className?: string;
}) {
  const [tipIndex, setTipIndex] = useState(0);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [voiceEnabled, setVoiceEnabled] = useState(false); // opt-in, not opt-out
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentMode, setCurrentMode] = useState<string>("PROBE");
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioBlobUrl = useRef<string | null>(null);

  const { data: guidance, isLoading: guidanceLoading } = useGuidanceNext(
    projectId ?? null
  );
  const chatMutation = useAvatarChat(projectId ?? null);
  const { data: historyData } = useAvatarHistory(
    chatOpen ? (projectId ?? null) : null
  );

  const contextualMessage =
    projectId && guidance?.rules?.length
      ? guidance.rules[0].message
      : undefined;
  const nextCta =
    projectId && guidance?.rules?.length ? guidance.rules[0].cta : undefined;

  const displayMessage =
    message ?? contextualMessage ?? DEFAULT_TIPS[tipIndex % DEFAULT_TIPS.length];

  const cycleTip = () => {
    if (!chatOpen) setTipIndex((i) => i + 1);
  };

  // ── Load history when chat opens ────────────────────────────────────

  useEffect(() => {
    if (chatOpen && historyData && !historyLoaded) {
      const loaded: ChatMessage[] = historyData.messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({
          role: m.role as "user" | "assistant",
          text: m.text,
          teachingMode: m.teaching_mode ?? undefined,
        }));
      if (loaded.length > 0) {
        setChatHistory(loaded);
        // Set current mode from last assistant message
        const lastAssistant = [...loaded].reverse().find((m) => m.role === "assistant");
        if (lastAssistant?.teachingMode) {
          setCurrentMode(lastAssistant.teachingMode);
        }
      }
      setHistoryLoaded(true);
    }
  }, [chatOpen, historyData, historyLoaded]);

  // Reset history loaded flag when project changes
  useEffect(() => {
    setHistoryLoaded(false);
    setChatHistory([]);
  }, [projectId]);

  // ── Voice output (OpenAI TTS) ───────────────────────────────────────

  const speak = useCallback(
    async (text: string) => {
      if (!voiceEnabled || !projectId) return;

      try {
        // Clean up previous blob URL
        if (audioBlobUrl.current) {
          URL.revokeObjectURL(audioBlobUrl.current);
          audioBlobUrl.current = null;
        }

        const blobUrl = await avatarSpeak(projectId, text);
        audioBlobUrl.current = blobUrl;

        const audio = new Audio(blobUrl);
        audioRef.current = audio;

        audio.onplay = () => setIsSpeaking(true);
        audio.onended = () => {
          setIsSpeaking(false);
          // Clean up blob URL after playback
          if (audioBlobUrl.current) {
            URL.revokeObjectURL(audioBlobUrl.current);
            audioBlobUrl.current = null;
          }
        };
        audio.onerror = () => {
          setIsSpeaking(false);
          if (audioBlobUrl.current) {
            URL.revokeObjectURL(audioBlobUrl.current);
            audioBlobUrl.current = null;
          }
        };

        await audio.play();
      } catch (err) {
        console.warn("TTS playback failed:", err);
        setIsSpeaking(false);
      }
    },
    [voiceEnabled, projectId]
  );

  const stopSpeaking = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    if (audioBlobUrl.current) {
      URL.revokeObjectURL(audioBlobUrl.current);
      audioBlobUrl.current = null;
    }
    setIsSpeaking(false);
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (audioBlobUrl.current) {
        URL.revokeObjectURL(audioBlobUrl.current);
      }
    };
  }, []);

  // Scroll chat to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Focus input when chat opens
  useEffect(() => {
    if (chatOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [chatOpen]);

  // ── Send message ──────────────────────────────────────────────────────

  const sendMessage = async () => {
    const trimmed = chatInput.trim();
    if (!trimmed) return;
    if (!projectId) return;

    const userMsg: ChatMessage = { role: "user", text: trimmed };
    setChatHistory((prev) => [...prev, userMsg]);
    setChatInput("");

    try {
      const res = await chatMutation.mutateAsync(trimmed);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        text: res.reply,
        teachingMode: res.teaching_mode,
      };
      setChatHistory((prev) => [...prev, assistantMsg]);
      setCurrentMode(res.teaching_mode || "PROBE");
      speak(res.reply);
    } catch {
      const errMsg: ChatMessage = {
        role: "assistant",
        text: "Sorry, I couldn\u2019t respond right now. Please try again.",
      };
      setChatHistory((prev) => [...prev, errMsg]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 rounded-xl border bg-background p-3 shadow-sm transition-all",
        chatOpen && "gap-3",
        className
      )}
      role="complementary"
      aria-label="Teaching guide"
    >
      {/* Avatar icon + label */}
      <button
        type="button"
        onClick={() => {
          if (chatOpen) {
            cycleTip();
          } else {
            setChatOpen(true);
          }
        }}
        className="focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-full"
        aria-label={chatOpen ? "Cycle tip" : "Open chat"}
      >
        <span
          className={cn(
            "relative flex items-center justify-center rounded-full bg-primary/10 text-primary ring-2 ring-primary/20 transition-all",
            chatOpen ? "h-10 w-10" : "h-14 w-14",
            isSpeaking && "ring-primary animate-pulse"
          )}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 48 48"
            className={cn(chatOpen ? "h-5 w-5" : "h-8 w-8")}
            aria-hidden
          >
            <circle cx="24" cy="16" r="8" fill="currentColor" opacity={0.9} />
            <path
              d="M14 28c0-4 4.5-8 10-8s10 4 10 8v4H14v-4z"
              fill="currentColor"
              opacity={0.9}
            />
            <rect
              x="20"
              y="22"
              width="12"
              height="14"
              rx="1"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              opacity={0.8}
            />
            <line
              x1="26"
              y1="22"
              x2="26"
              y2="36"
              stroke="currentColor"
              strokeWidth="1"
              opacity={0.6}
            />
            <path
              d="M12 14l12-4 12 4v2l-12 2-12-2v-2z"
              fill="currentColor"
              opacity={0.7}
            />
          </svg>
        </span>
      </button>

      <div className="flex items-center gap-1.5">
        <p className="text-xs font-medium text-muted-foreground text-center">
          Your guide
        </p>
        {chatOpen && (
          <button
            type="button"
            onClick={() => {
              setChatOpen(false);
              stopSpeaking();
            }}
            className="text-muted-foreground hover:text-foreground text-xs ml-1"
            aria-label="Close chat"
          >
            &times;
          </button>
        )}
      </div>

      {/* Guidance CTA (when chat is closed) */}
      {!chatOpen && nextCta && !message && (
        <p className="text-xs text-muted-foreground text-center">
          Next: {nextCta}
        </p>
      )}

      {/* Static message bubble (when chat is closed) */}
      {!chatOpen && (
        <div className="w-full rounded-lg bg-muted/80 px-2.5 py-2 text-left">
          {guidanceLoading && !contextualMessage && !message ? (
            <p className="text-xs text-muted-foreground">Loading...</p>
          ) : (
            <p className="text-xs text-foreground leading-snug">
              {displayMessage}
            </p>
          )}
        </div>
      )}

      {/* Chat panel (when open) */}
      {chatOpen && (
        <div className="flex w-full flex-col gap-2">
          {/* Teaching mode indicator */}
          {currentMode && chatHistory.length > 0 && (
            <div className="flex items-center justify-center">
              <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    currentMode === "PROBE" && "bg-blue-500",
                    currentMode === "HINT" && "bg-amber-500",
                    currentMode === "EXPLAIN" && "bg-green-500",
                    currentMode === "EXAMINER" && "bg-red-500",
                    currentMode === "REFLECTION" && "bg-purple-500"
                  )}
                />
                {MODE_LABELS[currentMode] || currentMode}
              </span>
            </div>
          )}

          {/* Chat messages */}
          <div className="max-h-64 w-full overflow-y-auto rounded-lg bg-muted/50 px-2 py-1.5 space-y-2">
            {chatHistory.length === 0 && (
              <p className="text-xs text-muted-foreground py-2 text-center">
                {projectId
                  ? "Ask me anything about your research."
                  : "Open a project to start chatting."}
              </p>
            )}
            {chatHistory.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  "flex",
                  msg.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-lg px-2.5 py-1.5 text-xs leading-snug whitespace-pre-wrap",
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-background border text-foreground"
                  )}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="flex justify-start">
                <div className="rounded-lg bg-background border px-2.5 py-1.5 text-xs text-muted-foreground">
                  <span className="inline-flex gap-1">
                    <span className="animate-bounce">.</span>
                    <span className="animate-bounce" style={{ animationDelay: "0.1s" }}>.</span>
                    <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>.</span>
                  </span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input row */}
          <div className="flex gap-1.5 items-center">
            <Input
              ref={inputRef}
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                projectId ? "Type a message..." : "Open a project first"
              }
              disabled={!projectId || chatMutation.isPending}
              className="h-8 text-xs flex-1"
              aria-label="Chat message"
            />
            <Button
              type="button"
              size="sm"
              variant="default"
              onClick={sendMessage}
              disabled={
                !projectId || !chatInput.trim() || chatMutation.isPending
              }
              className="h-8 px-2.5 shrink-0"
              aria-label="Send message"
            >
              {/* Send icon */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </Button>
          </div>

          {/* Voice toggle */}
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => {
                setVoiceEnabled((v) => !v);
                if (isSpeaking) stopSpeaking();
              }}
              className={cn(
                "flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] transition-colors",
                voiceEnabled
                  ? "text-primary bg-primary/10 hover:bg-primary/20"
                  : "text-muted-foreground bg-muted hover:bg-muted/80"
              )}
              aria-label={voiceEnabled ? "Disable voice" : "Enable voice"}
            >
              {/* Speaker icon */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                {voiceEnabled && (
                  <>
                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                  </>
                )}
                {!voiceEnabled && (
                  <line x1="23" y1="9" x2="17" y2="15" />
                )}
              </svg>
              {voiceEnabled ? "Voice on" : "Voice off"}
            </button>

            {isSpeaking && (
              <button
                type="button"
                onClick={stopSpeaking}
                className="text-[10px] text-muted-foreground hover:text-foreground"
                aria-label="Stop speaking"
              >
                Stop
              </button>
            )}
          </div>
        </div>
      )}

      {/* "Chat with me" prompt when closed and project is available */}
      {!chatOpen && projectId && (
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="w-full rounded-lg border border-dashed border-primary/30 bg-primary/5 px-2.5 py-1.5 text-xs text-primary hover:bg-primary/10 transition-colors text-center"
        >
          Chat with me
        </button>
      )}
    </div>
  );
}
