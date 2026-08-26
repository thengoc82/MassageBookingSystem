"use client";

import { useState, useMemo } from "react";
import { Check } from "lucide-react";
import CollapsibleSection from "./CollapsibleSection";

type TimePickerProps = {
  times: string[];
  onConfirm: (time: string) => void;
  onSelect: (time: string | null) => void;
  selectedTime: string | undefined;
  onEdit: () => void;
  isCompleted: boolean;
};

// Helper to group times by hour
const groupTimesByHour = (times: string[]) => {
  return times.reduce((acc, time) => {
    const hour = time.slice(0, 2);
    if (!acc[hour]) {
      acc[hour] = [];
    }
    acc[hour].push(time);
    return acc;
  }, {} as Record<string, string[]>);
};

export default function TimePicker({
  times,
  onConfirm,
  onSelect,
  selectedTime,
  onEdit,
  isCompleted,
}: TimePickerProps) {
  const [expandedHour, setExpandedHour] = useState<string | null>(() => {
    if (selectedTime) {
      return selectedTime.slice(0, 2);
    }
    return times.length > 0 ? times[0].slice(0, 2) : null;
  });

  const groupedTimes = useMemo(() => groupTimesByHour(times), [times]);

  const handleConfirm = () => {
    if (selectedTime) {
      onConfirm(selectedTime);
    }
  };

  const handleTimeClick = (time: string) => {
    onSelect(time);
  };

  const toggleHour = (hour: string) => {
    setExpandedHour(expandedHour === hour ? null : hour);
  };

  return (
    <CollapsibleSection
      title="Start time"
      isCompleted={isCompleted}
      summary={selectedTime}
      onEdit={onEdit}
    >
      <div className="space-y-2">
        {Object.entries(groupedTimes)
          .sort(([hourA], [hourB]) => hourA.localeCompare(hourB))
          .map(([hour, hourTimes]) => (
            <div key={hour}>
              <button
                onClick={() => toggleHour(hour)}
                className="flex w-full items-center justify-between rounded bg-gray-200 px-3 py-2 text-left text-sm font-medium text-gray-800"
              >
                <span>{hour}:00</span>
                <span
                  className={`transform transition-transform ${
                    expandedHour === hour ? "rotate-180" : "rotate-0"
                  }`}
                >
                  ▼
                </span>
              </button>
              {expandedHour === hour && (
                <div className="grid grid-cols-4 gap-2 p-2">
                  {hourTimes.map((time) => (
                    <button
                      key={time}
                      onClick={() => handleTimeClick(time)}
                      className={`rounded px-2 py-1.5 text-xs transition ${
                        selectedTime === time
                          ? "bg-indigo-600 text-white"
                          : "bg-white text-gray-700 hover:bg-gray-50"
                      }`}
                    >
                      {time}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
      </div>
      {selectedTime && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleConfirm}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white"
          >
            Confirm
          </button>
        </div>
      )}
    </CollapsibleSection>
  );
}
