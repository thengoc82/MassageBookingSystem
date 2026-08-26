"use client";

import { CheckCircle2, CircleDashed } from "lucide-react";

type Step = {
  name: string;
  status: "completed" | "active" | "inactive";
};

const steps: Omit<Step, "status">[] = [
  { name: "Shop" },
  { name: "Date" },
  { name: "Guests" },
  { name: "Duration" },
  { name: "Course & Add-ons" },
  { name: "Time" },
  { name: "Therapist" },
  { name: "Phone" },
  { name: "Review" },
  { name: "Confirm" },
  { name: "Booking Code" },
];

type Props = {
  activeStep: number;
};

export default function BookingProgress({ activeStep }: Props) {
  return (
    <div className="h-full bg-gray-50/50 p-4">
      <h3 className="mb-4 text-sm font-semibold text-gray-500">
        Booking Progress
      </h3>
      <ul className="space-y-3">
        {steps.map((step, index) => {
          const status =
            index < activeStep
              ? "completed"
              : index === activeStep
              ? "active"
              : "inactive";
          return (
            <li key={step.name} className="flex items-center gap-2">
              {status === "completed" ? (
                <CheckCircle2 size={16} className="text-green-500" />
              ) : (
                <CircleDashed
                  size={16}
                  className={
                    status === "active" ? "text-indigo-600" : "text-gray-300"
                  }
                />
              )}
              <span
                className={`text-sm ${
                  status === "active"
                    ? "font-semibold text-indigo-600"
                    : status === "completed"
                    ? "text-gray-500 line-through"
                    : "text-gray-400"
                }`}
              >
                {step.name}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
