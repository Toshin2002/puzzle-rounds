export default function FinalLeaderboard({ state, send, leave }) {
  const board = state.leaderboard
  const podium = board.slice(0, 3)
  const rounds = Array.from({ length: state.total_rounds }, (_, i) => i + 1)
  // Order the podium 2nd, 1st, 3rd so the winner stands in the middle.
  const podiumOrder = [podium[1], podium[0], podium[2]].filter(Boolean)
  const winners = board.filter((p) => p.rank === 1)
  const headline =
    !board.length || board[0].score === 0 ? 'Nobody scored this time'
    : winners.length > 1 ? `It's a tie: ${winners.map((w) => w.name).join(' & ')}!`
    : `${winners[0].name} wins!`

  return (
    <div className="card">
      <p className="eyebrow center">Final leaderboard</p>
      <h1 className="title center">{headline}</h1>

      <div className="podium">
        {podiumOrder.map((p) => (
          <div key={p.id} className={`step rank-${p.rank}`}>
            <span className="pname">{p.name}</span>
            <span className="pts">{p.score}</span>
            <div className="block">{p.rank}</div>
          </div>
        ))}
      </div>

      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th>#</th><th>Player</th>
              {rounds.map((r) => <th key={r} className="num">R{r}</th>)}
              <th className="num">Total</th>
            </tr>
          </thead>
          <tbody>
            {board.map((p) => (
              <tr key={p.id} className={p.id === state.you.id ? 'me' : ''}>
                <td>{p.rank}</td>
                <td>{p.name}</td>
                {rounds.map((r) => <td key={r} className="num muted">{p.round_points[r - 1] ?? 0}</td>)}
                <td className="num strong">{p.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="actions">
        {state.you.is_host
          ? <button className="btn primary wide" onClick={() => send('back_to_lobby')}>Play again</button>
          : <p className="muted center">The host can start another game.</p>}
        <button className="btn ghost" onClick={leave}>Leave</button>
      </div>
    </div>
  )
}
