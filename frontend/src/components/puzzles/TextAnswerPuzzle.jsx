import { useEffect, useRef, useState } from 'react'

/**
 * Generic puzzle UI: show a prompt, type an answer, submit.
 * Works for any puzzle whose client_view() returns { prompt, input, hint?, placeholder? }.
 */
export default function TextAnswerPuzzle({ view, disabled, onSubmit }) {
  const [value, setValue] = useState('')
  const inputRef = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [view.prompt])

  const submit = (e) => {
    e.preventDefault()
    if (!value.trim() || disabled) return
    onSubmit(value.trim())
    setValue('')
  }

  return (
    <form className="puzzle" onSubmit={submit}>
      <div className="prompt">{view.prompt}</div>
      {view.hint && <p className="muted small center">{view.hint}</p>}
      <div className="answer-row">
        <input
          ref={inputRef}
          type="text"
          inputMode={view.input === 'number' ? 'numeric' : 'text'}
          autoComplete="off"
          value={value}
          disabled={disabled}
          placeholder={view.placeholder || 'Your answer'}
          onChange={(e) => setValue(e.target.value)}
        />
        <button className="btn primary" disabled={disabled || !value.trim()}>Submit</button>
      </div>
    </form>
  )
}
