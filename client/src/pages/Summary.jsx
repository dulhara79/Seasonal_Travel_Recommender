import React from 'react'
import SummaryViewer from '../components/SummaryViewer'

export default function Summary({ markdown }) {
  return (
    <div style={{padding:20}}>
      <h2>Summary</h2>
      <SummaryViewer markdown={markdown} />
    </div>
  )
}
