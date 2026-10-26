import Timer from './Timer'
import { getPuzzleComponent } from './puzzles'

const STATUS_LABEL = { solving: 'Solving…', solved: 'Solved', out: 'Out of tries' }

export default function Playing({ state, send, clockOffset, feedback }) {
  const { puzzle, my_submission: mine } = state
  const PuzzleView = getPuzzleComponent(puzzle.type)
  const solved = state.players.filter((p) => p.status === 'solved').length

  return (
    <div className="playing">
      <section className="card">
        <div className="round-head">
          <span className="eyebrow">Round {state.round} of {state.total_rounds} · {puzzle.title}</span>
          <Timer deadline={state.deadline} total={puzzle.time_limit} clockOffset={clockOffset} />
        </div>

        <p className="muted">{puzzle.instructions}</p>

        <PuzzleView
          view={puzzle.view}
          disabled={mine?.finished}
          onSubmit={(answer) => send('submit', { answer })}
        />

        <div className="feedback-area">
          {mine?.correct && <p className="ok">Correct! +{mine.points} points. Waiting for the others…</p>}
          {mine?.finished && !mine.correct && <p className="bad">Out of tries for this round.</p>}
          {!mine?.finished && feedback && !feedback.correct && (
            <p className="bad">Not quite. {feedback.attempts_left} {feedback.attempts_left === 1 ? 'try' : 'tries'} left.</p>
          )}
        </div>
      </section>

      <aside className="card side">
        <h2 className="section-title">{solved}/{state.players.length} solved</h2>
        <ul className="player-list compact">
          {state.players.map((p) => (
            <li key={p.id} className={p.connected ? '' : 'offline'}>
              <span className="pname">{p.name}</span>
              <span className={`status ${p.status}`}>{p.connected ? STATUS_LABEL[p.status] : 'Offline'}</span>
              <span className="pts">{p.score}</span>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
