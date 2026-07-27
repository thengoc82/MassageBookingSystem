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
  success: boolean;
  session_id: string;
  message: string;
  phase?: string;
  data?: Record<string, unknown>;
  error?: string | null;
  // Add other fields that the chatbot might return
};

const CHAT_API_ENDPOINT = `${process.env.NEXT_PUBLIC_CHATBOT_URL || ""}/chat`;

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
            message: text,
          }),
        });

        if (!response.ok) {
          let errorDetail = `HTTP ${response.status}: Failed to get response`;
          try {
            const errData = await response.json();
            if (errData && errData.error) {
              errorDetail = errData.error;
            } else if (errData && errData.message) {
              errorDetail = errData.message;
            }
          } catch (jsonErr) {
            // response was not JSON, use generic message
          }
          throw new Error(errorDetail);
        }

        const data: ChatResponse = await response.json();

        // Always display the message from the chatbot if it's a valid JSON response
        addMessage({
          role: "assistant",
          content: data.message,
        });

        // Preserve phase, session_id, and data
        // (sessionId is already managed, data is not directly used by useChat but passed through)
        // phase is used below for pendingConfirmation

        if (data.phase === "confirming_action") {
          setPendingConfirmation(true);
        } else if (!data.success && data.message) {
          // If success is false but it's a valid chat response with a message,
          // display the message normally (already done by addMessage above).
          // No additional error UI should be shown for this case.
        }
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : `An unknown error occurred: ${String(err)}`;
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