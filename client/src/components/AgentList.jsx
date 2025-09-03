import React from 'react'

export default function AgentList({ agents }){
  return (
    <aside style={{padding:10}}>
      <h4>Agents</h4>
      <ul>
        {(agents || []).map(a=> <li key={a}>{a}</li>)}
      </ul>
    </aside>
  )
}
