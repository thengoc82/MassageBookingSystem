import { useState, useRef, useEffect } from "react";
import { PackageOption } from "@/components/chatbot/PackageOptions";
import { api } from "@/lib/api";
import {
  BookingState,
  ChatRequest,
  ChatResponse,
  ConversationPhase,
} from "@/lib/types";

export type Message = {
  id: string;
  text: string;
  isUser: boolean;
  phase?: string;
  data?: any;
  selectedTherapistId?: string | number;
  selectedTime?: string;
  selectedPackage?: PackageOption;
  selectedCourseId?: string;
  selectedAddonIds?: string[];
  selectedShopId?: number;
};

export const useChat = (userId: string | null) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingConfirmation, setPendingConfirmation] = useState(false);
  const [bookingState, setBookingState] = useState<BookingState | null>(null);
  const [currentPhase, setCurrentPhase] = useState<ConversationPhase>(
    ConversationPhase.GREETING
  );
  const [isBookingCompleted, setIsBookingCompleted] = useState(false);
  const sessionId = useRef<string | null>(null);
  const initStarted = useRef(false);

  const [shownGreeting, setShownGreeting] = useState(false);

  useEffect(() => {
    if (messages.length === 0 && !isLoading && !initStarted.current) {
      initStarted.current = true;
      startConversation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const generateSessionId = () => {
    return (
      Math.random().toString(36).substring(2, 15) +
      Math.random().toString(36).substring(2, 15)
    );
  };

  const updateMessage = (id: string, updates: Partial<Message>) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
    );
  };

  const handleBackendResponse = (data: ChatResponse) => {
    if (data.phase) {
      setCurrentPhase(data.phase);
    }

    if (data.message) {
      const assistantMessage: Message = {
        id: Date.now().toString() + "-assistant",
        text: data.message,
        isUser: false,
        phase: data.phase,
        data: data.data,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }

    if (data.phase === ConversationPhase.GREETING) {
      setShownGreeting(true);
    }

    if (data.booking_state) {
      setBookingState(data.booking_state);
    }

    if (data.phase === ConversationPhase.BOOKING_COMPLETE) {
      setIsBookingCompleted(true);
    }
    
    // The backend now controls the confirmation flow via phase
    setPendingConfirmation(
      data.phase === ConversationPhase.CONFIRMING_BOOKING ||
        data.phase === ConversationPhase.REQUESTING_REVIEW
    );
  }

  const startConversation = async () => {
    if (!sessionId.current) {
      sessionId.current = generateSessionId();
    }
    setIsLoading(true);
    setError(null);

    const body: ChatRequest = {
      message: "start",
      start_conversation: true,
      session_id: sessionId.current,
      user_id: userId,
    };

    try {
      const data: ChatResponse = await api.chat.sendMessage(body);
      handleBackendResponse(data);
    } catch (err: any) {
      setError(err.message || "Failed to start the conversation.");
      const errorMessage: Message = {
        id: Date.now().toString() + "-error",
        text: err.message || "Failed to connect to the chatbot. Please try again later.",
        isUser: false,
      };
      setMessages([errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (text: string, payload?: Record<string, any>) => {
    if (!sessionId.current) {
      sessionId.current = generateSessionId();
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      isUser: true,
    };
    setMessages((prev) => [...prev, userMessage]);
    setShownGreeting(false);
    
    setIsLoading(true);
    setError(null);

    const body: ChatRequest = {
      message: text,
      session_id: sessionId.current,
      user_id: userId,
      ...payload,
    };

    console.log("Sending to backend:", body); // [DEBUG-a4f2]

    try {
      const data: ChatResponse = await api.chat.sendMessage(body);
      handleBackendResponse(data);
    } catch (err: any) {
      setError(err.message || "Failed to get response from the chatbot.");
      const errorMessage: Message = {
        id: Date.now().toString() + "-error",
        text: err.message || "Failed to get a response. Please check your connection.",
        isUser: false,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };
  
  const confirm = (choice: string) => {
    sendMessage(choice);
    setPendingConfirmation(false);
  };

  const cancel = (choice: string) => {
    sendMessage(choice);
    setPendingConfirmation(false);
  };

  const restartBooking = () => {
    setIsBookingCompleted(false);
    setBookingState(null);
    setCurrentPhase(ConversationPhase.GREETING);
    startConversation();
  };

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
    updateMessage,
    bookingState,
    shownGreeting,
    isBookingCompleted,
    restartBooking,
    currentPhase,
  };
};
