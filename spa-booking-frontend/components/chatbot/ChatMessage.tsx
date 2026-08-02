
type ChatMessageProps = {
  message: {
    id: string;
    text: string;
    isUser: boolean; // Assuming messages have a sender
  };
};

export default function ChatMessage({ message }: ChatMessageProps) {
  return (
    <div className={`flex ${message.isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`rounded-lg px-4 py-2 ${
          message.isUser ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-800"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}
