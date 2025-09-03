import React, { useState } from 'react'
import axios from 'axios'
import ConversationBody from '../components/ConversationBody'
import SummaryViewer from '../components/SummaryViewer'
import { Link } from 'react-router-dom'

export default function Conversation({ onSummary }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  // Try to fetch from summary agent via gateway; fallback to pasted markdown
  async function requestSummary() {
    setLoading(true)
    try {
      // Gateway mounts agents under /agents/summary_agent if available
      const resp = await axios.post('/agents/summary_agent/summarize', { text: input })
      // Expect response.markdown or response.summary
      const md = resp.data.markdown || resp.data.summary || JSON.stringify(resp.data)
      onSummary(md)
    } catch (e) {
      // If network fails, assume input is markdown and pass it through
      onSummary(input || 'No summary available')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{padding:20}}>
      <h2>Conversation</h2>
      <p>Paste markdown from the summary agent or type text to request a summary.</p>
      <textarea value={input} onChange={e=>setInput(e.target.value)} rows={8} style={{width:'100%'}} />
      <div style={{marginTop:10}}>
        <button onClick={requestSummary} disabled={loading}>{loading ? 'Requesting...' : 'Request Summary'}</button>
      </div>
      <hr />
  <ConversationBody markdownPlaceholder="Summary will appear on the Summary page" />
  <h3>Immediate Summary Preview</h3>
  <SummaryViewer markdown={input} />
  <p>Or view the polished summary on the <Link to="/summary">Summary page</Link>.</p>
    </div>
  )
}
