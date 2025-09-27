import React from 'react'

export default function ChatMessage({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2`}> 
      <div className={`max-w-[70%] p-3 rounded ${isUser ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
        <div className="whitespace-pre-wrap">{msg.text}</div>
        <div className="text-xs text-gray-500 mt-1">{new Date(msg.timestamp).toLocaleString()}</div>
      </div>
    </div>
  )
}
