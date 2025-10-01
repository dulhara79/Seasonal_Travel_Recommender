import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext.jsx"; // FIX: Added .jsx extension
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api";

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

  // Get login function and user state from context
  const { login, user } = useAuth();
  const navigate = useNavigate(); // Initialize navigate hook

  // --- Redirection Effect ---
  // If the user object becomes available (after successful login), navigate to /chat
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
        // Successful login updates 'user' in AuthContext, triggering the useEffect above
        await login(form.username, form.password);
      } else {
        // Register API call
        const res = await axios.post(`${API_BASE_URL}/auth/register`, form);
        setSuccess("Registration successful! Please log in.");
        // Clear sensitive fields after successful registration
        setForm((prev) => ({ ...prev, password: "" }));
        setIsLogin(true); // Switch to login view
      }
    } catch (err) {
      const message =
        err.response?.data?.detail || "An unexpected error occurred.";
      setError(message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-8 space-y-6 bg-white rounded-xl shadow-2xl">
        <h2 className="text-3xl font-extrabold text-center text-gray-900">
          {isLogin ? "Sign in to your account" : "Create a new account"}
        </h2>
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-xl relative text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-xl relative text-sm">
            {success}
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit}>
          {!isLogin && (
            <>
              <input
                type="text"
                name="name"
                placeholder="Full Name"
                required={!isLogin}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              />
              <input
                type="email"
                name="email"
                placeholder="Email Address"
                required={!isLogin}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              />
            </>
          )}
          <input
            type="text"
            name="username"
            placeholder="Username"
            required
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
          />
          <input
            type="password"
            name="password"
            placeholder="Password"
            required
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
          />

          <button
            type="submit"
            className="w-full py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition duration-150"
          >
            {isLogin ? "Sign In" : "Register"}
          </button>
        </form>

        <div className="text-sm text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="font-medium text-blue-600 hover:text-blue-500 focus:outline-none"
          >
            {isLogin
              ? "Don't have an account? Register"
              : "Already have an account? Sign In"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthForm;
