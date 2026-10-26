import { useState } from 'react'
import { shareLink } from '../session'

export default function Lobby({ state, send, leave }) {
  const [copied, setCopied] = useState(false)
  const isHost = state.you.is_host
  const online = state.players.filter((p) => p.connected).length

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareLink(state.code))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch { /* clipboard blocked */ }
  }

  return (
    <div className="card">
      <p className="eyebrow">Room code</p>
      <div className="big-code">{state.code}</div>
      <button className="btn ghost small" onClick={copy}>{copied ? 'Link copied' : 'Copy invite link'}</button>

      <h2 className="section-title">Players <span className="muted">({online})</span></h2>
      <ul className="player-list">
        {state.players.map((p) => (
          <li key={p.id} className={p.connected ? '' : 'offline'}>
            <span className="avatar">{p.name[0]?.toUpperCase()}</span>
            <span className="pname">{p.name}{p.id === state.you.id && <em> (you)</em>}</span>
            {p.is_host && <span className="tag">Host</span>}
            {!p.connected && <span className="tag dim">Offline</span>}
          </li>
        ))}
      </ul>

      <div className="actions">
        {isHost ? (
          <button className="btn primary wide" onClick={() => send('start')}>
            Start game · {state.total_rounds} rounds
          </button>
        ) : (
          <p className="muted center">Waiting for the host to start…</p>
        )}
        <button className="btn ghost" onClick={leave}>Leave</button>
      </div>
    </div>
  )
}
