import React, { useState, useEffect, useRef } from "react";
// Assuming you update AuthContext to include deleteConversation and deleteAccount
import { useAuth } from "../contexts/AuthContext";
import { ArrowUpCircleIcon } from "@heroicons/react/24/solid";
// Importing Trash and UserMinus icons for the new delete functionality
import { TrashIcon, UserMinusIcon } from "@heroicons/react/24/outline";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// --- Markdown Renderer Component (Simplified Inline for Context) ---
const MarkdownRenderer = ({ content }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      // Using a basic prose setup for clean formatting
      className="prose prose-sm max-w-none text-gray-800 break-words"
      components={{
        h1: ({ node, ...props }) => (
          <h1
            className="text-xl font-extrabold mt-4 mb-2 border-b border-blue-200 pb-1 text-blue-700"
            {...props}
          />
        ),
        h2: ({ node, ...props }) => (
          <h2
            className="text-lg font-bold mt-3 mb-1 text-blue-600"
            {...props}
          />
        ),
        ul: ({ node, ...props }) => (
          <ul className="list-disc list-inside space-y-1 pl-4" {...props} />
        ),
        ol: ({ node, ...props }) => (
          <ol className="list-decimal list-inside space-y-1 pl-4" {...props} />
        ),
        p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
};

const ChatInterface = () => {
  const {
    user,
    api,
    logout,
    getConversationsList,
    fetchConversationById,
    startNewConversation,
    appendChatMessage,
  updateConversationTitle,
    // NEW: Assuming your AuthContext exposes these new API wrappers
    deleteConversation,
    deleteAccount,
  } = useAuth();

  const [conversations, setConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [previousState, setPreviousState] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () =>
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  useEffect(scrollToBottom, [messages]); // --- Conversation Management ---

  const loadConversations = async () => {
    try {
      const list = await getConversationsList();
      setConversations(list);
    } catch (error) {
      console.error("Error loading conversations:", error);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [user]);

  const startNewTrip = async () => {
    const newConv = await startNewConversation("New Trip");
    setCurrentConvId(newConv.id);
    setMessages([]);
    setPreviousState(null);
    setInput("");
    loadConversations();
  };

  // Heuristic: compute a friendly conversation title from the user's first message
  const computeTitleFromQuery = (q) => {
    if (!q || !q.trim()) return "New Trip";
    const txt = q.trim();
    // Try to capture a destination using 'to <destination>' pattern
    const toMatch = txt.match(/\bto\s+([A-Za-z0-9 \-\'’]{2,60}?)(?:\s+(?:for|in|during|with|on|$))/i);
    if (toMatch && toMatch[1]) {
      let dest = toMatch[1].trim();
      dest = dest.replace(/[.,;!?)]+$/g, "");
      // Capitalize words
      dest = dest
        .split(/\s+/)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
      // Try to capture simple traveler hints (e.g., 'family', 'couple', 'solo', '3 people')
      const pplMatch = txt.match(/\b(family|couple|solo|group|friends|\d+\s*(people|persons|travellers|travelers|kids|children))\b/i);
      const suffix = pplMatch ? ` — ${pplMatch[0]}` : "";
      return `Trip to ${dest}${suffix}`.slice(0, 100);
    }
    // Fallback: use first 6 words as a short title
    const words = txt.split(/\s+/).slice(0, 6).join(" ");
    const short = words.replace(/[\n\r]/g, " ").replace(/["'`]/g, "");
    return (short.charAt(0).toUpperCase() + short.slice(1)).slice(0, 100);
  };

  const loadTrip = async (convId) => {
    setCurrentConvId(convId);
    try {
      const conv = await fetchConversationById(convId);
      const loadedMessages = conv.messages.map((msg) => ({
        role: msg.role,
        text: msg.text,
        isUser: msg.role === "user",
        timestamp: msg.timestamp,
      }));
      setMessages(loadedMessages);
      setPreviousState(null);
    } catch (error) {
      console.error("Failed to load trip:", error);
      startNewTrip();
    }
  };

  // --- NEW: Trip Deletion Handler ---
  const handleDeleteTrip = async (convId, event) => {
    // Stop the click event from propagating to the parent div (which loads the trip)
    event.stopPropagation();

    if (
      !window.confirm("Are you sure you want to permanently delete this trip?")
    ) {
      return;
    }

    try {
      // Call the API function to delete the conversation
      await deleteConversation(convId);

      // If the deleted conversation was the currently open one, reset the chat view
      if (currentConvId === convId) {
        setCurrentConvId(null);
        setMessages([]);
        setPreviousState(null);
      }

      // Reload the list of conversations
      await loadConversations();
    } catch (error) {
      console.error("Failed to delete trip:", error);
      alert("Failed to delete trip. Please try again.");
    }
  };

  // --- NEW: Account Deletion Handler ---
  const handleDeleteAccount = async () => {
    if (
      !window.confirm(
        "WARNING: Are you absolutely sure you want to delete your account? This action is permanent and will delete all your trip history."
      )
    ) {
      return;
    }

    try {
      await deleteAccount();
      // If successful, the server should invalidate the session/token.
      // We force a logout on the client side to clear state.
      logout();
    } catch (error) {
      console.error("Failed to delete account:", error);
      alert(
        "Failed to delete account. Please try logging in again or contact support."
      );
    }
  }; // --- Chat Submission and Persistence (Unchanged) ---

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const query = input.trim();
    const userMessage = {
      role: "user",
      text: query,
      isUser: true,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      let activeConvId = currentConvId;
      if (!activeConvId) {
        const title = computeTitleFromQuery(query);
        const newConv = await startNewConversation(title);
        activeConvId = newConv.id;
        setCurrentConvId(activeConvId);
        // Optimistically update local conversation list so the sidebar shows the title immediately
        setConversations((prev) => {
          try {
            // avoid duplicates
            const exists = prev.some((c) => c.id === newConv.id);
            if (exists) return prev.map((c) => (c.id === newConv.id ? newConv : c));
            return [newConv, ...(prev || [])];
          } catch (e) {
            return prev || [];
          }
        });
        loadConversations();
      }

      await appendChatMessage(activeConvId, userMessage.role, userMessage.text);

      // If the conversation on the server still has a default title, attempt to update it
      try {
        // fetch the conversation to inspect current server title
        const serverConv = await fetchConversationById(activeConvId);
        if (!serverConv.title || serverConv.title === "New Trip") {
          const title = computeTitleFromQuery(query);
          await updateConversationTitle(activeConvId, title);
          // Optimistically update local copy as well so the UI reflects the change immediately
          setConversations((prev) =>
            (prev || []).map((c) => (c.id === activeConvId ? { ...c, title } : c))
          );
          // reload conversations to ensure server-state sync
          loadConversations();
        }
      } catch (err) {
        // non-fatal; log for debugging
        console.debug("Could not update conversation title:", err);
      }

      const payload = {
        query: query,
        previous_state: previousState,
      };

      const res = await api.post("/query", payload);
      const botResponseText = res.data.response;

      const botMessage = {
        role: "assistant",
        text: botResponseText,
        isUser: false,
        timestamp: new Date().toISOString(),
      };

      setPreviousState(res.data.current_state);
      setMessages((prev) => [...prev, botMessage]);

      await appendChatMessage(
        activeConvId,
        botMessage.role,
        botMessage.text,
        res.data.current_state
      );
    } catch (error) {
      console.error("API Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          text: "Sorry, I ran into an error. Please try again.",
          isUser: false,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimestamp = (isoString) => {
    if (!isoString) return "Just now";
    return new Date(isoString).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="flex h-screen antialiased text-gray-800">
      {" "}
      <div className="flex flex-row h-full w-full overflow-x-hidden">
        {/* Sidebar */}{" "}
        <div className="flex flex-col py-8 pl-6 pr-2 w-72 bg-gray-50 flex-shrink-0 border-r border-gray-200">
          {/* Header/Title/Logout */}{" "}
          <div className="flex justify-between items-center h-12 w-full mb-4">
            {" "}
            <div className="text-xl font-bold text-blue-600">
              Trip Planner
            </div>{" "}
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-red-500 transition duration-150"
            >
              Logout{" "}
            </button>{" "}
          </div>{" "}
          <p className="text-sm text-gray-600 mb-2">
            Welcome, {user?.name || user?.username}!{" "}
          </p>
          {/* New Trip Button */}{" "}
          <button
            onClick={startNewTrip}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition duration-150 text-sm mb-4"
          >
            + Start New Trip{" "}
          </button>
          {/* Trip History List (Scrollable Area) */}
          <div className="flex flex-col space-y-2 overflow-y-auto flex-grow mb-4">
            <h3 className="text-sm font-semibold text-gray-700 sticky top-0 bg-gray-50 pb-1 border-b">
              Trip History
            </h3>
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => loadTrip(conv.id)}
                className={`p-3 rounded-xl cursor-pointer transition duration-150 flex justify-between items-center group
                            ${
                              conv.id === currentConvId
                                ? "bg-blue-200 font-semibold"
                                : "bg-white hover:bg-gray-100"
                            }
                        `}
              >
                <span className="truncate text-sm flex-grow">
                  {conv.title || `Trip ${conv.id.substring(0, 8)}`}
                </span>

                {/* NEW: Delete Trip Button */}
                <button
                  onClick={(e) => handleDeleteTrip(conv.id, e)}
                  className={`ml-2 p-1 rounded-full text-gray-400 hover:text-red-600 hover:bg-red-100 transition duration-150
                                ${
                                  conv.id === currentConvId
                                    ? "opacity-100"
                                    : "opacity-0 group-hover:opacity-100"
                                }
                            `}
                  title="Delete Trip"
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
          {/* NEW: Sidebar Footer for Account Management */}
          <div className="flex flex-col mt-auto pt-4 border-t border-gray-200">
            <button
              onClick={handleDeleteAccount}
              className="flex items-center justify-center p-2 rounded-lg text-sm text-red-600 hover:bg-red-50 transition duration-150"
              title="Permanently Delete Account"
            >
              <UserMinusIcon className="w-5 h-5 mr-2" />
              Delete Account
            </button>
          </div>{" "}
        </div>
        {/* Main Chat Area */}{" "}
        <div className="flex flex-col flex-auto h-full p-6">
          {" "}
          <div className="flex flex-col flex-auto flex-shrink-0 rounded-2xl bg-gray-100 h-full p-4">
            {/* Messages */}{" "}
            <div className="flex flex-col h-full overflow-x-auto mb-4">
              {" "}
              <div className="flex flex-col h-full">
                {" "}
                {messages.length === 0 && (
                  <div className="flex items-center justify-center h-full text-gray-500 flex-col">
                    {" "}
                    <h2 className="text-xl mb-2">Welcome!</h2>{" "}
                    <p className="text-center">
                      Start planning your trip. <br /> Example: "Plan a trip to
                      Sri Lanka for a family of four in late October."{" "}
                    </p>{" "}
                  </div>
                )}{" "}
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${
                      msg.isUser ? "justify-end" : "justify-start"
                    } mb-4`}
                  >
                    {" "}
                    <div
                      className={`flex flex-col max-w-lg shadow-lg 
            ${
              msg.isUser
                ? "bg-blue-600 text-white rounded-tl-xl rounded-tr-xl rounded-bl-xl"
                : "bg-white text-gray-800 rounded-tl-xl rounded-tr-xl rounded-br-xl"
            } px-4 py-3`}
                    >
                      {" "}
                      {msg.isUser ? (
                        <p>{msg.text}</p>
                      ) : (
                        // Render Markdown for bot responses only
                        <MarkdownRenderer content={msg.text} />
                      )}{" "}
                      <span
                        className={`text-xs mt-1 ${
                          msg.isUser ? "text-blue-200" : "text-gray-400"
                        }`}
                      >
                        {formatTimestamp(msg.timestamp)}{" "}
                      </span>{" "}
                    </div>{" "}
                  </div>
                ))}{" "}
                {isLoading && (
                  <div className="flex justify-start mb-4">
                    {" "}
                    <div className="bg-white text-gray-800 rounded-tl-xl rounded-tr-xl rounded-br-xl px-4 py-3 shadow-md">
                      {" "}
                      <div className="animate-pulse">Thinking...</div>{" "}
                    </div>{" "}
                  </div>
                )}
                <div ref={messagesEndRef} />{" "}
              </div>{" "}
            </div>
            {/* Input Box */}{" "}
            <div className="flex flex-row items-center h-16 rounded-xl bg-white w-full px-4">
              {" "}
              <div className="flex-grow ml-4">
                {" "}
                <form onSubmit={handleSubmit} className="flex w-full">
                  {" "}
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={
                      isLoading
                        ? "Processing..."
                        : "Ask me anything about your trip..."
                    }
                    disabled={isLoading}
                    className="flex w-full border-none focus:outline-none text-gray-600 placeholder-gray-400 p-2"
                  />{" "}
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className={`ml-2 flex items-center justify-center ${
                      isLoading || !input.trim()
                        ? "text-gray-400"
                        : "text-blue-500 hover:text-700"
                    } transition duration-150`}
                  >
                    {" "}
                    <ArrowUpCircleIcon className="w-8 h-8" />{" "}
                  </button>{" "}
                </form>{" "}
              </div>{" "}
            </div>{" "}
          </div>{" "}
        </div>{" "}
      </div>{" "}
    </div>
  );
};

export default ChatInterface;
