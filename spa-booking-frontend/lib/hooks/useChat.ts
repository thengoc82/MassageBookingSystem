"use client";

import { useState, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";

// Core data types
export type Citation = {
  url: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  timestamp: string;
};

type ChatResponse = {
  session_id: string;
  message: {
    role: "assistant";
    content: string;
    citations?: { url: string }[];
    requires_confirmation?: boolean;
  };
};

const CHAT_API_ENDPOINT = `${process.env.NEXT_PUBLIC_API_URL || ""}/chat`;

/**
 * useChat
 *
 * Core hook for chatbot UI components. Manages session, message
 * history, network state, and API communication.
 *
 * It holds no business logic about the booking flow itself. That
 * responsibility stays on the backend. The hook just shuttles
 * text messages back and forth, and renders UI hints from the
 * backend like `requires_confirmation`.
 */
export const useChat = (userId: string | null) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Session ID is generated once on hook init
  const [sessionId] = useState<string>(() => uuidv4());

  // Confirmation state
  const [pendingConfirmation, setPendingConfirmation] = useState(false);

  const addMessage = useCallback(
    (message: Omit<Message, "id" | "timestamp">) => {
      const newMessage: Message = {
        ...message,
        id: uuidv4(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, newMessage]);
    },
    []
  );

  const sendMessage = useCallback(
    async (text: string, isConfirmation = false) => {
      if (!text.trim() || !sessionId) return;

      setIsLoading(true);
      setError(null);
      if (!isConfirmation) {
        addMessage({ role: "user", content: text });
      }
      setPendingConfirmation(false);

      try {
        const response = await fetch(CHAT_API_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            user_id: userId,
            message: {
              role: "user",
              content: text,
            },
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(
            errData.error || `HTTP ${response.status}: Failed to get response`
          );
        }

        const data: ChatResponse = await response.json();

        addMessage({
          role: "assistant",
          content: data.message.content,
          citations: data.message.citations,
        });

        if (data.message.requires_confirmation) {
          setPendingConfirmation(true);
        }
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : "An unknown error occurred.";
        setError(errorMessage);
        addMessage({
          role: "assistant",
          content: `Sorry, I ran into a problem: ${errorMessage}`,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [addMessage, sessionId, userId]
  );

  const confirm = useCallback(
    (text: "yes" | "Yes") => {
      sendMessage(text, true);
    },
    [sendMessage]
  );

  const cancel = useCallback(
    (text: "no" | "No") => {
      sendMessage(text, true);
    },
    [sendMessage]
  );

  return {
    messages,
    input,
    setInput,
    sendMessage,
    isLoading,
    error,
    pendingConfirmation,
    confirm,
    cancel,
  };
};