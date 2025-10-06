import React, { createContext, useState, useContext, useEffect, useRef } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const AuthContext = createContext();

const API_BASE_URL = "https://huggingface.co/spaces/dulharakaushalya/seasonal-travel-recommender-backend";

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Inactivity timeout (ms). Default: 30 minutes. Can be overridden.
  const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes
  const inactivityTimer = useRef(null);

  // --- Authenticated API Instance ---
  const api = axios.create({
    baseURL: API_BASE_URL,
  });

  api.interceptors.request.use((config) => {
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  });
  // Intercept 401 responses and auto-logout
  api.interceptors.response.use(
    (r) => r,
    (error) => {
      if (error?.response?.status === 401) {
        // Token invalid or expired -> force logout
        logout();
        // Redirect to login
        try {
          navigate('/auth');
        } catch (e) {
          /* ignore if navigate not available */
        }
      }
      return Promise.reject(error);
    }
  );
  // ----------------------------------

  // --- Auth Logic ---
  useEffect(() => {
    const loadUser = async () => {
      if (token) {
        try {
          const res = await api.get("/auth/me");
          setUser(res.data);
          localStorage.setItem("token", token);
        } catch (error) {
          console.error("Token expired or invalid", error);
          setToken(null);
          localStorage.removeItem("token");
          setUser(null);
        }
      }
      setIsLoading(false);
    };
    loadUser();
  }, [token]);

  // ---------------------- Inactivity handling ----------------------
  const resetInactivityTimer = () => {
    if (inactivityTimer.current) {
      clearTimeout(inactivityTimer.current);
    }
    if (token) {
      inactivityTimer.current = setTimeout(() => {
        // On timeout, log the user out and navigate to auth
        logout();
        try {
          navigate('/auth');
        } catch (e) {
          /* ignore navigation errors */
        }
      }, INACTIVITY_TIMEOUT);
    }
  };

  useEffect(() => {
    // Activity events that indicate the user is active
    const events = ["click", "mousemove", "keydown", "scroll", "touchstart"];

    const handleActivity = () => resetInactivityTimer();

    events.forEach((ev) => window.addEventListener(ev, handleActivity));

    // Start or clear the timer when token changes
    resetInactivityTimer();

    return () => {
      events.forEach((ev) => window.removeEventListener(ev, handleActivity));
      if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);
  // -----------------------------------------------------------------

  const login = async (username, password) => {
    const params = new URLSearchParams();
    params.append("username", username);
    params.append("password", password);

    const config = {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    };

    const res = await axios.post(`${API_BASE_URL}/auth/token`, params, config);
    setToken(res.data.access_token);
    // User data will be loaded via useEffect
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("token");
    // Clear inactivity timer on logout
    if (inactivityTimer.current) {
      clearTimeout(inactivityTimer.current);
      inactivityTimer.current = null;
    }
    // Navigate to login page
    try {
      navigate('/auth');
    } catch (e) {
      /* ignore navigation errors when used outside router context */
    }
  };

  // --- Conversation Persistence Functions (using the 'api' instance) ---
  const getConversationsList = async () => {
    const res = await api.get("/conversations/list");
    return res.data;
  };

  const fetchConversationById = async (conversationId) => {
    const res = await api.get(`/conversations/${conversationId}`);
    return res.data;
  };

  const startNewConversation = async (
    title = "New Trip",
    sessionId = "default"
  ) => {
    const payload = { title, session_id: sessionId };
    const res = await api.post("/conversations/", payload);
    return res.data;
  };

  const appendChatMessage = async (
    conversationId,
    role,
    text,
    metadata = {}
  ) => {
    // Map common client-side role names to server-expected roles
    const roleMap = {
      assistant: "agent",
      bot: "agent",
      agent: "agent",
      user: "user",
      system: "system",
    };
    const serverRole = roleMap[role] || role;

    // Build message object expected by server schema
    const message = {
      role: serverRole,
      text,
      metadata: metadata || {},
      timestamp: new Date().toISOString(),
    };

    const payload = {
      conversation_id: conversationId,
      message,
    };

    try {
      await api.post("/conversations/append", payload);
    } catch (error) {
      // Surface the error so callers can handle it if needed
      console.error("Failed to append message:", error);
      throw error;
    }
  };

  const deleteConversation = async (convId) => {
    // Assuming 'api' is an Axios/Fetch instance configured with the base URL and auth headers
    const response = await api.delete(`/conversations/${convId}`);
    return response.data; // Expects { "deleted": true, "conversation_id": "..." }
  };

  const deleteAccount = async () => {
    // This endpoint handles the deletion of the user and their data on the server
    const response = await api.delete("/auth/me");
    return response.data; // Expects { "message": "Account successfully deleted..." }
  };

  const updateConversationTitle = async (conversationId, title) => {
    const res = await api.patch(`/conversations/${conversationId}/title`, { title });
    return res.data;
  };

  // -------------------------------------------------------------------

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        login,
        logout,
        isLoading,
        api,
        getConversationsList,
        fetchConversationById,
        startNewConversation,
        appendChatMessage,
  updateConversationTitle,
        deleteConversation,
        deleteAccount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
