"use client";

import { CheckCircle2 } from "lucide-react";
import CollapsibleSection from "./CollapsibleSection";

// TODO: Replace with actual data structure from the API
type Course = {
  course_id: string;
  name: string;
  duration: number;
  price: number;
};

type Addon = {
  addon_id: string;
  name: string;
  duration: number;
  price: number;
};

// Represents a selectable package
export type PackageOption = {
  name: string;
  totalDuration: number;
  totalPrice: number;
  course: Course;
  addons: Addon[];
};

type Props = {
  packages: PackageOption[];
  selectedPackage: PackageOption | null;
  onSelect: (pkg: PackageOption) => void;
  onConfirm: () => void;
  onEdit: () => void;
  isCompleted: boolean;
};

/**
 * PackageOptions
 *
 * Displays a list of selectable packages.
 */
export default function PackageOptions({
  packages,
  selectedPackage,
  onSelect,
  onConfirm,
  onEdit,
  isCompleted,
}: Props) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("ja-JP", {
      style: "currency",
      currency: "JPY",
    }).format(amount);
  };

  const summary = selectedPackage && (
    <>
      <p className="font-semibold text-gray-800">{selectedPackage.name}</p>
      <p className="text-sm text-gray-600">
        {selectedPackage.totalDuration} min • {formatCurrency(selectedPackage.totalPrice)}
      </p>
    </>
  );

  return (
    <CollapsibleSection
      title="Package"
      isCompleted={isCompleted}
      summary={summary}
      onEdit={onEdit}
    >
      <div className="space-y-3">
        <div className="grid grid-cols-1 gap-3">
          {packages.map((pkg, index) => (
            <button
              key={index}
              type="button"
              onClick={() => onSelect(pkg)}
              className={`relative w-full rounded-lg border p-4 text-left transition ${
                selectedPackage?.name === pkg.name
                  ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-500"
                  : "border-gray-300 bg-white hover:border-gray-400"
              }`}
            >
              {selectedPackage?.name === pkg.name && (
                <CheckCircle2
                  className="absolute right-3 top-3 h-5 w-5 text-indigo-600"
                  aria-hidden="true"
                />
              )}
              <p className="mb-2 text-base font-semibold text-gray-800">
                {pkg.name}
              </p>
              <div className="mb-3">
                <p className="text-sm font-medium text-gray-700">Services</p>
                <ul className="text-sm text-gray-600">
                  <li className="flex justify-between">
                    <span>{pkg.course.name}</span>
                    <span>{pkg.course.duration} min</span>
                  </li>
                  {pkg.addons.map((addon) => (
                    <li key={addon.addon_id} className="flex justify-between">
                      <span>{addon.name}</span>
                      <span>{addon.duration} min</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex items-baseline justify-between border-t border-gray-200 pt-3">
                <p className="text-base font-medium text-gray-700">Total</p>
                <div className="text-right">
                  <p className="text-lg font-bold text-gray-900">
                    {pkg.totalDuration} min • {formatCurrency(pkg.totalPrice)}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onConfirm}
          disabled={!selectedPackage}
          className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          Confirm
        </button>
      </div>
    </CollapsibleSection>
  );
}
