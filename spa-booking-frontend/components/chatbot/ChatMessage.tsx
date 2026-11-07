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
      className="ml-1 inline-block h-5 w-5 rounded-full bg-celadon-soft text-center text-xs font-semibold leading-5 text-[#1F4A41] ring-1 ring-line transition hover:bg-[#BFDBD3]"
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
 * and citations. User messages are right-aligned celadon; assistant
 * messages are left-aligned white.
 */
export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";
  const alignment = isUser ? "items-end" : "items-start";
  const bubbleColor = isUser
    ? "bg-celadon text-white"
    : "bg-white text-basalt ring-1 ring-line";

  return (
    <div className={`flex flex-col ${alignment}`}>
      <div
        className={`flex max-w-[88%] flex-col rounded-2xl px-3.5 py-2.5 text-[15px] leading-relaxed ${bubbleColor} ${
          isUser ? "rounded-br-sm" : "rounded-bl-sm"
        }`}
      >
        <div className="prose prose-sm max-w-none text-inherit prose-p:my-1 prose-headings:my-2 prose-a:text-inherit prose-a:underline">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 border-t border-line pt-2">
            <span className="text-xs font-semibold text-ink-soft">
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
        className="mt-1 text-xs text-ink-soft"
      >
        {format(new Date(message.timestamp), "h:mm a")}
      </time>
    </div>
  );
}
