import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChatWindow from "../ChatWindow";
import { useChat } from "@/lib/hooks/useChat";

// Mock the dependencies
jest.mock("@/lib/hooks/useChat", () => ({
  useChat: jest.fn(),
}));

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "user-123" } }),
}));

jest.mock("date-fns", () => ({
  format: () => "12:00 PM",
}));

const mockUseChat = useChat as jest.Mock;

describe("ChatWindow", () => {
  const mockSendMessage = jest.fn();
  const mockSetInput = jest.fn();

  beforeEach(() => {
    mockUseChat.mockReturnValue({
      messages: [],
      input: "",
      setInput: mockSetInput,
      sendMessage: mockSendMessage,
      isLoading: false,
      error: null,
      pendingConfirmation: false,
      confirm: jest.fn(),
      cancel: jest.fn(),
    });
    jest.clearAllMocks();
  });

  it("renders correctly", () => {
    render(<ChatWindow onClose={() => {}} />);

    expect(screen.getByText("Booking Assistant")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Type a message…")).toBeInTheDocument();
  });

  it("calls sendMessage when the send button is clicked", async () => {
    const user = userEvent.setup();
    mockUseChat.mockReturnValueOnce({
      ...mockUseChat(),
      input: "Hello",
    });

    render(<ChatWindow onClose={() => {}} />);

    const input = screen.getByPlaceholderText("Type a message…");
    await user.type(input, "Hello");
    const sendButton = screen.getByText("Send");
    await user.click(sendButton);

    expect(mockSendMessage).toHaveBeenCalledWith("Hello");
  });

  it("disables input and button when loading", () => {
    mockUseChat.mockReturnValueOnce({
      ...mockUseChat(),
      isLoading: true,
    });

    render(<ChatWindow onClose={() => {}} />);

    expect(screen.getByPlaceholderText("Waiting for response…")).toBeDisabled();
    expect(screen.getByText("Send")).toBeDisabled();
  });

  it("shows an error message", () => {
    mockUseChat.mockReturnValueOnce({
      ...mockUseChat(),
      error: "Something went wrong",
    });

    render(<ChatWindow onClose={() => {}} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });
});