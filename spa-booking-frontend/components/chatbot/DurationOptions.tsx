"use client";

import CollapsibleSection from "./CollapsibleSection";
import { useState } from "react";

type Props = {
  onSelect: (duration: number) => void;
  selectedDuration: number | null;
  isCompleted: boolean;
  onEdit: () => void;
};

const DURATION_OPTIONS = [15, 30, 45, 60, 75, 90];

export default function DurationOptions({
  onSelect,
  selectedDuration,
  isCompleted,
  onEdit,
}: Props) {
    const summary = (
    <p className="font-semibold">{selectedDuration} min</p>
  );

  if (isCompleted) {
    return (
      <CollapsibleSection
        title="Duration"
        isCompleted={isCompleted}
        summary={summary}
        onEdit={onEdit}
      >
        <></>
      </CollapsibleSection>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      {DURATION_OPTIONS.map((duration) => (
        <button
          key={duration}
          onClick={() => onSelect(duration)}
          className={`p-3 rounded-lg text-center font-semibold transition-colors ${
            selectedDuration === duration
              ? "bg-indigo-600 text-white"
              : "bg-gray-200 hover:bg-gray-300"
          }`}
        >
          {duration} min
        </button>
      ))}
    </div>
  );
}
