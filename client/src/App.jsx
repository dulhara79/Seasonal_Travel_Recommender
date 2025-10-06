import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext.jsx'; // FIX: Added .jsx extension
import AuthForm from './components/AuthForm.jsx'; // FIX: Added .jsx extension
import ChatInterface from './components/ChatInterface.jsx'; // FIX: Added .jsx extension

// A simple protected route wrapper
const ProtectedRoute = ({ element: Element }) => {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <h1 className="text-xl font-semibold">Loading...</h1>
        </div>
    );
  }

  return user ? <Element /> : <Navigate to="/auth" />;
};

const AppRoutes = () => {
    const { user } = useAuth(); 

    return (
        <Routes>
            <Route path="/auth" element={<AuthForm />} />
            <Route path="/chat" element={<ProtectedRoute element={ChatInterface} />} />
            <Route path="/" element={<Navigate to={user ? "/chat" : "/auth"} />} />
        </Routes>
    )
}


const App = () => {
  return (
    // FIX: Added future flags to BrowserRouter to silence v7 deprecation warnings
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
