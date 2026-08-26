"use client";

import { Message } from "@/lib/hooks/useChat";
import CollapsibleSection from "./CollapsibleSection";

type Therapist = {
  therapistId: string;
  name: string;
  gender: string;
  isAvailable: boolean;
};

type Props = {
  message: Message;
  onSelect: (therapistId: string | null) => void;
  onConfirm: () => void;
  onSkip: () => void;
  selectedTherapistId?: string;
  onEdit: () => void;
  isCompleted: boolean;
  selectedTherapistName?: string;
};

export default function TherapistOptions({
  message,
  onSelect,
  onConfirm,
  onSkip,
  selectedTherapistId,
  onEdit,
  isCompleted,
  selectedTherapistName,
}: Props) {
  const therapists = message.data?.options as Therapist[] | undefined;

  if (!therapists || therapists.length === 0) {
    return null;
  }

  const handleSelection = (therapist: Therapist) => {
    if (therapist.therapistId === selectedTherapistId) {
      onSelect(null);
    } else {
      onSelect(therapist.therapistId);
    }
  };

  const summary = selectedTherapistName || "No preference";

  return (
    <CollapsibleSection
      title="Therapist"
      isCompleted={isCompleted}
      summary={summary}
      onEdit={onEdit}
    >
      <div className="flex flex-col space-y-2">
        {therapists.map((therapist) => {
          const isSelected = therapist.therapistId === selectedTherapistId;
          const isDisabled = !therapist.isAvailable;

          return (
            <button
              key={therapist.therapistId}
              onClick={() => handleSelection(therapist)}
              disabled={isDisabled}
              className={`group flex flex-col items-start rounded-lg border p-3 text-left text-sm text-gray-800 transition ${
                isSelected
                  ? "border-indigo-500 bg-indigo-50"
                  : "border-gray-200 bg-white hover:bg-gray-50"
              } ${isDisabled ? "cursor-not-allowed opacity-50" : ""}`}
            >
              <div className="flex items-center">
                <span
                  className={`mr-3 h-4 w-4 rounded-full border flex items-center justify-center ${
                    isSelected ? "border-indigo-600 bg-indigo-600" : "border-gray-400"
                  }`}
                >
                  {isSelected && (
                    <svg
                      className="h-2.5 w-2.5 fill-current text-white"
                      viewBox="0 0 16 16"
                    >
                      <circle cx="8" cy="8" r="8" />
                    </svg>
                  )}
                </span>
                <span className="font-semibold">{therapist.name}</span>
              </div>
            </button>
          );
        })}
        <div className="flex justify-end space-x-2 pt-2">
          <button
            onClick={onSkip}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            No preference
          </button>
          <button
            onClick={onConfirm}
            disabled={!selectedTherapistId}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            Confirm
          </button>
        </div>
      </div>
    </CollapsibleSection>
  );
}
