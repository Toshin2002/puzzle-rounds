import { useCountdown } from '../useCountdown'

export default function RoundIntro({ state, clockOffset }) {
  const left = useCountdown(state.deadline, clockOffset)
  const { puzzle } = state

  return (
    <div className="card center intro">
      <p className="eyebrow">Round {state.round} of {state.total_rounds}</p>
      <h1 className="title">{puzzle?.title}</h1>
      <p className="muted">{puzzle?.instructions}</p>
      <div className="intro-count">{Math.ceil(left) || 'Go!'}</div>
      <p className="muted small">{puzzle && `${Math.round(puzzle.time_limit)} seconds · ${puzzle.max_attempts} tries`}</p>
    </div>
  )
}
