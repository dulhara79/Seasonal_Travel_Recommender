import React, { useState, useEffect, useRef, forwardRef, useMemo } from "react";
// Removed: import { getTravelRecommendation } from '../../GradioRecommenderService';
import { useAuth } from "../contexts/AuthContext";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// --- START: Custom Confirmation Modal Component (ConfirmModal) ---
/**
 * Custom Confirmation Modal Component
 * Uses forwardRef to allow the component to be focused when opened,
 * which is good for accessibility, though not strictly required here.
 */
const ConfirmModal = forwardRef(
  ({ isOpen, onClose, onConfirm, title, message, type = "danger" }, ref) => {
    if (!isOpen) return null;

    const colors = useMemo(
      () => ({
        danger: {
          gradient: "from-red-500 to-rose-600",
          button:
            "from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700",
          icon: (
            <svg
              className="w-16 h-16 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          ),
        },
        warning: {
          gradient: "from-amber-500 to-orange-600",
          button:
            "from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700",
          icon: (
            <svg
              className="w-16 h-16 text-amber-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          ),
        },
      }),
      []
    );

    const theme = colors[type];

    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
          aria-hidden="true"
        ></div>
        {/* Modal Content */}
        <div
          ref={ref}
          className="relative bg-white rounded-3xl shadow-2xl max-w-md w-full transform animate-scale-in overflow-hidden"
          tabIndex="-1"
        >
          <div className={`h-2 bg-gradient-to-r ${theme.gradient}`}></div>

          <div className="p-8">
            <div className="flex flex-col items-center text-center">
              <div className="mb-6 transform animate-bounce-gentle">
                {theme.icon}
              </div>

              <h3
                id="modal-title"
                className="text-2xl font-bold text-gray-900 mb-3"
              >
                {title}
              </h3>

              <p className="text-gray-600 mb-8 leading-relaxed">{message}</p>

              <div className="flex gap-3 w-full">
                <button
                  onClick={onClose}
                  className="flex-1 px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    onConfirm();
                    onClose();
                  }}
                  className={`flex-1 px-6 py-3 bg-gradient-to-r ${theme.button} text-white rounded-xl font-semibold shadow-lg transition-all duration-300 transform hover:scale-105`}
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
);
ConfirmModal.displayName = "ConfirmModal";
// --- END: Custom Confirmation Modal Component (ConfirmModal) ---

// --- START: Markdown Renderer Component (MarkdownRenderer) ---
/**
 * Renders markdown content with Tailwind CSS and custom component styling.
 * @param {object} props - The component props.
 * @param {string} props.content - The markdown content string.
 */
const MarkdownRenderer = ({ content }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      className="prose prose-sm max-w-none text-gray-800 break-words"
      components={{
        // Customize H1 for a more themed look
        h1: ({ node, ...props }) => (
          <h1
            className="text-xl font-extrabold mt-4 mb-2 border-b border-emerald-200 pb-1 text-emerald-700"
            {...props}
          />
        ),
        // Customize H2
        h2: ({ node, ...props }) => (
          <h2
            className="text-lg font-bold mt-3 mb-1 text-emerald-600"
            {...props}
          />
        ),
        // Customize Unordered List
        ul: ({ node, ...props }) => (
          <ul className="list-disc list-inside space-y-1 pl-4" {...props} />
        ),
        // Customize Ordered List
        ol: ({ node, ...props }) => (
          <ol className="list-decimal list-inside space-y-1 pl-4" {...props} />
        ),
        // Customize Paragraphs
        p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
};
// --- END: Markdown Renderer Component (MarkdownRenderer) ---

// --- START: Main Chat Interface Component (ChatInterface) ---
const ChatInterface = () => {
  // Destructure auth context functions and state
  const {
    user,
    api,
    logout,
    getConversationsList,
    fetchConversationById,
    startNewConversation,
    appendChatMessage,
    updateConversationTitle,
    deleteConversation,
    deleteAccount,
  } = useAuth();

  // State management
  const [conversations, setConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  // Renamed to `currentState` to reflect its nature as the state *for the next* query
  const [currentState, setCurrentState] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [processingLastNode, setProcessingLastNode] = useState(null);
  const [processingSteps, setProcessingSteps] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    type: "",
    data: null,
  });

  // Refs
  const messagesEndRef = useRef(null);

  // Effect to scroll to the bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Effect to set mounted state for animations
  useEffect(() => {
    setMounted(true);
  }, []);

  // Function to fetch and set conversations list
  const loadConversations = async () => {
    try {
      const list = await getConversationsList();
      setConversations(list);
    } catch (error) {
      console.error("Error loading conversations:", error);
      // Optional: Show a user-facing error notification
    }
  };

  // Initial load of conversations
  useEffect(() => {
    // Only load if user is available (meaning auth is complete)
    if (user) {
      loadConversations();
    }
  }, [user]); // Depend on user to ensure it runs after login

  /**
   * Starts a new conversation/trip.
   */
  const startNewTrip = async () => {
    try {
      const newConv = await startNewConversation("New Trip");
      setCurrentConvId(newConv.id);
      setMessages([]);
      setCurrentState(null); // Reset state for a new conversation
      setInput("");
      loadConversations(); // Reload sidebar list to show the new conversation
    } catch (error) {
      console.error("Failed to start new trip:", error);
    }
  };

  /**
   * Computes a friendly title for a new conversation based on the user's query.
   * @param {string} q - The user's query.
   * @returns {string} - The computed title.
   */
  const computeTitleFromQuery = (q) => {
    if (!q || !q.trim()) return "New Trip";
    const txt = q.trim();
    // Regex to find "to [destination]"
    const toMatch = txt.match(
      /\bto\s+([A-Za-z0-9 \-'']{2,60}?)(?:\s+(?:for|in|during|with|on|$))/i
    );
    if (toMatch && toMatch[1]) {
      let dest = toMatch[1].trim();
      dest = dest.replace(/[.,;!?)]+$/g, "");
      // Capitalize first letter of each word
      dest = dest
        .split(/\s+/)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
      // Regex to find group type (family, solo, etc.)
      const pplMatch = txt.match(
        /\b(family|couple|solo|group|friends|\d+\s*(people|persons|travellers|travelers|kids|children))\b/i
      );
      const suffix = pplMatch ? ` — ${pplMatch[0]}` : "";
      return `Trip to ${dest}${suffix}`.slice(0, 100);
    }
    // Fallback: take the first 6 words
    const words = txt.split(/\s+/).slice(0, 6).join(" ");
    const short = words.replace(/[\n\r]/g, " ").replace(/["'`]/g, "");
    return (short.charAt(0).toUpperCase() + short.slice(1)).slice(0, 100);
  };

  /**
   * Loads an existing conversation by ID.
   * @param {string} convId - The ID of the conversation to load.
   */
  const loadTrip = async (convId) => {
    setCurrentConvId(convId);
    try {
      const conv = await fetchConversationById(convId);
      const loadedMessages = conv.messages.map((msg) => ({
        role: msg.role,
        text: msg.text,
        isUser: msg.role === "user",
        timestamp: msg.timestamp,
        savedState: msg.state, // `msg.state` is the state saved on the server
      }));

      // Find the state from the *most recent assistant message*
      const lastAssistantMessage = loadedMessages
        .slice()
        .reverse()
        .find((msg) => msg.role === "assistant");

      // Set the state for the *next* query
      const lastSavedState = lastAssistantMessage?.savedState || null;

      setMessages(loadedMessages);
      setCurrentState(lastSavedState); // Use the loaded state for the next query
      setInput("");
    } catch (error) {
      console.error("Failed to load trip:", error);
      // Fallback: start a new trip if the old one fails to load
      startNewTrip();
    }
  };

  /**
   * Handler for showing the delete trip confirmation modal.
   * @param {string} convId - The ID of the trip to delete.
   * @param {object} event - The click event.
   */
  const handleDeleteTrip = (convId, event) => {
    event.stopPropagation();
    setConfirmModal({
      isOpen: true,
      type: "deleteTrip",
      data: convId,
    });
  };

  /**
   * Confirms and executes the deletion of a trip.
   */
  const confirmDeleteTrip = async () => {
    const convId = confirmModal.data;
    try {
      await deleteConversation(convId);
      if (currentConvId === convId) {
        // Clear chat if the currently viewed trip was deleted
        setCurrentConvId(null);
        setMessages([]);
        setCurrentState(null);
      }
      await loadConversations();
    } catch (error) {
      console.error("Failed to delete trip:", error);
    }
  };

  /**
   * Handler for showing the delete account confirmation modal.
   */
  const handleDeleteAccount = () => {
    setConfirmModal({
      isOpen: true,
      type: "deleteAccount",
      data: null,
    });
  };

  /**
   * Confirms and executes the deletion of the user account.
   */
  const confirmDeleteAccount = async () => {
    try {
      await deleteAccount();
      logout(); // Log out after successful deletion
    } catch (error) {
      console.error("Failed to delete account:", error);
    }
  };

  /**
   * Handles the submission of a new chat message.
   */
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

    // 1. Update UI immediately with user message
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      let activeConvId = currentConvId;

      // 2. Start new conversation if none is active
      if (!activeConvId) {
        const title = computeTitleFromQuery(query);
        const newConv = await startNewConversation(title);
        activeConvId = newConv.id;
        setCurrentConvId(activeConvId);
        // Optimistic update of conversations list, then force a reload
        setConversations((prev) => [newConv, ...(prev || [])]);
        loadConversations();
      }

      // 3. Save user message to the server
      await appendChatMessage(activeConvId, userMessage.role, userMessage.text);

      // 4. Update title if it's still the default ("New Trip")
      try {
        const serverConv = await fetchConversationById(activeConvId);
        if (!serverConv.title || serverConv.title === "New Trip") {
          const title = computeTitleFromQuery(query);
          await updateConversationTitle(activeConvId, title);
          setConversations((prev) =>
            (prev || []).map((c) =>
              c.id === activeConvId ? { ...c, title } : c
            )
          );
          loadConversations();
        }
      } catch (err) {
        console.debug("Could not update conversation title:", err);
      }

      // 5. Call the recommender API
      const payload = {
        query: query,
        previous_state: currentState, // Send the previous state
      };

      const res = await api.post("/query", payload);
      const botResponseText = res.data.response;
      const newState = res.data.current_state || {};

      const botMessage = {
        role: "assistant",
        text: botResponseText,
        isUser: false,
        timestamp: new Date().toISOString(),
        savedState: newState, // Add the state to the message object for loading
      };

      // 6. Update local state
      setCurrentState(newState); // Set the new state for the next query
      // Extract optional processing data
      if (newState._processing_last_node)
        setProcessingLastNode(newState._processing_last_node);
      if (Array.isArray(newState._processing_steps))
        setProcessingSteps(newState._processing_steps.slice(-10)); // Keep only the last 10 steps

      // 7. Update UI with bot message
      setMessages((prev) => [...prev, botMessage]);

      // 8. Save bot message and new state to the server
      await appendChatMessage(
        activeConvId,
        botMessage.role,
        botMessage.text,
        newState // Send the new state to be saved with the bot message
      );
    } catch (error) {
      console.error("API Error:", error);
      // Display a user-friendly error message
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          text: "Sorry, I ran into an error. Please try again.",
          isUser: false,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Formats an ISO string timestamp into a local time string.
   * @param {string} isoString - The ISO timestamp string.
   * @returns {string} - The formatted time string.
   */
  const formatTimestamp = (isoString) => {
    if (!isoString) return "Just now";
    return new Date(isoString).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // --- Render ---
  return (
    <div className="flex h-screen antialiased text-gray-800 bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 relative overflow-hidden">
      {/* Custom Styles/Keyframes */}
      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse-subtle {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(5deg); }
        }
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scale-in {
          from { opacity: 0; transform: scale(0.9); }
          to { opacity: 1; transform: scale(1); }
        }
        @keyframes bounce-gentle {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        .animate-fade-in-up {
          animation: fadeInUp 0.5s ease-out;
        }
        .animate-pulse-subtle {
          animation: pulse-subtle 2s ease-in-out infinite;
        }
        .animate-fade-in {
          animation: fade-in 0.2s ease-out;
        }
        .animate-scale-in {
          animation: scale-in 0.3s ease-out;
        }
        .animate-bounce-gentle {
          animation: bounce-gentle 2s ease-in-out infinite;
        }
        .gradient-shift {
          background-size: 200% 200%;
          animation: shimmer 3s ease infinite;
        }
      `}</style>

      {/* Confirmation Modals */}
      <ConfirmModal
        isOpen={confirmModal.isOpen && confirmModal.type === "deleteTrip"}
        onClose={() => setConfirmModal({ isOpen: false, type: "", data: null })}
        onConfirm={confirmDeleteTrip}
        title="Delete This Trip?"
        message="This will permanently delete all messages and data for this trip. This action cannot be undone."
        type="warning"
      />

      <ConfirmModal
        isOpen={confirmModal.isOpen && confirmModal.type === "deleteAccount"}
        onClose={() => setConfirmModal({ isOpen: false, type: "", data: null })}
        onConfirm={confirmDeleteAccount}
        title="Delete Your Account?"
        message="This will permanently delete your account and all your trip history. This action is irreversible and all your data will be lost forever."
        type="danger"
      />

      {/* Animated background patterns */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute top-10 right-10 w-72 h-72 bg-gradient-to-br from-emerald-300/20 to-teal-300/20 rounded-full blur-3xl"
          style={{ animation: "float 8s ease-in-out infinite" }}
        ></div>
        <div
          className="absolute bottom-20 left-10 w-80 h-80 bg-gradient-to-br from-cyan-300/20 to-blue-300/20 rounded-full blur-3xl"
          style={{ animation: "float 10s ease-in-out infinite 2s" }}
        ></div>
        <div
          className="absolute top-1/2 left-1/3 w-64 h-64 bg-gradient-to-br from-teal-300/15 to-emerald-300/15 rounded-full blur-3xl"
          style={{ animation: "float 12s ease-in-out infinite 4s" }}
        ></div>
      </div>

      <div className="flex flex-row h-full w-full overflow-x-hidden relative z-10">
        {/* Sidebar */}
        <div
          className={`flex flex-col py-6 px-4 ${
            sidebarOpen ? "w-80" : "w-0"
          } bg-white/90 backdrop-blur-xl flex-shrink-0 border-r border-emerald-200/50 shadow-2xl transition-all duration-300 overflow-hidden`}
        >
          {/* Header */}
          <div
            className={`flex flex-col mb-6 transition-all duration-300 ${
              mounted ? "opacity-100" : "opacity-0"
            }`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className="w-11 h-11 bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 rounded-2xl flex items-center justify-center shadow-lg transform hover:scale-110 transition-transform duration-300 gradient-shift">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
                  </svg>
                </div>
                <div>
                  <div className="text-lg font-bold bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 bg-clip-text text-transparent">
                    Ceylon Travels
                  </div>
                  <div className="text-xs text-gray-500 font-medium">
                    AI Trip Planner
                  </div>
                </div>
              </div>
              <button
                onClick={logout}
                className="text-xs text-gray-500 hover:text-red-500 transition-all duration-300 px-3 py-1.5 rounded-lg hover:bg-red-50 font-medium"
              >
                Logout
              </button>
            </div>

            <div className="bg-gradient-to-r from-emerald-100 via-teal-100 to-cyan-100 rounded-2xl p-3 mb-4 border border-emerald-200/50">
              <p className="text-sm text-gray-700 font-medium">
                Welcome,{" "}
                <span className="text-emerald-700 font-semibold">
                  {user?.name || user?.username}
                </span>
                !
              </p>
            </div>

            {/* New Trip Button */}
            <button
              onClick={startNewTrip}
              className="bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-600 hover:via-teal-600 hover:to-cyan-600 text-white font-semibold py-3 px-4 rounded-2xl transition-all duration-300 text-sm shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center justify-center space-x-2 gradient-shift"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              <span>Start New Adventure</span>
            </button>
          </div>

          {/* Trip History */}
          <div className="flex flex-col space-y-2 overflow-y-auto flex-grow mb-4 pr-2">
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-wider sticky top-0 bg-white/90 backdrop-blur-sm py-2 mb-2 rounded-lg px-2">
              Your Journeys
            </h3>
            {conversations.map((conv, idx) => (
              <div
                key={conv.id}
                onClick={() => loadTrip(conv.id)}
                className={`p-3 rounded-2xl cursor-pointer transition-all duration-300 flex justify-between items-center group relative overflow-hidden
                  ${
                    conv.id === currentConvId
                      ? "bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 text-white shadow-lg scale-105"
                      : "bg-white/70 hover:bg-white hover:shadow-md text-gray-700 border border-emerald-100"
                  }
                `}
                style={{
                  animationDelay: `${idx * 50}ms`,
                  animation: mounted
                    ? "fadeInUp 0.5s ease-out forwards"
                    : "none",
                }}
              >
                <div className="flex items-center space-x-2 flex-grow min-w-0">
                  <svg
                    className={`w-4 h-4 flex-shrink-0 ${
                      conv.id === currentConvId
                        ? "text-white"
                        : "text-emerald-500"
                    }`}
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
                  </svg>
                  <span className="truncate text-sm font-medium">
                    {conv.title || `Trip ${conv.id.substring(0, 8)}`}
                  </span>
                </div>

                {/* Delete Trip Button */}
                <button
                  onClick={(e) => handleDeleteTrip(conv.id, e)}
                  className={`ml-2 p-1.5 rounded-xl transition-all duration-300 flex-shrink-0
                    ${
                      conv.id === currentConvId
                        ? "bg-white/20 hover:bg-white/30 text-white"
                        : "text-gray-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100"
                    }
                  `}
                  title="Delete Trip"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            ))}
            {conversations.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <svg
                  className="w-12 h-12 mx-auto mb-2 opacity-50"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p className="text-sm">No trips yet</p>
              </div>
            )}
          </div>

          {/* Settings Footer */}
          <div className="flex items-center justify-center mt-auto pt-4 border-t border-emerald-200/50 relative">
            <div className="relative">
              <button
                onClick={() => setSettingsOpen((s) => !s)}
                className="flex items-center justify-center gap-2 p-2.5 rounded-xl text-sm text-emerald-700 hover:bg-emerald-50 transition-all duration-300 font-medium"
                title="Settings"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11.049 2.927c.3-.921 1.603-.921 1.902 0a1.724 1.724 0 002.573 1.008c.83-.53 1.86.18 1.618 1.119a1.724 1.724 0 001.012 2.57c.92.3.92 1.603 0 1.902a1.724 1.724 0 00-1.008 2.573c.53.83-.18 1.86-1.119 1.618a1.724 1.724 0 00-2.57 1.012c-.3.92-1.603.92-1.902 0a1.724 1.724 0 00-2.573-1.008c-.83.53-1.86-.18-1.618-1.119a1.724 1.724 0 00-1.012-2.57c-.92-.3-.92-1.603 0-1.902a1.724 1.724 0 001.008-2.573c-.53-.83.18-1.86 1.119-1.618.96.262 1.55-.788 2.57-1.012z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <span className="hidden sm:inline">Settings</span>
              </button>

              {/* Settings Popover */}
              {settingsOpen && (
                <div className="absolute left-0 bottom-14 w-64 bg-white rounded-2xl shadow-xl border border-emerald-100 p-3 z-50 animate-fade-in animate-scale-in">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm font-semibold text-gray-700">
                      Settings
                    </div>
                    <button
                      onClick={() => setSettingsOpen(false)}
                      className="text-gray-400 hover:text-gray-600"
                      title="Close"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="space-y-2">
                    <button
                      onClick={handleDeleteAccount}
                      className="w-full text-left flex items-center justify-start gap-2 p-2 rounded-xl hover:bg-red-50 transition-all duration-150 text-sm text-red-600 font-medium"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13 7a4 4 0 11-8 0 4 4 0 018 0zM9 14a6 6 0 00-6 6v1h12v-1a6 6 0 00-6-6zM21 12h-6"
                        />
                      </svg>
                      Delete Account
                    </button>

                    <div className="text-xs text-gray-500">
                      More settings coming soon
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex flex-col flex-auto h-full p-6 relative">
          {/* Toggle Sidebar Button (Mobile) */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="absolute top-4 left-4 z-20 lg:hidden bg-white/90 backdrop-blur-xl p-2 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 border border-emerald-200/50"
          >
            <svg
              className="w-6 h-6 text-gray-700"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          <div className="flex flex-col flex-auto flex-shrink-0 rounded-3xl bg-white/70 backdrop-blur-xl h-full p-6 shadow-2xl border border-white/30">
            {/* Messages Container */}
            <div className="flex flex-col h-full overflow-y-auto mb-4">
              <div className="flex flex-col h-full">
                {messages.length === 0 && (
                  <div className="flex items-center justify-center h-full text-gray-600 flex-col animate-fade-in-up">
                    <div className="bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 w-20 h-20 rounded-3xl flex items-center justify-center mb-6 shadow-xl transform hover:scale-110 transition-transform duration-300 gradient-shift">
                      <svg
                        className="w-10 h-10 text-white"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
                      </svg>
                    </div>
                    <h2 className="text-3xl font-bold mb-3 bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 bg-clip-text text-transparent">
                      Welcome to Ceylon Travels
                    </h2>
                    <p className="text-center max-w-md text-gray-600 mb-4 leading-relaxed">
                      Start planning your dream Sri Lankan adventure. Discover
                      hidden gems, cultural treasures, pristine beaches, and
                      unforgettable experiences.
                    </p>
                    <div className="bg-gradient-to-r from-emerald-100 via-teal-100 to-cyan-100 rounded-2xl p-5 max-w-md border border-emerald-200/50">
                      <p className="text-sm text-gray-700 font-semibold mb-3">
                        Try asking:
                      </p>
                      <ul className="text-sm text-gray-600 space-y-2">
                        <li className="flex items-center">
                          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-2"></span>
                          "Plan a 7-day trip to Sri Lanka for a family"
                        </li>
                        <li className="flex items-center">
                          <span className="w-1.5 h-1.5 bg-teal-500 rounded-full mr-2"></span>
                          "What are the best beaches in the south?"
                        </li>
                        <li className="flex items-center">
                          <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full mr-2"></span>
                          "Create a cultural tour itinerary"
                        </li>
                      </ul>
                    </div>
                  </div>
                )}
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${
                      msg.isUser ? "justify-end" : "justify-start"
                    } mb-4 animate-fade-in-up`}
                  >
                    <div
                      className={`flex flex-col max-w-2xl shadow-lg transition-all duration-300 hover:shadow-xl
                        ${
                          msg.isUser
                            ? "bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 text-white rounded-3xl rounded-br-md"
                            : "bg-white/90 backdrop-blur-sm text-gray-800 rounded-3xl rounded-bl-md border border-emerald-100"
                        } px-5 py-4`}
                    >
                      {msg.isUser ? (
                        <p className="leading-relaxed">{msg.text}</p>
                      ) : (
                        <div className="leading-relaxed">
                          <MarkdownRenderer content={msg.text} />
                        </div>
                      )}
                      <span
                        className={`text-xs mt-2 flex items-center space-x-1 ${
                          msg.isUser ? "text-white/80" : "text-gray-400"
                        }`}
                      >
                        <svg
                          className="w-3 h-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <span>{formatTimestamp(msg.timestamp)}</span>
                      </span>
                    </div>
                  </div>
                ))}
                {/* Typing/Loading Indicator */}
                {isLoading && (
                  <div className="flex justify-start mb-4">
                    <div className="flex flex-col max-w-2xl bg-white/90 backdrop-blur-sm text-gray-800 rounded-3xl rounded-bl-md border border-emerald-100 px-5 py-4 shadow-lg animate-pulse-subtle">
                      <div className="flex space-x-2">
                        <div
                          className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"
                          style={{ animationDelay: "0s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-teal-500 rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-cyan-500 rounded-full animate-bounce"
                          style={{ animationDelay: "0.4s" }}
                        ></div>
                      </div>
                    </div>
                  </div>
                )}
                {/* Scroll Anchor */}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Chat Input Area */}
            <div className="flex flex-row items-center">
              <div className="flex-grow ml-4">
                <form onSubmit={handleSubmit}>
                  <div className="relative flex w-full">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      disabled={isLoading}
                      placeholder={
                        isLoading
                          ? "AI is typing..."
                          : "Plan a trip or ask a question..."
                      }
                      className="flex w-full border border-emerald-300 rounded-3xl focus:outline-none focus:border-emerald-500 pl-4 h-12 text-sm transition-all duration-300 disabled:bg-gray-50 disabled:text-gray-500 pr-16 shadow-inner"
                    />
                    <button
                      type="submit"
                      disabled={!input.trim() || isLoading}
                      className={`absolute right-1 top-1/2 transform -translate-y-1/2 p-2 rounded-full text-white transition-all duration-300 shadow-md
                        ${
                          !input.trim() || isLoading
                            ? "bg-gray-300 cursor-not-allowed"
                            : "bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 hover:scale-105"
                        }`}
                      title="Send Message"
                    >
                      <svg
                        className="w-5 h-5 transform rotate-90"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                      </svg>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
