import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import { useNavigate } from "react-router-dom";
import axios from "axios";

// Prefer Vite env var so the frontend can target different backends in prod/dev
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const AuthForm = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [form, setForm] = useState({
    name: "",
    email: "",
    username: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [mounted, setMounted] = useState(false);

  const { login, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (user) {
      navigate("/chat");
    }
  }, [user, navigate]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      if (isLogin) {
        await login(form.username, form.password);
      } else {
  const registerUrl = `${API_BASE_URL.replace(/\/$/, '')}/api/auth/register`;
  const res = await axios.post(registerUrl, form);
        setSuccess("Registration successful! Please log in.");
        setForm((prev) => ({ ...prev, password: "" }));
        setIsLogin(true);
      }
    } catch (err) {
      const message =
        err.response?.data?.detail || "An unexpected error occurred.";
      setError(message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div
          className={`absolute top-20 left-10 w-72 h-72 bg-gradient-to-br from-emerald-300/30 to-teal-300/30 rounded-full blur-3xl transition-all duration-1000 ${
            mounted ? "opacity-100 scale-100" : "opacity-0 scale-75"
          }`}
          style={{ animation: "float 8s ease-in-out infinite" }}
        ></div>
        <div
          className={`absolute bottom-20 right-10 w-96 h-96 bg-gradient-to-br from-cyan-300/30 to-blue-300/30 rounded-full blur-3xl transition-all duration-1000 delay-300 ${
            mounted ? "opacity-100 scale-100" : "opacity-0 scale-75"
          }`}
          style={{ animation: "float 10s ease-in-out infinite 2s" }}
        ></div>
        <div
          className={`absolute top-1/2 left-1/2 w-80 h-80 bg-gradient-to-br from-teal-300/20 to-emerald-300/20 rounded-full blur-3xl transition-all duration-1000 delay-500 ${
            mounted ? "opacity-100 scale-100" : "opacity-0 scale-75"
          }`}
          style={{ animation: "float 12s ease-in-out infinite 4s" }}
        ></div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) translateX(0px) rotate(0deg); }
          33% { transform: translateY(-20px) translateX(10px) rotate(3deg); }
          66% { transform: translateY(10px) translateX(-10px) rotate(-3deg); }
        }
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes slideIn {
          from { transform: translateY(30px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        @keyframes pulse-glow {
          0%, 100% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.3); }
          50% { box-shadow: 0 0 40px rgba(16, 185, 129, 0.5); }
        }
        .animate-slide-in {
          animation: slideIn 0.6s ease-out forwards;
        }
        .gradient-shift {
          background-size: 200% 200%;
          animation: shimmer 3s ease infinite;
        }
        .pulse-glow {
          animation: pulse-glow 3s ease-in-out infinite;
        }
      `}</style>

      <div
        className={`max-w-md w-full mx-4 transition-all duration-700 ${
          mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
        }`}
      >
        <div className="bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/30 overflow-hidden pulse-glow">
          {/* Header with gradient */}
          <div className="relative px-8 pt-8 pb-6 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 text-white overflow-hidden">
            <div
              className="absolute inset-0 opacity-10"
              style={{
                backgroundImage:
                  "radial-gradient(circle at 2px 2px, white 1px, transparent 0)",
                backgroundSize: "32px 32px",
              }}
            ></div>
            <div className="relative">
              <div className="flex items-center justify-center mb-4">
                <div className="w-20 h-20 bg-white/20 backdrop-blur rounded-3xl flex items-center justify-center transform transition-transform duration-500 hover:scale-110 hover:rotate-6 shadow-lg">
                  <svg
                    className="w-12 h-12"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
                  </svg>
                </div>
              </div>
              <h2 className="text-3xl font-bold text-center mb-2 tracking-tight">
                Ceylon Travels
              </h2>
              <p className="text-center text-white/90 text-sm font-medium">
                {isLogin
                  ? "Welcome back, explorer!"
                  : "Begin your Sri Lankan adventure"}
              </p>
            </div>
          </div>

          <div className="p-8 space-y-6">
            {/* Error & Success Messages */}
            {error && (
              <div className="bg-gradient-to-r from-red-50 to-rose-50 border-l-4 border-red-500 text-red-700 px-4 py-3 rounded-xl relative animate-slide-in shadow-md">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg
                      className="w-5 h-5 mr-2"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <span className="text-sm font-medium">{error}</span>
                </div>
              </div>
            )}
            {success && (
              <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border-l-4 border-emerald-500 text-emerald-700 px-4 py-3 rounded-xl relative animate-slide-in shadow-md">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg
                      className="w-5 h-5 mr-2"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <span className="text-sm font-medium">{success}</span>
                </div>
              </div>
            )}

            {/* Form */}
            <form className="space-y-5" onSubmit={handleSubmit}>
              {!isLogin && (
                <>
                  <div className="group">
                    <label className="block text-sm font-semibold text-gray-700 mb-2 transition-colors group-focus-within:text-emerald-600">
                      Full Name
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        name="name"
                        value={form.name}
                        placeholder="Enter your full name"
                        required={!isLogin}
                        onChange={handleChange}
                        className="w-full px-4 py-3 pl-11 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all duration-300 outline-none bg-white/70 backdrop-blur hover:border-gray-300"
                      />
                      <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
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
                            d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                          />
                        </svg>
                      </div>
                    </div>
                  </div>
                  <div className="group">
                    <label className="block text-sm font-semibold text-gray-700 mb-2 transition-colors group-focus-within:text-emerald-600">
                      Email Address
                    </label>
                    <div className="relative">
                      <input
                        type="email"
                        name="email"
                        value={form.email}
                        placeholder="Enter your email"
                        required={!isLogin}
                        onChange={handleChange}
                        className="w-full px-4 py-3 pl-11 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all duration-300 outline-none bg-white/70 backdrop-blur hover:border-gray-300"
                      />
                      <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
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
                            d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                          />
                        </svg>
                      </div>
                    </div>
                  </div>
                </>
              )}
              <div className="group">
                <label className="block text-sm font-semibold text-gray-700 mb-2 transition-colors group-focus-within:text-emerald-600">
                  Username
                </label>
                <div className="relative">
                  <input
                    type="text"
                    name="username"
                    value={form.username}
                    placeholder="Choose a username"
                    required
                    onChange={handleChange}
                    className="w-full px-4 py-3 pl-11 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all duration-300 outline-none bg-white/70 backdrop-blur hover:border-gray-300"
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
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
                        d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                </div>
              </div>
              <div className="group">
                <label className="block text-sm font-semibold text-gray-700 mb-2 transition-colors group-focus-within:text-emerald-600">
                  Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    name="password"
                    value={form.password}
                    placeholder="Enter your password"
                    required
                    onChange={handleChange}
                    className="w-full px-4 py-3 pl-11 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all duration-300 outline-none bg-white/70 backdrop-blur hover:border-gray-300"
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
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
                        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                      />
                    </svg>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-3.5 px-4 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-300 mt-6 relative overflow-hidden group gradient-shift"
              >
                <span className="relative z-10 flex items-center justify-center">
                  {isLogin ? "Sign In" : "Create Account"}
                  <svg
                    className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7l5 5m0 0l-5 5m5-5H6"
                    />
                  </svg>
                </span>
              </button>
            </form>

            {/* Toggle Login/Register */}
            <div className="text-center pt-4 border-t border-gray-200">
              <button
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError("");
                  setSuccess("");
                }}
                className="text-sm font-medium text-gray-600 hover:text-emerald-600 transition-colors duration-300"
              >
                {isLogin
                  ? "Don't have an account? "
                  : "Already have an account? "}
                <span className="text-emerald-600 hover:text-emerald-700 font-semibold">
                  {isLogin ? "Sign Up" : "Sign In"}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Footer tagline */}
        <p className="text-center mt-6 text-gray-600 text-sm font-medium flex items-center justify-center space-x-2">
          <svg
            className="w-5 h-5 text-emerald-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          <span>Discover the pearl of the Indian Ocean</span>
        </p>
      </div>
    </div>
  );
};

export default AuthForm;
