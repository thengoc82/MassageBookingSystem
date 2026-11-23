import { act, renderHook } from "@testing-library/react";
import { useChat } from "./useChat";

jest.mock("uuid", () => ({ v4: () => "test-id" }));

it("uses server progress to show and clear final confirmation", async () => {
  const fetchMock = jest.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true, session_id: "s1", message: "Please confirm",
        phase: "confirming_action",
        booking_progress: {
          active: true, stage: "confirmation", details: { people: 2 },
          missing: [], requires_confirmation: true,
        },
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true, session_id: "s1", message: "Booked",
        phase: "booking_complete",
        booking_progress: {
          active: true, stage: "complete", details: { booking_code: "BK1" },
          missing: [], requires_confirmation: false,
        },
      }),
    });
  const originalFetch = global.fetch;
  global.fetch = fetchMock as typeof fetch;
  try {
    const { result } = renderHook(() => useChat(null));
    await act(async () => { await result.current.sendMessage("Book a massage"); });
    expect(result.current.pendingConfirmation).toBe(true);
    expect(result.current.bookingProgress?.details.people).toBe(2);
    await act(async () => { await result.current.sendMessage("yes", true); });
    expect(result.current.pendingConfirmation).toBe(false);
    expect(result.current.bookingProgress?.details.booking_code).toBe("BK1");
  } finally {
    global.fetch = originalFetch;
  }
});

it("hides confirmation when its network result is unknown", async () => {
  const fetchMock = jest.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true, session_id: "s1", message: "Please confirm",
        phase: "confirming_action",
        booking_progress: {
          active: true, stage: "confirmation", details: {},
          missing: [], requires_confirmation: true,
        },
      }),
    })
    .mockRejectedValueOnce(new Error("Network disconnected"));
  const originalFetch = global.fetch;
  global.fetch = fetchMock as typeof fetch;
  try {
    const { result } = renderHook(() => useChat(null));
    await act(async () => { await result.current.sendMessage("Book a massage"); });
    expect(result.current.pendingConfirmation).toBe(true);
    await act(async () => { await result.current.sendMessage("yes", true); });
    expect(result.current.pendingConfirmation).toBe(false);
    expect(result.current.bookingProgress).toBeNull();
    expect(result.current.error).toContain("couldn't verify");
  } finally {
    global.fetch = originalFetch;
  }
});
