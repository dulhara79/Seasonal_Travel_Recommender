import React from 'react'

export default function ConversationBody({ markdownPlaceholder }){
  return (
    <div style={{marginTop:10}}>
      <h3>Conversation Body</h3>
      <div style={{minHeight:120, border:'1px solid #eee', padding:10}}>
        <small>{markdownPlaceholder}</small>
      </div>
    </div>
  )
}
