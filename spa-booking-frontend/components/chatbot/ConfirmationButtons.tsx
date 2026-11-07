"use client";

import { Check } from "lucide-react";

type Props = {
  onConfirm: () => void;
  onCancel: () => void;
  disabled?: boolean;
};

/**
 * ConfirmationButtons
 *
 * Renders inline Confirm/Cancel buttons used whenever the chatbot
 * asks the user to approve an action (booking, modification,
 * cancellation). Sends a plain-text reply to the backend — the server
 * remains the source of truth for the confirmation flow.
 */
export default function ConfirmationButtons({
  onConfirm,
  onCancel,
  disabled,
}: Props) {
  return (
    <div className="flex gap-2 pl-10">
      <button
        type="button"
        onClick={onConfirm}
        disabled={disabled}
        aria-label="Confirm"
        className="flex h-11 flex-1 items-center justify-center gap-1.5 rounded-[10px] bg-celadon px-4 text-sm font-semibold text-white transition-colors hover:bg-celadon-deep disabled:cursor-not-allowed disabled:bg-[#B8C4C0]"
      >
        <Check size={16} aria-hidden="true" />
        Confirm booking
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={disabled}
        aria-label="Cancel"
        className="flex h-11 flex-1 items-center justify-center rounded-[10px] border border-celadon px-4 text-sm font-semibold text-celadon-deep transition-colors hover:bg-celadon-soft disabled:cursor-not-allowed disabled:border-[#B8C4C0] disabled:text-[#8A9A96] disabled:hover:bg-transparent"
      >
        Cancel
      </button>
    </div>
  );
}
