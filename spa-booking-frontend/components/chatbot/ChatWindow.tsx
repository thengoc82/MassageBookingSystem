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
      className="flex h-[600px] w-[380px] max-w-[calc(100vw-2rem)] flex-col rounded-2xl bg-white shadow-2xl ring-1 ring-gray-200 sm:h-[600px] sm:w-[420px]"
    >
      {/* Header */}
      <div className="flex items-center justify-between rounded-t-2xl bg-blue-600 px-4 py-3 text-white">
        <div>
          <h2 className="text-base font-semibold">Booking Assistant</h2>
          <p className="text-xs text-blue-100">Online</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close chat"
          className="rounded-full p-1 transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-white"
        >
          <X size={20} />
        </button>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto bg-gray-50 px-4 py-3"
      >
        {messages.map((m) => (
          <ChatMessage key={m.id} message={m} />
        ))}

        {isLoading && (
          <div className="flex items-start gap-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
              AI
            </div>
            <div
              className="rounded-2xl bg-white px-3 py-2 text-sm text-gray-700 shadow ring-1 ring-gray-200"
              aria-live="polite"
            >
              <Loader2 className="inline animate-spin" size={16} />
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
            className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200"
          >
            {error}
          </div>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 border-t border-gray-200 bg-white p-3"
      >
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
          className="flex-1 resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          Send
        </button>
      </form>
    </div>
  );
}