"use client";

import { useState, ReactNode } from "react";
import { ChevronDown } from "lucide-react";

type Props = {
  title: string;
  children: ReactNode;
  isCompleted: boolean;
  summary: ReactNode;
  onEdit: () => void;
};

export default function CollapsibleSection({
  title,
  children,
  isCompleted,
  summary,
  onEdit,
}: Props) {
  if (isCompleted) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <div className="mt-1 text-base font-semibold text-gray-800">
              {summary}
            </div>
          </div>
          <button
            onClick={onEdit}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            Change
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-indigo-500/50 bg-white">
      <div className="p-4">
        <h3 className="text-base font-semibold text-gray-800">{title}</h3>
      </div>
      <div className="border-t border-gray-200 p-4">{children}</div>
    </div>
  );
}
