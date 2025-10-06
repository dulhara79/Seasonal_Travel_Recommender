import { useState } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [conversation, setConversation] = useState([]);
  const [followupAnswers, setFollowupAnswers] = useState({});

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
    const API_URL = `${API_BASE_URL}/travel`;

  const sendQuery = async (q = query, answers = followupAnswers) => {
    const res = await axios.post(API_URL, {
      query: q,
      followup_answers: answers,
    });

    const data = res.data;
    if (data.status === "followup") {
      setConversation((prev) => [
        ...prev,
        { role: "system", text: "I need a bit more info:" },
        ...data.questions.map((q) => ({ role: "assistant", text: q })),
      ]);
    } else {
      setConversation((prev) => [
        ...prev,
        { role: "assistant", text: "✅ Trip Plan Ready!" },
        { role: "assistant", text: "📍 Locations: " + data.locations.join(", ") },
        { role: "assistant", text: "🎯 Activities: " + JSON.stringify(data.activities) },
        { role: "assistant", text: "📝 Summary: " + data.summary },
      ]);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setConversation((prev) => [...prev, { role: "user", text: query }]);
    sendQuery();
    setQuery("");
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center p-6">
      <h1 className="text-3xl font-bold mb-6">🌍 Travel Recommender</h1>

      <div className="w-full max-w-2xl bg-white shadow-md rounded-lg p-4 mb-6">
        <div className="h-96 overflow-y-auto space-y-2">
          {conversation.map((msg, i) => (
            <div
              key={i}
              className={`p-2 rounded ${
                msg.role === "user" ? "bg-blue-100 text-right" : "bg-gray-200"
              }`}
            >
              {msg.text}
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-2xl flex">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about your trip..."
          className="flex-1 border rounded-l px-4 py-2"
        />
        <button
          type="submit"
          className="bg-blue-500 text-white px-6 py-2 rounded-r hover:bg-blue-600"
        >
          Send
        </button>
      </form>
    </div>
  );
}

export default App;