"use client";

type Props = {
  onBookAnother: () => void;
  onAskQuestion: () => void;
};

export default function PostBookingOptions({
  onBookAnother,
  onAskQuestion,
}: Props) {
  return (
    <div className="flex flex-col items-center space-y-2 p-2">
        <h3 className="text-sm font-semibold text-gray-500 mb-2">What would you like to do next?</h3>
      <button
        onClick={onBookAnother}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Book another massage
      </button>
      <button
        onClick={onAskQuestion}
        className="w-full rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Ask a question
      </button>
    </div>
  );
}
