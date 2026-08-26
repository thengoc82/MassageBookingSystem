"use client";

import { Pencil, X } from "lucide-react";
import { BookingState } from "@/lib/types";

type Props = {
  booking: BookingState;
  editingSection: string | null;
  onChangeSection: (section: string) => void;
  onClearSection: () => void;
};

const DetailRow = ({
  label,
  value,
  isEditing,
  onChangeClick,
  onClearClick,
  canEdit = true,
}: {
  label: string;
  value: string | number | undefined;
  isEditing: boolean;
  onChangeClick: () => void;
  onClearClick: () => void;
  canEdit?: boolean;
}) => (
  <div
    className={`flex justify-between py-1.5 text-sm ${
      isEditing ? "rounded-md bg-blue-50 -mx-2 px-2" : ""
    }`}
  >
    <span className="text-gray-500">{label}</span>
    <div className="flex items-center gap-2">
      <span className="font-medium text-gray-800">{value || "-"}</span>
      {value && canEdit && (
        <button
          onClick={isEditing ? onClearClick : onChangeClick}
          className="text-gray-400 hover:text-gray-600"
        >
          {isEditing ? <X size={14} /> : <Pencil size={14} />}
        </button>
      )}
    </div>
  </div>
);

export default function CurrentBooking({
  booking = {},
  editingSection,
  onChangeSection,
  onClearSection,
}: Props) {
  const isLocked = !!booking.time;

  return (
    <div className="h-full bg-white p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-500">Your Booking</h3>
      </div>
      <div className="space-y-2 rounded-lg bg-gray-50 p-3">
        <DetailRow
          label="Shop"
          value={booking.shopName}
          isEditing={!isLocked && editingSection === "shop"}
          onChangeClick={() => !isLocked && onChangeSection("shop")}
          onClearClick={onClearSection}
          canEdit={!isLocked}
        />
        <DetailRow
          label="Date"
          value={booking.date}
          isEditing={!isLocked && editingSection === "date"}
          onChangeClick={() => !isLocked && onChangeSection("date")}
          onClearClick={onClearSection}
          canEdit={!isLocked}
        />
        <DetailRow
          label="Guests"
          value={booking.guests}
          isEditing={!isLocked && editingSection === "guests"}
          onChangeClick={() => !isLocked && onChangeSection("guests")}
          onClearClick={onClearSection}
          canEdit={!isLocked}
        />
        <DetailRow
          label="Duration"
          value={booking.duration ? `${booking.duration} min` : undefined}
          isEditing={!isLocked && editingSection === "duration"}
          onChangeClick={() => !isLocked && onChangeSection("duration")}
          onClearClick={onClearSection}
          canEdit={!isLocked}
        />
        <DetailRow
          label="Package"
          value={booking.courseName}
          isEditing={!isLocked && editingSection === "course"}
          onChangeClick={() => !isLocked && onChangeSection("course")}
          onClearClick={onClearSection}
          canEdit={!isLocked}
        />
        <DetailRow
          label="Time"
          value={booking.time}
          isEditing={!isLocked && editingSection === "time"}
          onChangeClick={() => !isLocked && onChangeSection("time")}
          onClearClick={onClearSection}
          canEdit={!isLocked}
        />
        <DetailRow
          label="Therapist"
          value={booking.therapistName}
          isEditing={editingSection === "therapist"}
          onChangeClick={() => onChangeSection("therapist")}
          onClearClick={onClearSection}
        />
        <DetailRow
          label="Phone"
          value={booking.phone}
          isEditing={false}
          onChangeClick={() => {}}
          onClearClick={() => {}}
          canEdit={false}
        />
      </div>
    </div>
  );
}
