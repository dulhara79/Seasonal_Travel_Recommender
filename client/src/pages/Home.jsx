import React from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div style={{padding:20}}>
      <h1>Seasonal Travel Recommender</h1>
      <p>Welcome — use the Conversation page to interact with agents.</p>
      <nav>
        <Link to="/conversation">Conversation</Link> | <Link to="/summary">Summary</Link>
      </nav>
    </div>
  )
}
