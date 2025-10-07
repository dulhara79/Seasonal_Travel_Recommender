import React from "react";

/**
 * Utility function for formatting timestamps consistently.
 */
const formatTimestamp = (timestamp) => {
  if (!timestamp) return "";
  try {
    // Handle either a Date object or an ISO string
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (error) {
    return "N/A";
  }
};

/**
 * Renders a single chat message bubble with updated Tailwind styling.
 * Assumes the message object has properties like 'text' and 'sender' (or 'role').
 */
export default function ChatMessage({ msg }) {
  // Use 'sender' for consistency with common chat app patterns, fall back to 'role'
  const senderType = msg.sender || msg.role;
  const isUser = senderType === "user";
  const senderLabel = isUser ? "You" : "AI Agent";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] p-4 rounded-3xl shadow-md transition-all duration-300 ${
          isUser
            ? "bg-blue-600 text-white rounded-br-md ml-auto"
            : "bg-gray-100 text-gray-900 rounded-tl-md mr-auto"
        }`}
      >
        <div
          className={`font-semibold text-sm mb-1 ${
            isUser ? "text-white/90" : "text-blue-700"
          }`}
        >
          {senderLabel}
        </div>
        <div className="whitespace-pre-wrap leading-relaxed">{msg.text}</div>

        <div
          className={`text-xs mt-2 block w-full text-right ${
            isUser ? "text-white/70" : "text-gray-500"
          }`}
        >
          {formatTimestamp(msg.timestamp)}
        </div>
      </div>
    </div>
  );
}
