import { useEffect } from 'react'
import { useGame } from './useGame'
import Home from './components/Home'
import Lobby from './components/Lobby'
import RoundIntro from './components/RoundIntro'
import Playing from './components/Playing'
import RoundResults from './components/RoundResults'
import FinalLeaderboard from './components/FinalLeaderboard'

export default function App() {
  const game = useGame()
  const { session, state, status, error, setError } = game

  // In-game errors (e.g. "Time's up!") show as a toast that fades after a few seconds.
  useEffect(() => {
    if (!session || !error) return
    const id = setTimeout(() => setError(null), 3500)
    return () => clearTimeout(id)
  }, [session, error, setError])

  if (!session) {
    return (
      <Shell>
        <Home onCreate={game.createRoom} onJoin={game.joinRoom} error={error} />
      </Shell>
    )
  }

  if (!state) {
    return (
      <Shell>
        <div className="card center">
          <p className="muted">{status === 'reconnecting' ? 'Trying to reach the server…' : 'Connecting…'}</p>
          <button className="btn ghost" onClick={game.leave}>Cancel</button>
        </div>
      </Shell>
    )
  }

  const props = { state, send: game.send, clockOffset: game.clockOffset, feedback: game.feedback, leave: game.leave }
  const screens = {
    lobby: <Lobby {...props} />,
    round_intro: <RoundIntro {...props} />,
    playing: <Playing {...props} />,
    round_results: <RoundResults {...props} />,
    final: <FinalLeaderboard {...props} />,
  }

  return (
    <Shell code={state.code}>
      {status === 'reconnecting' && <div className="banner">Connection lost — reconnecting…</div>}
      {error && (
        <div className="toast" onClick={() => game.setError(null)}>{error}</div>
      )}
      {screens[state.phase]}
    </Shell>
  )
}

function Shell({ code, children }) {
  return (
    <div className="shell">
      <header className="topbar">
        <span className="logo">Puzzle<span>Rounds</span></span>
        {code && <span className="room-chip">Room {code}</span>}
      </header>
      <main>{children}</main>
    </div>
  )
}
