import React from 'react'
import { Link } from 'react-router-dom'

export default function Header(){
  return (
    <header style={{padding:10, borderBottom:'1px solid #ddd'}}>
      <Link to="/">Home</Link> | <Link to="/conversation">Conversation</Link> | <Link to="/summary">Summary</Link>
    </header>
  )
}
