import { useCountdown } from '../useCountdown'

/** A countdown bar that turns urgent in the last few seconds. */
export default function Timer({ deadline, total, clockOffset }) {
  const left = useCountdown(deadline, clockOffset)
  const pct = total ? Math.max(0, Math.min(100, (left / total) * 100)) : 0
  const urgent = left <= 5

  return (
    <div className={`timer ${urgent ? 'urgent' : ''}`}>
      <div className="timer-bar"><div style={{ width: `${pct}%` }} /></div>
      <span className="timer-num">{Math.ceil(left)}s</span>
    </div>
  )
}
