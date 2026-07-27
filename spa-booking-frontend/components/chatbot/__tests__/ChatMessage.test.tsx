import React from "react";
import { render, screen } from "@testing-library/react";
import ChatMessage from "../ChatMessage";
import type { Message } from "@/lib/hooks/useChat";

describe("ChatMessage", () => {
  it("renders a user message", () => {
    const message: Message = {
      id: "1",
      role: "user",
      content: "Hello",
      timestamp: new Date().toISOString(),
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders an assistant message", () => {
    const message: Message = {
      id: "2",
      role: "assistant",
      content: "Hi there",
      timestamp: new Date().toISOString(),
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByText("Hi there")).toBeInTheDocument();
  });

  it("renders citations if provided", () => {
    const message: Message = {
      id: "4",
      role: "assistant",
      content: "Here is some info.",
      citations: [{ url: "http://example.com" }],
      timestamp: new Date().toISOString(),
    };

    render(<ChatMessage message={message} />);

    const link = screen.getByText("1");
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "http://example.com");
  });
});