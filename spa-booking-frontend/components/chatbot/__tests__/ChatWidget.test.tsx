import React, { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChatWidget from "../ChatWidget";

jest.mock("../ChatWindow", () => ({
  __esModule: true,
  default: function MockChatWindow({ onClose }: { onClose: () => void }) {
    const [count, setCount] = useState(0);
    return <div>
      <span>Messages: {count}</span>
      <button onClick={() => setCount(count + 1)}>Add message</button>
      <button onClick={onClose}>Close window</button>
    </div>;
  },
}));

it("keeps chat state when the window closes and reopens", async () => {
  const user = userEvent.setup();
  render(<ChatWidget />);
  await user.click(screen.getByRole("button", { name: "Open chat" }));
  await user.click(screen.getByRole("button", { name: "Add message" }));
  expect(screen.getByText("Messages: 1")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Close window" }));
  await user.click(screen.getByRole("button", { name: "Open chat" }));
  expect(screen.getByText("Messages: 1")).toBeVisible();
});
