"use client";

type GreetingProps = {
  sendMessage: (message: string) => void;
  disabled?: boolean;
};

export default function Greeting({ sendMessage, disabled }: GreetingProps) {
  const handleBook = () => {
    sendMessage("I want to book a massage");
  };

  const handleAsk = () => {
    sendMessage("I have a question");
  };

  return (
    <div className="flex justify-center space-x-2 my-2">
      <button
        onClick={handleBook}
        disabled={disabled}
        className="px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-100 border border-transparent rounded-full hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        Book a massage
      </button>
      <button
        onClick={handleAsk}
        disabled={disabled}
        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-transparent rounded-full hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
      >
        Ask something
      </button>
    </div>
  );
}
