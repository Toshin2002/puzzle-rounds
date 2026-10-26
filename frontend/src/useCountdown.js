import { useEffect, useState } from 'react'

/** Seconds left until `deadline` (server epoch ms), corrected for clock difference. */
export function useCountdown(deadline, clockOffset) {
  const calc = () => (deadline ? Math.max(0, (deadline - (Date.now() + clockOffset)) / 1000) : 0)
  const [left, setLeft] = useState(calc)

  useEffect(() => {
    setLeft(calc())
    if (!deadline) return
    const id = setInterval(() => setLeft(calc()), 100)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deadline, clockOffset])

  return left
}
