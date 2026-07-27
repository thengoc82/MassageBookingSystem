"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { format } from "date-fns";
import type { Message } from "@/lib/hooks/useChat";

type Props = {
  message: Message;
};

function Citation({ url, number }: { url: string; number: number }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="ml-1 inline-block h-5 w-5 rounded-full bg-gray-200 text-center text-xs font-semibold leading-5 text-gray-600 ring-1 ring-gray-300 transition hover:bg-gray-300 hover:text-gray-800"
      title={`Source: ${url}`}
    >
      {number}
    </a>
  );
}

/**
 * ChatMessage
 *
 * Renders a user or assistant message bubble with timestamp, content,
 * and citations. User messages are right-aligned blue; assistant
al-aligned gray.
 */
export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";
  const alignment = isUser ? "items-end" : "items-start";
  const bubbleColor = isUser
    ? "bg-blue-600 text-white"
    : "bg-white text-gray-800 ring-1 ring-gray-200";

  return (
    <div className={`flex flex-col ${alignment}`}>
      <div
        className={`flex max-w-[90%] flex-col rounded-2xl px-3 py-2 text-sm shadow-sm ${bubbleColor} ${
          isUser ? "rounded-br-none" : "rounded-bl-none"
        }`}
      >
        <div className="prose prose-sm max-w-none text-inherit prose-p:my-1 prose-headings:my-2 prose-a:text-inherit hover:prose-a:text-blue-200">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 border-t border-gray-300 pt-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              Sources:
            </span>
            {message.citations.map((c, i) => (
              <Citation key={c.url} url={c.url} number={i + 1} />
            ))}
          </div>
        )}
      </div>

      <time
        dateTime={message.timestamp}
        className="mt-1 text-xs text-gray-400"
      >
        {format(new Date(message.timestamp), "h:mm a")}
      </time>
    </div>
  );
}