"use client";

import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import { DayPicker } from "react-day-picker";
import "react-day-picker/dist/style.css";
import { format } from "date-fns";

type Props = {
  onSelect: (date: string) => void;
  isCompleted: boolean;
  onEdit: () => void;
  selectedDate: string | null;
};

export default function DateOptions({
  onSelect,
  isCompleted,
  onEdit,
  selectedDate,
}: Props) {
  const [date, setDate] = useState<Date | undefined>(
    selectedDate ? new Date(selectedDate) : undefined
  );

  const handleDateSelect = (selected: Date | undefined) => {
    if (selected) {
      setDate(selected);
      onSelect(format(selected, "yyyy-MM-dd"));
    }
  };

    const summary = <p className="font-semibold">{selectedDate}</p>;

  if (isCompleted && selectedDate) {
    return (
      <CollapsibleSection
        title="Date"
        isCompleted={isCompleted}
        summary={summary}
        onEdit={onEdit}
      >
        <></>
      </CollapsibleSection>
    );
  }

  return (
    <div className="p-2 bg-white rounded-lg shadow-lg">
      <DayPicker
        mode="single"
        selected={date}
        onSelect={handleDateSelect}
        disabled={{ before: new Date() }}
        className="rounded-md"
      />
    </div>
  );
}
