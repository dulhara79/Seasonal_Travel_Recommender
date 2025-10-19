import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const LandingPage = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isSignInOpen, setIsSignInOpen] = useState(false);
  const [isSignUpOpen, setIsSignUpOpen] = useState(false);
  const navigate = useNavigate();
  const { login, signup, user, logout } = useAuth();

  // Form states
  const [signInData, setSignInData] = useState({
    login: "",
    password: "",
  });

  const [signUpData, setSignUpData] = useState({
    username: "",
    name: "",
    email: "",
    password: "",
  });

  const [signInError, setSignInError] = useState("");
  const [signUpError, setSignUpError] = useState("");
  const [isSignInLoading, setIsSignInLoading] = useState(false);
  const [isSignUpLoading, setIsSignUpLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      type: "bot",
      content: `Hello! 👋 I'm your personal travel assistant. I can help you with:
• Finding the best destinations
• Planning your itinerary  
• Booking flights & hotels
• Getting travel tips

What would you like to know about Sri Lanka?`,
    },
  ]);
  const [chatInput, setChatInput] = useState("");

  const openModal = (type) => {
    if (type === "signin") {
      setIsSignInOpen(true);
      setSignInError("");
      setSignInData({ login: "", password: "" });
    }
    if (type === "signup") {
      setIsSignUpOpen(true);
      setSignUpError("");
      setSignUpData({ username: "", name: "", email: "", password: "" });
    }
  };

  const closeModal = (type) => {
    if (type === "signin") {
      setIsSignInOpen(false);
      setSignInError("");
      setSignInData({ login: "", password: "" });
    }
    if (type === "signup") {
      setIsSignUpOpen(false);
      setSignUpError("");
      setSignUpData({ username: "", name: "", email: "", password: "" });
    }
  };

  const switchModal = (from, to) => {
    closeModal(from);
    openModal(to);
  };

  // Handle Sign In
  const handleSignIn = async (e) => {
    e.preventDefault();
    setSignInError("");
    setIsSignInLoading(true);

    try {
      await login(signInData);
      setIsSignInOpen(false);
      navigate("/chat");
    } catch (error) {
      setSignInError(error.message || "Login failed. Please try again.");
    } finally {
      setIsSignInLoading(false);
    }
  };

  // Handle Sign Up
  const handleSignUp = async (e) => {
    e.preventDefault();
    setSignUpError("");
    setIsSignUpLoading(true);

    try {
      await signup(signUpData);
      setIsSignUpOpen(false);
      navigate("/chat");
    } catch (error) {
      setSignUpError(error.message || "Registration failed. Please try again.");
    } finally {
      setIsSignUpLoading(false);
    }
  };

  const toggleChat = () => {
    setIsChatOpen(!isChatOpen);
  };

  const generateAIResponse = (userInput) => {
    const responses = {
      sigiriya:
        "🏛️ Sigiriya is amazing! I recommend visiting early morning (6 AM) to avoid crowds. The climb takes 2-3 hours. Would you like me to check availability for guided tours?",
      temple:
        "🕉️ The Temple of the Sacred Tooth is perfect for cultural experiences! Visit during Puja ceremonies (5:30 AM, 9:30 AM, 6:30 PM). I can arrange a cultural guide for you.",
      tea: "🍃 Nuwara Eliya is beautiful! Best time is April-September. I suggest the scenic train ride from Kandy. Want me to book train tickets and tea plantation tours?",
      galle:
        "🏰 Galle Fort is magical at sunset! Stay 2-3 days to explore fully. I can find you charming boutique hotels within the fort walls.",
      price:
        "💰 Great news! We have special packages starting from $299 for 5 days. With our current 40% discount, that's just $179! Shall I show you the details?",
      book: "📅 I'd love to help you book! First, let me ask: What dates are you thinking? How many travelers? What's your budget range?",
      default:
        "🤖 That's a great question! I specialize in Sri Lankan travel. I can help with destinations, bookings, itineraries, and travel tips. What specifically would you like to know?",
    };

    const input = userInput.toLowerCase();
    for (let key in responses) {
      if (input.includes(key)) {
        return responses[key];
      }
    }
    return responses["default"];
  };

  const sendMessage = () => {
    if (chatInput.trim() === "") return;
    const newMessages = [...chatMessages, { type: "user", content: chatInput }];
    setChatMessages(newMessages);

    setTimeout(() => {
      const botResponse = generateAIResponse(chatInput);
      setChatMessages((prev) => [
        ...prev,
        { type: "bot", content: botResponse },
      ]);
    }, 1000);

    setChatInput("");
  };

  const handleChatKeyPress = (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  };

  // --- Button Styles from ChatInterface ---
  const btnBase =
    "cursor-pointer font-semibold transition-all duration-300 ease-in-out disabled:opacity-60 disabled:cursor-not-allowed";

  // Secondary button (like "Sign In" or "Cancel")
  const btnSecondary = `${btnBase} bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl py-2.5 px-5 transform hover:scale-105`;

  // Primary button (like "Sign Up" or "Confirm")
  const btnPrimary = `${btnBase} bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-600 hover:via-teal-600 hover:to-cyan-600 text-white rounded-2xl py-3 px-6 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 gradient-shift`;

  return (
    <div className="font-sans bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 text-gray-800 leading-relaxed antialiased">
      {/* --- Injected styles from ChatInterface --- */}
      <style>{`
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
        @keyframes pulse-subtle {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }
        .gradient-shift {
          background-size: 200% 200%;
          animation: shimmer 3s ease infinite;
        }
        .animate-float {
          animation: float 10s ease-in-out infinite;
        }
        .animate-fade-in {
          animation: fade-in 0.3s ease-out;
        }
        .animate-scale-in {
          animation: scale-in 0.3s ease-out;
        }
        .animate-pulse-subtle {
          animation: pulse-subtle 2s ease-in-out infinite;
        }
      `}</style>
      {/* --- End of injected styles --- */}

      <header className="bg-white/90 backdrop-blur-xl py-4 fixed w-full top-0 z-40 shadow-lg border-b border-emerald-200/50">
        <div className="container max-w-6xl mx-auto px-5">
          <div className="flex flex-col gap-4 md:flex-row justify-between items-center">
            <div className="logo text-[28px] font-bold bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 bg-clip-text text-transparent">
              Ceylon Travels
            </div>
            <nav>
              <ul className="flex flex-col md:flex-row items-center list-none m-0 gap-4 md:gap-[30px]">
                <li>
                  <Link
                    to="/"
                    className="no-underline text-gray-600 font-medium transition-colors duration-300 hover:text-emerald-700"
                  >
                    Products
                  </Link>
                </li>
                <li>
                  <a
                    href="#"
                    className="no-underline text-gray-600 font-medium transition-colors duration-300 hover:text-emerald-700"
                  >
                    Contact Us
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="no-underline text-gray-600 font-medium transition-colors duration-300 hover:text-emerald-700"
                  >
                    About Us
                  </a>
                </li>
                {user ? (
                  <>
                    <li>
                      <button
                        className={btnSecondary}
                        onClick={() => navigate("/chat")}
                      >
                        Go to Chat
                      </button>
                    </li>
                    <li>
                      <button className={btnPrimary} onClick={logout}>
                        Logout
                      </button>
                    </li>
                  </>
                ) : (
                  <>
                    <li>
                      <button
                        className={btnSecondary}
                        onClick={() => navigate("/auth")}
                      >
                        Sign In
                      </button>
                    </li>
                    <li>
                      <button
                        className={btnPrimary}
                        onClick={() => navigate("/auth")}
                      >
                        Sign Up
                      </button>
                    </li>
                  </>
                )}
              </ul>
            </nav>
          </div>
        </div>
      </header>

      <main className="mt-20 py-10 relative overflow-hidden">
        {/* Animated background patterns from ChatInterface */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div
            className="absolute top-10 right-10 w-72 h-72 bg-gradient-to-br from-emerald-300/20 to-teal-300/20 rounded-full blur-3xl"
            style={{ animation: "float 8s ease-in-out infinite" }}
          ></div>
          <div
            className="absolute bottom-20 left-10 w-80 h-80 bg-gradient-to-br from-cyan-300/20 to-blue-300/20 rounded-full blur-3xl"
            style={{ animation: "float 10s ease-in-out infinite 2s" }}
          ></div>
        </div>

        <div className="container max-w-6xl mx-auto px-5 relative z-10">
          <section className="grid grid-cols-1 gap-10 items-center mb-24 min-h-[500px] text-center md:grid-cols-2 md:gap-[60px] md:text-left">
            <div className="hero-content">
              <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6 leading-tight bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 bg-clip-text text-transparent">
                Start your journey by one click, explore beautiful Sri Lanka!
              </h1>
              <p className="text-lg text-gray-700 mb-8 leading-relaxed">
                Experience the pearl of the Indian Ocean with exclusive deals,
                expert guidance, and unforgettable memories. Book now and save
                up to 40% on your dream vacation!
              </p>
              <button
                className="bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-600 hover:via-teal-600 hover:to-cyan-600 text-white border-none py-4 px-9 rounded-2xl text-base font-semibold cursor-pointer transition-all duration-300 ease-in-out shadow-lg hover:shadow-xl transform hover:-translate-y-1 gradient-shift"
                onClick={() => (user ? navigate("/chat") : navigate("/auth"))}
              >
                {user
                  ? "Start Planning Your Trip!"
                  : "Start Your Adventure - Free Trial!"}
              </button>
            </div>
            <div className="hero-images relative h-[450px]">
              <img
                src="https://media.istockphoto.com/id/2158988664/photo/aerial-view-of-famous-beach-of-the-south-coast-of-sri-lanka-area-near-the-town-of-weligama.webp?a=1&b=1&s=612x612&w=0&k=20&c=oezERUpPMW7Tt_TG-o0o1MS3B2si9YJqkcg9N3OLEXg="
                className="absolute right-0 top-0 w-[350px] h-[400px] rounded-3xl object-cover shadow-2xl"
                alt="Sri Lanka Beach"
              />
              <div className="floating-badge absolute bg-white/80 backdrop-blur-md text-emerald-700 font-semibold py-2.5 px-5 rounded-2xl text-sm shadow-lg animate-float top-5 left-0 border border-emerald-200/50">
                🎯 40% OFF Limited Time!
              </div>
              <div
                className="floating-badge absolute bg-white/80 backdrop-blur-md text-emerald-700 font-semibold py-2.5 px-5 rounded-2xl text-sm shadow-lg animate-float bottom-12 left-5 border border-emerald-200/50"
                style={{ animationDelay: "2s" }}
              >
                ✨ 10K+ Happy Travelers
              </div>
            </div>
          </section>

          <section className="destinations mb-24 bg-white/90 backdrop-blur-xl py-16 px-10 rounded-3xl shadow-2xl border border-white/30">
            <h2 className="section-title text-4xl font-bold text-gray-900 mb-5 text-center">
              Popular Destinations
            </h2>
            <p className="section-subtitle text-center text-gray-600 text-base mb-12">
              Discover Sri Lanka's most breathtaking locations with our
              expert-curated travel packages
            </p>
            <div className="destinations-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
              {/* Card 1 */}
              <div className="destination-card bg-white/70 hover:bg-white rounded-2xl overflow-hidden shadow-lg transition-all duration-300 ease-in-out cursor-pointer hover:-translate-y-1.5 hover:shadow-xl border border-emerald-100">
                <img
                  src="https://images.unsplash.com/photo-1711797750174-c3750dd9d7c9?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8c2lnaXJpeWF8ZW58MHx8MHx8fDA%3D"
                  alt="Sigiriya Rock"
                  className="w-full h-[180px] object-cover"
                />
                <div className="card-content p-5">
                  <h3 className="text-lg font-bold mb-2.5 text-gray-800">
                    Sigiriya Rock Fortress
                  </h3>
                  <p className="text-gray-600 text-sm leading-snug">
                    Ancient wonder with panoramic views. Climb the legendary
                    Lion Rock and discover 5th-century frescoes.
                  </p>
                </div>
              </div>
              {/* Card 2 */}
              <div className="destination-card bg-white/70 hover:bg-white rounded-2xl overflow-hidden shadow-lg transition-all duration-300 ease-in-out cursor-pointer hover:-translate-y-1.5 hover:shadow-xl border border-emerald-100">
                <img
                  src="https://images.unsplash.com/photo-1642095012223-65ee6d570974?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTh8fHNyaSUyMGxhbmthJTIwdG91cmlzbXxlbnwwfHwwfHx8MA%3D%3D"
                  alt="Temple of Tooth"
                  className="w-full h-[180px] object-cover"
                />
                <div className="card-content p-5">
                  <h3 className="text-lg font-bold mb-2.5 text-gray-800">
                    Temple of the Sacred Tooth
                  </h3>
                  <p className="text-gray-600 text-sm leading-snug">
                    Sacred Buddhist temple in Kandy housing a tooth relic of
                    Buddha. Experience spiritual tranquility.
                  </p>
                </div>
              </div>
              {/* Card 3 */}
              <div className="destination-card bg-white/70 hover:bg-white rounded-2xl overflow-hidden shadow-lg transition-all duration-300 ease-in-out cursor-pointer hover:-translate-y-1.5 hover:shadow-xl border border-emerald-100">
                <img
                  src="https://media.istockphoto.com/id/2164077307/photo/aerial-view-of-tea-plantation-near-the-lake-on-sri-lanka.webp?a=1&b=1&s=612x612&w=0&k=20&c=8rZIaABFAapYfd1Jng5ZipZLB1__DS199LRayqI9SKg="
                  alt="Tea plantations"
                  className="w-full h-[180px] object-cover"
                />
                <div className="card-content p-5">
                  <h3 className="text-lg font-bold mb-2.5 text-gray-800">
                    Nuwara Eliya Tea Country
                  </h3>
                  <p className="text-gray-600 text-sm leading-snug">
                    Rolling green hills and colonial charm. Experience cool
                    climates and scenic train rides.
                  </p>
                </div>
              </div>
              {/* Card 4 */}
              <div className="destination-card bg-white/70 hover:bg-white rounded-2xl overflow-hidden shadow-lg transition-all duration-300 ease-in-out cursor-pointer hover:-translate-y-1.5 hover:shadow-xl border border-emerald-100">
                <img
                  src="https://media.istockphoto.com/id/1254219156/photo/sunrise-over-galle-dutch-fort-lighthouse-surrounded-by-coconut-trees-in-sri-lanka.webp?a=1&b=1&s=612x612&w=0&k=20&c=bYJZasnNl4ixnOecseYOulTJgHvrfyoW6ZhbhGRcfFM="
                  alt="Galle Fort"
                  className="w-full h-[180px] object-cover"
                />
                <div className="card-content p-5">
                  <h3 className="text-lg font-bold mb-2.5 text-gray-800">
                    Galle Dutch Fort
                  </h3>
                  <p className="text-gray-600 text-sm leading-snug">
                    Historic coastal fortress with cobblestone streets. Explore
                    400-year-old ramparts and ocean views.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="why-choose-us flex flex-wrap items-center justify-between py-16 px-5 gap-10">
            <div className="why-image flex-1 basis-[40%] flex justify-center">
              <img
                src="https://media.istockphoto.com/id/2157291795/photo/happy-tourist-couple-taking-selfie-while-exploring-the-city.jpg?s=612x612&w=0&k=20&c=UNZ-TTcpY7ThX8KfCGxrhkc5dxSTVtYm2S8IjpGqXIA="
                alt="Travelers"
                className="max-w-full rounded-3xl shadow-2xl"
              />
            </div>

            <div className="why-content flex-1 basis-[50%]">
              <h2 className="text-3xl font-bold mb-4 text-gray-900">
                Why Choose Us
              </h2>
              <p className="intro text-gray-700 mb-6">
                Enjoy different experiences in every place you visit and
                discover new and affordable adventures of course.
              </p>

              <div className="features flex flex-col gap-4">
                <div className="feature-card flex items-start bg-white/70 hover:bg-white rounded-2xl p-4 shadow-lg transition-shadow duration-300 ease-in-out hover:shadow-xl border border-emerald-100">
                  <div className="icon text-2xl mr-3">🧠</div>
                  <div className="text">
                    <h3 className="m-0 text-base font-semibold text-emerald-700">
                      AI-Powered Personalization
                    </h3>
                    <p className="mt-1 m-0 text-gray-600 text-sm">
                      We use advanced AI to understand your preferences and
                      recommend destinations, activities, and packages.
                    </p>
                  </div>
                </div>

                <div className="feature-card flex items-start bg-white/70 hover:bg-white rounded-2xl p-4 shadow-lg transition-shadow duration-300 ease-in-out hover:shadow-xl border border-emerald-100">
                  <div className="icon text-2xl mr-3">☀️❄️🌧️</div>
                  <div className="text">
                    <h3 className="m-0 text-base font-semibold text-emerald-700">
                      Season-Aware Suggestions
                    </h3>
                    <p className="mt-1 m-0 text-gray-600 text-sm">
                      Get recommendations based on real-time seasonal trends,
                      weather, and local events.
                    </p>
                  </div>
                </div>

                <div className="feature-card flex items-start bg-white/70 hover:bg-white rounded-2xl p-4 shadow-lg transition-shadow duration-300 ease-in-out hover:shadow-xl border border-emerald-100">
                  <div className="icon text-2xl mr-3">🤖</div>
                  <div className="text">
                    <h3 className="m-0 text-base font-semibold text-emerald-700">
                      All-in-One Smart Agents
                    </h3>
                    <p className="mt-1 m-0 text-gray-600 text-sm">
                      Our smart agents work together for a seamless travel
                      planning experience.
                    </p>
                  </div>
                </div>
                {/* ... other feature cards ... */}
              </div>

              <a
                href="#"
                className="more-link inline-flex items-center mt-6 text-emerald-600 no-underline font-medium hover:underline"
              >
                Another Product →
              </a>
            </div>
          </section>
        </div>
      </main>

      {/* Chat Widget */}
      <div className="chat-widget fixed bottom-5 right-5 z-50">
        <button
          className="chat-button w-[60px] h-[60px] bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 border-none rounded-full text-white text-2xl cursor-pointer shadow-lg transition-all duration-300 ease-in-out animate-pulse-subtle hover:scale-110 gradient-shift"
          onClick={toggleChat}
        >
          💬
        </button>
        {isChatOpen && (
          <div className="chat-window absolute bottom-20 right-0 w-[320px] h-[450px] md:w-[350px] md:h-[500px] bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl flex flex-col overflow-hidden border border-white/30 animate-fade-in">
            <div className="chat-header bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 text-white p-5 text-center">
              <h3 className="font-bold text-lg">🤖 Ceylon Travels AI</h3>
              <p className="text-sm opacity-90">
                Hi! I'm here to help plan your adventure!
              </p>
            </div>
            <div className="chat-messages flex-1 p-5 overflow-y-auto bg-gray-50 flex flex-col gap-4">
              {chatMessages.map((message, index) => (
                <div
                  key={index}
                  className={`message py-2.5 px-4 rounded-2xl max-w-[85%] shadow-md animate-fade-in ${
                    message.type === "bot"
                      ? "bg-white text-gray-800 self-start border border-emerald-100"
                      : "bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 text-white self-end ml-auto"
                  }`}
                >
                  {message.content.split("\n").map((line, lineIndex) => (
                    <React.Fragment key={lineIndex}>
                      {line}
                      {lineIndex < message.content.split("\n").length - 1 && (
                        <br />
                      )}
                    </React.Fragment>
                  ))}
                </div>
              ))}
            </div>
            <div className="chat-input flex p-4 bg-white border-t border-emerald-200/50">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={handleChatKeyPress}
                placeholder="Ask me anything..."
                className="flex-1 border border-emerald-300 rounded-full py-2.5 px-4 bg-white outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
              <button
                onClick={sendMessage}
                className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white border-none w-10 h-10 rounded-full ml-2.5 cursor-pointer flex items-center justify-center shadow-md hover:scale-105 transition-transform"
              >
                ➤
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Sign In Modal */}
      {isSignInOpen && (
        <div
          className="modal fixed inset-0 w-full h-full bg-black/60 backdrop-blur-sm z-50 flex justify-center items-center animate-fade-in"
          onClick={() => closeModal("signin")}
        >
          <div
            className="modal-content bg-white rounded-3xl w-[400px] max-w-[90%] text-center relative shadow-2xl overflow-hidden animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="h-2 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500"></div>
            <button
              className="close-modal absolute top-4 right-5 bg-transparent border-none text-2xl cursor-pointer text-gray-400 hover:text-gray-700"
              onClick={() => closeModal("signin")}
            >
              ×
            </button>
            <div className="p-10">
              <h2 className="text-2xl font-bold mb-6 text-gray-900">
                Welcome Back!
              </h2>
              {signInError && (
                <div className="bg-red-100 text-red-600 p-3 rounded-lg mb-5 text-sm border border-red-200">
                  {signInError}
                </div>
              )}
              <form onSubmit={handleSignIn}>
                <div className="form-group mb-5 text-left">
                  <label className="block mb-1 text-gray-600 text-sm font-medium">
                    Email or Username
                  </label>
                  <input
                    type="text"
                    placeholder="Enter your email or username"
                    value={signInData.login}
                    onChange={(e) =>
                      setSignInData({ ...signInData, login: e.target.value })
                    }
                    required
                    disabled={isSignInLoading}
                    className="w-full p-3 border border-emerald-300 rounded-lg outline-none transition-colors duration-300 ease-in-out focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 disabled:bg-gray-100"
                  />
                </div>
                <div className="form-group mb-5 text-left">
                  <label className="block mb-1 text-gray-600 text-sm font-medium">
                    Password
                  </label>
                  <input
                    type="password"
                    placeholder="Enter your password"
                    value={signInData.password}
                    onChange={(e) =>
                      setSignInData({ ...signInData, password: e.target.value })
                    }
                    required
                    disabled={isSignInLoading}
                    className="w-full p-3 border border-emerald-300 rounded-lg outline-none transition-colors duration-300 ease-in-out focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 disabled:bg-gray-100"
                  />
                </div>
                <button
                  type="submit"
                  className={`${btnPrimary} w-full mt-2.5`}
                  disabled={isSignInLoading}
                >
                  {isSignInLoading ? "Signing In..." : "Sign In"}
                </button>
              </form>
              <p className="mt-5 text-gray-600">
                Don't have an account?
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    switchModal("signin", "signup");
                  }}
                  className="text-emerald-700 ml-1 hover:underline font-medium"
                >
                  Sign up here
                </a>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Sign Up Modal */}
      {isSignUpOpen && (
        <div
          className="modal fixed inset-0 w-full h-full bg-black/60 backdrop-blur-sm z-50 flex justify-center items-center animate-fade-in"
          onClick={() => closeModal("signup")}
        >
          <div
            className="modal-content bg-white rounded-3xl w-[400px] max-w-[90%] text-center relative shadow-2xl overflow-hidden animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="h-2 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500"></div>
            <button
              className="close-modal absolute top-4 right-5 bg-transparent border-none text-2xl cursor-pointer text-gray-400 hover:text-gray-700"
              onClick={() => closeModal("signup")}
            >
              ×
            </button>
            <div className="p-10">
              <h2 className="text-2xl font-bold mb-4 text-gray-900">
                Join Ceylon Travels!
              </h2>
              <p className="text-gray-600 mb-5">
                🎁 Get 20% off your first booking!
              </p>
              {signUpError && (
                <div className="bg-red-100 text-red-600 p-3 rounded-lg mb-5 text-sm border border-red-200">
                  {signUpError}
                </div>
              )}
              <form onSubmit={handleSignUp}>
                <div className="form-group mb-5 text-left">
                  <label className="block mb-1 text-gray-600 text-sm font-medium">
                    Username
                  </label>
                  <input
                    type="text"
                    placeholder="Choose a username"
                    value={signUpData.username}
                    onChange={(e) =>
                      setSignUpData({ ...signUpData, username: e.target.value })
                    }
                    required
                    disabled={isSignUpLoading}
                    className="w-full p-3 border border-emerald-300 rounded-lg outline-none transition-colors duration-300 ease-in-out focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 disabled:bg-gray-100"
                  />
                </div>
                <div className="form-group mb-5 text-left">
                  <label className="block mb-1 text-gray-600 text-sm font-medium">
                    Full Name
                  </label>
                  <input
                    type="text"
                    placeholder="Enter your full name"
                    value={signUpData.name}
                    onChange={(e) =>
                      setSignUpData({ ...signUpData, name: e.target.value })
                    }
                    required
                    disabled={isSignUpLoading}
                    className="w-full p-3 border border-emerald-300 rounded-lg outline-none transition-colors duration-300 ease-in-out focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 disabled:bg-gray-100"
                  />
                </div>
                <div className="form-group mb-5 text-left">
                  <label className="block mb-1 text-gray-600 text-sm font-medium">
                    Email
                  </label>
                  <input
                    type="email"
                    placeholder="Enter your email"
                    value={signUpData.email}
                    onChange={(e) =>
                      setSignUpData({ ...signUpData, email: e.target.value })
                    }
                    required
                    disabled={isSignUpLoading}
                    className="w-full p-3 border border-emerald-300 rounded-lg outline-none transition-colors duration-300 ease-in-out focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 disabled:bg-gray-100"
                  />
                </div>
                <div className="form-group mb-5 text-left">
                  <label className="block mb-1 text-gray-600 text-sm font-medium">
                    Password
                  </label>
                  <input
                    type="password"
                    placeholder="Create a password (min 6 chars)"
                    value={signUpData.password}
                    onChange={(e) =>
                      setSignUpData({ ...signUpData, password: e.target.value })
                    }
                    required
                    disabled={isSignUpLoading}
                    minLength={6}
                    className="w-full p-3 border border-emerald-300 rounded-lg outline-none transition-colors duration-300 ease-in-out focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 disabled:bg-gray-100"
                  />
                </div>
                <button
                  type="submit"
                  className={`${btnPrimary} w-full mt-2.5`}
                  disabled={isSignUpLoading}
                >
                  {isSignUpLoading ? "Creating Account..." : "Start Free Trial"}
                </button>
              </form>
              <p className="mt-5 text-gray-600">
                Already have an account?
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    switchModal("signup", "signin");
                  }}
                  className="text-emerald-700 ml-1 hover:underline font-medium"
                >
                  Sign in here
                </a>
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;
