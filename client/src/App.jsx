import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Chat from './pages/Chat'
import LandingPage from './components/LandingPage'
import { useAuth } from './contexts/AuthContext'

function Protected({ children }) {
	const { token } = useAuth()
	if (!token) return <Navigate to="/login" replace />
	return children
}

export default function App() {
	return (
		<Routes>
			<Route path="/" element={<LandingPage />} />
			<Route path="/login" element={<Login />} />
			<Route path="/signup" element={<Signup />} />
			<Route
				path="/chat"
				element={
					<Protected>
						<Chat />
					</Protected>
				}
			/>
		</Routes>
	)
}
