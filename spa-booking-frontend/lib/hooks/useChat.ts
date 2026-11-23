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
  booking_progress?: BookingProgress | null;
};

export type BookingProgress = {
  active: boolean;
  stage: string | null;
  details: Partial<Record<
    "shop" | "service" | "date" | "duration" | "people" | "time" |
    "time_preference" | "phone" | "booking_code", string | number
  >>;
  missing: string[];
  requires_confirmation: boolean;
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
  const [bookingProgress, setBookingProgress] = useState<BookingProgress | null>(null);

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
          } catch {
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

        if (data.booking_progress) {
          setBookingProgress(data.booking_progress);
          setPendingConfirmation(data.booking_progress.requires_confirmation);
        } else {
          setPendingConfirmation(data.phase === "confirming_action");
        }
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : `An unknown error occurred: ${String(err)}`;
        if (isConfirmation || pendingConfirmation) {
          const guidance = /^(yes|y|confirm|book it)$/i.test(text.trim())
            ? "I couldn't verify whether your booking was created. Please check your booking by phone before trying again."
            : "I couldn't verify your response. Please send another message to continue.";
          setPendingConfirmation(false);
          setBookingProgress(null);
          setError(guidance);
          addMessage({ role: "assistant", content: guidance });
          return;
        }
        setError(errorMessage);
        addMessage({
          role: "assistant",
          content: `Sorry, I ran into a problem: ${errorMessage}`,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [addMessage, pendingConfirmation, sessionId, userId]
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
    bookingProgress,
    confirm,
    cancel,
  };
};
