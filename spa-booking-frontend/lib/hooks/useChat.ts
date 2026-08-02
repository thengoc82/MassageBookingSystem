import { useState, useRef } from "react";

export type Message = {
  id: string;
  text: string;
  isUser: boolean;
};

export const useChat = (userId: string | null) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingConfirmation, setPendingConfirmation] = useState(false);
  const sessionId = useRef<string | null>(null);

  // Function to generate a simple session ID
  const generateSessionId = () => {
    return (
      Math.random().toString(36).substring(2, 15) +
      Math.random().toString(36).substring(2, 15)
    );
  };

  const sendMessage = async (text: string) => {
    if (!sessionId.current) {
      sessionId.current = generateSessionId();
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      isUser: true,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_CHATBOT_API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId.current,
          user_id: userId,
        }),
      });

      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new Error("Invalid response from server. Expected JSON.");
      }

      const data = await response.json();

      if (data.message) {
        const assistantMessage: Message = {
          id: Date.now().toString() + "-assistant",
          text: data.message,
          isUser: false,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }

      if (!response.ok && !data.message) {
         throw new Error(data.detail || "Network response was not ok");
      }


    } catch (err: any) {
      setError(err.message || "Failed to get response from the chatbot. Please try again.");
      const assistantMessage: Message = {
          id: Date.now().toString() + "-assistant",
          text: err.message || "Failed to get response from the chatbot. Please try again.",
          isUser: false,
        };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const confirm = (choice: string) => {
    // This functionality might need to be implemented as part of the backend communication
    console.log("Confirmed:", choice);
    setPendingConfirmation(false);
  };

  const cancel = (choice: string) => {
    // This functionality might need to be implemented as part of the backend communication
    console.log("Cancelled:", choice);
    setPendingConfirmation(false);
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
  };
};
