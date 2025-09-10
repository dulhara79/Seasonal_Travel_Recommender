import React from 'react'
import ReactMarkdown from 'react-markdown'

export default function SummaryViewer({ markdown }){
  return (
    <div style={{border:'1px solid #eee', padding:12}}>
      <ReactMarkdown>{markdown || '*No summary available*'}</ReactMarkdown>
    </div>
  )
}
