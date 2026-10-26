import { useRef, useState } from 'react'
import { getRoomFromUrl, getSavedName } from '../session'

export default function Home({ onCreate, onJoin, error }) {
  const [name, setName] = useState(getSavedName)
  const [code, setCode] = useState(() => getRoomFromUrl() || '')
  const [busy, setBusy] = useState(false)
  const [nameHint, setNameHint] = useState(false)
  const nameRef = useRef(null)
  const hasName = name.trim().length > 0

  const create = async () => {
    setBusy(true)
    await onCreate(name)
    setBusy(false)
  }

  const join = (e) => {
    e.preventDefault()
    if (code.trim().length !== 4) return
    if (!hasName) {
      setNameHint(true)
      nameRef.current?.focus()
      return
    }
    onJoin(code, name)
  }

  return (
    <div className="card home">
      <h1 className="title">Five rounds.<br />One leaderboard.</h1>
      <p className="muted">Solve each puzzle faster than your friends.</p>

      <label className="field">
        <span>Your name</span>
        <input
          ref={nameRef}
          value={name}
          maxLength={20}
          placeholder="e.g. Priya"
          onChange={(e) => { setName(e.target.value); setNameHint(false) }}
          autoFocus
        />
      </label>
      {nameHint && !hasName && <p className="error">Enter your name to join the room.</p>}

      <button className="btn primary wide" disabled={!hasName || busy} onClick={create}>
        {busy ? 'Creating…' : 'Create a room'}
      </button>

      <div className="divider"><span>or join one</span></div>

      <form className="join-row" onSubmit={join}>
        <input
          className="code-input"
          value={code}
          maxLength={4}
          placeholder="CODE"
          onChange={(e) => setCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ''))}
        />
        <button className="btn" disabled={code.length !== 4}>Join</button>
      </form>

      {error && <p className="error">{error}</p>}
    </div>
  )
}
