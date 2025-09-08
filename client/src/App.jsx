import { useState } from 'react'
import './App.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Conversation from './pages/Conversation'
import Summary from './pages/Summary'

function App() {
  // conversationMarkdown will hold markdown received from the summary agent
  const [conversationMarkdown, setConversationMarkdown] = useState('# Summary will appear here')

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/conversation" element={<Conversation markdown={conversationMarkdown} onSummary={setConversationMarkdown} />} />
        <Route path="/summary" element={<Summary markdown={conversationMarkdown} />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
