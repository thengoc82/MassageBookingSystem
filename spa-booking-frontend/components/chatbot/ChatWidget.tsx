"use client";

import { useState } from "react";
import ChatWindow from "./ChatWindow";
import { MessageCircle } from "lucide-react";

/**
 * ChatWidget
 *
 * Floating button + window. Mounts once in the root layout, persists
 * across page navigations within the SPA, and renders nothing if the
 * user has explicitly closed it for the session.
 */
export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {isOpen ? (
        <ChatWindow onClose={() => setIsOpen(false)} />
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          aria-label="Open chat"
          className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition-transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2"
        >
          <MessageCircle size={24} />
        </button>
      )}
    </div>
  );
}