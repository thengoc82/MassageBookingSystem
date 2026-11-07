"use client";

import { useEffect, useRef } from "react";
import { X, Loader2 } from "lucide-react";
import { useChat } from "@/lib/hooks/useChat";
import { useAuth } from "@/contexts/AuthContext";
import ChatMessage from "./ChatMessage";
import ConfirmationButtons from "./ConfirmationButtons";

type Props = {
  onClose: () => void;
};

/**
 * ChatWindow
 *
 * Renders the header, scrollable message list, optional confirmation
 * buttons from the last assistant message, the input area, and a
 * disabled state while waiting for a backend response.
 */
export default function ChatWindow({ onClose }: Props) {
  const { user } = useAuth();
  const {
    messages,
    input,
    setInput,
    sendMessage,
    isLoading,
    error,
    pendingConfirmation,
    confirm,
    cancel,
  } = useChat(user?.id ?? null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isLoading]);

  // Keep focus on input when window opens / after response
  useEffect(() => {
    if (!isLoading && inputRef.current) inputRef.current.focus();
  }, [isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Chat with booking assistant"
      className="flex h-[min(720px,calc(100vh-2rem))] w-[420px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl bg-linen shadow-2xl ring-1 ring-line"
    >
      {/* Header */}
      <div className="flex items-center gap-3 bg-basalt py-3.5 pl-5 pr-2 text-white">
        <span
          aria-hidden="true"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-celadon"
        >
          <svg width="24" height="24" viewBox="0 0 28 28">
            <ellipse cx="14" cy="19" rx="11" ry="6" fill="#1F2B2A" opacity="0.45" />
            <ellipse cx="14" cy="13" rx="8" ry="4.5" fill="#B7DCD3" />
            <ellipse cx="14" cy="8" rx="5" ry="3" fill="#fff" />
          </svg>
        </span>
        <div className="flex-1 leading-tight">
          <h2 className="font-display text-lg font-bold">Booking Assistant</h2>
          <p className="text-[13px] text-[#B9CAC6]">Usually answers within a few seconds</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close chat"
          className="flex h-11 w-11 items-center justify-center rounded-[10px] transition-colors hover:bg-basalt-2"
        >
          <X size={20} aria-hidden="true" />
        </button>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto bg-[#F1F5F3] px-4 py-5"
      >
        {messages.length === 0 && (
          <div className="flex items-start">
            <div className="max-w-[88%] rounded-2xl rounded-bl-sm bg-white px-3.5 py-2.5 text-[15px] leading-relaxed text-basalt ring-1 ring-line">
              Hi, I can book, change or cancel a massage for you. What would you like to do?
            </div>
          </div>
        )}

        {messages.map((m) => (
          <ChatMessage key={m.id} message={m} />
        ))}

        {isLoading && (
          <div className="flex items-start gap-2">
            <div
              className="rounded-2xl rounded-bl-sm bg-white px-3.5 py-2.5 text-sm text-ink-soft ring-1 ring-line"
              aria-live="polite"
            >
              <Loader2 className="inline animate-spin" size={16} aria-hidden="true" />
              <span className="ml-2">Typing…</span>
            </div>
          </div>
        )}

        {pendingConfirmation && (
          <ConfirmationButtons
            onConfirm={() => confirm("yes")}
            onCancel={() => cancel("no")}
            disabled={isLoading}
          />
        )}

        {error && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200"
          >
            {error}
          </div>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-line bg-linen px-4 pb-3.5 pt-3"
      >
        <div className="flex items-end gap-2">
          <label htmlFor="chat-input" className="sr-only">
            Message
          </label>
          <textarea
            id="chat-input"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
            placeholder={
              isLoading ? "Waiting for response…" : "Type a message…"
            }
            className="min-h-11 flex-1 resize-none rounded-[10px] border border-[#C5D0CC] bg-white px-3.5 py-2.5 text-[15px] disabled:cursor-not-allowed disabled:bg-[#EEF2F0]"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="h-11 rounded-[10px] bg-basalt px-4 text-sm font-semibold text-white transition-colors hover:bg-basalt-2 disabled:cursor-not-allowed disabled:bg-[#B8C4C0]"
          >
            Send
          </button>
        </div>
        <p className="mt-2 text-xs leading-snug text-ink-soft">
          Times are checked again when you confirm, so a slot can change if someone books first.
        </p>
      </form>
    </div>
  );
}
