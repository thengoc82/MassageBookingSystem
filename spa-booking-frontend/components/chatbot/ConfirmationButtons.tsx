"use client";

import { Check, X } from "lucide-react";

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
    <div className="flex justify-start pl-10">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onConfirm}
          disabled={disabled}
          aria-label="Confirm"
          className="flex items-center gap-1 rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-400 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          <Check size={14} />
          Confirm
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={disabled}
          aria-label="Cancel"
          className="flex items-center gap-1 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-400 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          <X size={14} />
          Cancel
        </button>
      </div>
    </div>
  );
}