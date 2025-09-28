import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Signup() {
  const [username, setUsername] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const { signup } = useAuth()
  const navigate = useNavigate()

  const onSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await signup({ username, name, email, password })
      navigate('/chat')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded shadow">
        <h2 className="text-2xl font-semibold mb-4">Create an account</h2>
        {error && <div className="text-sm text-red-600 mb-2">{error}</div>}
        <form onSubmit={onSubmit} className="space-y-3">
          <input className="w-full p-2 border rounded" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <input className="w-full p-2 border rounded" placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} required />
          <input className="w-full p-2 border rounded" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input className="w-full p-2 border rounded" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button className="w-full bg-green-600 text-white p-2 rounded" type="submit">Sign up</button>
        </form>
        <p className="mt-3 text-sm">Already have an account? <Link to="/login" className="text-blue-600">Sign in</Link></p>
      </div>
    </div>
  )
}
