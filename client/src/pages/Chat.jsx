import React, { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import ChatMessage from '../components/ChatMessage'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export default function Chat() {
  const { token, logout, user } = useAuth()
  const [conversations, setConversations] = useState([])
  const [activeConv, setActiveConv] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!token) return
    fetchConversations()
  }, [token])

  const fetchConversations = async () => {
    setLoading(true)
    const res = await fetch(`${API_BASE}/api/conversations/`, { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) {
      setLoading(false)
      return
    }
    const data = await res.json()
    setConversations(data)
    if (data.length > 0) setActiveConv(data[0])
    setLoading(false)
  }

  const createConversation = async () => {
    const res = await fetch(`${API_BASE}/api/conversations/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Chat' }),
    })
    if (!res.ok) return
    const conv = await res.json()
    setConversations((c) => [conv, ...c])
    setActiveConv(conv)
  }

  const sendMessage = async () => {
    if (!input.trim() || !activeConv) return
    const payload = {
      conversation_id: activeConv.id,
      message: { role: 'user', text: input.trim(), metadata: {} },
    }
    const res = await fetch(`${API_BASE}/api/conversations/append`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (res.ok) {
      // locally append for instant UI
      const msg = { ...payload.message, timestamp: new Date().toISOString() }
      setActiveConv((c) => ({ ...c, messages: [...(c.messages || []), msg] }))
      setConversations((list) => list.map((c) => (c.id === activeConv.id ? { ...c, messages: [...(c.messages || []), msg] } : c)))
      setInput('')
    }
  }

  const selectConv = async (conv) => {
    // fetch latest
    const res = await fetch(`${API_BASE}/api/conversations/${conv.id}`, { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) return
    const c = await res.json()
    setActiveConv(c)
  }

  return (
    <div className="min-h-screen flex bg-gray-50">
      <aside className="w-80 p-4 border-r bg-white">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="font-semibold">{user?.name || user?.username}</div>
            <div className="text-xs text-gray-500">{user?.email}</div>
          </div>
          <button onClick={logout} className="text-sm text-red-600">Logout</button>
        </div>
        <div className="mb-3">
          <button onClick={createConversation} className="w-full bg-blue-600 text-white p-2 rounded">New Chat</button>
        </div>
        <div>
          {loading && <div className="text-sm text-gray-500">Loading...</div>}
          {!loading && conversations.length === 0 && <div className="text-sm text-gray-500">No conversations</div>}
          <ul className="space-y-2">
            {conversations.map((c) => (
              <li key={c.id}>
                <button onClick={() => selectConv(c)} className={`w-full text-left p-2 rounded ${activeConv?.id === c.id ? 'bg-gray-100' : ''}`}>
                  <div className="font-medium">{c.title || 'Untitled'}</div>
                  <div className="text-xs text-gray-500">{new Date(c.updated_at).toLocaleString()}</div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </aside>
      <main className="flex-1 p-6 flex flex-col">
        <div className="flex-1 overflow-auto mb-4">
          {!activeConv && <div className="text-gray-500">Select or create a conversation</div>}
          {activeConv && (
            <div>
              <h3 className="text-xl font-semibold mb-2">{activeConv.title || 'Chat'}</h3>
              <div className="space-y-2">
                {(activeConv.messages || []).map((m, idx) => (
                  <ChatMessage key={idx} msg={m} />
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="pt-3 border-t">
          <div className="flex gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your message" className="flex-1 p-2 border rounded" />
            <button onClick={sendMessage} className="bg-blue-600 text-white p-2 rounded">Send</button>
          </div>
        </div>
      </main>
    </div>
  )
}
