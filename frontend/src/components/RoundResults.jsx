import { useCountdown } from '../useCountdown'

export default function RoundResults({ state, clockOffset }) {
  const left = useCountdown(state.deadline, clockOffset)
  const { puzzle, round_results: results } = state
  const isLast = state.round === state.total_rounds

  return (
    <div className="card">
      <p className="eyebrow">Round {state.round} of {state.total_rounds} · results</p>
      <div className="solution">
        <span className="muted small">The answer was</span>
        <strong>{puzzle?.solution?.answer}</strong>
        {puzzle?.solution?.explanation && <span className="muted small">{puzzle.solution.explanation}</span>}
      </div>

      <table className="table">
        <thead>
          <tr><th>Player</th><th></th><th>Time</th><th>Round</th><th>Total</th></tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.player_id} className={r.player_id === state.you.id ? 'me' : ''}>
              <td>{r.name}</td>
              <td>{r.correct ? <span className="ok">✓</span> : <span className="bad">✗</span>}</td>
              <td className="muted">{r.time != null ? `${r.time}s` : '—'}</td>
              <td className="pts">+{r.points}</td>
              <td className="pts strong">{r.total}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="muted center small">
        {isLast ? 'Final leaderboard' : `Round ${state.round + 1}`} in {Math.ceil(left)}…
      </p>
    </div>
  )
}
