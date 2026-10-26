import { useCallback, useEffect, useRef, useState } from 'react'
import {
  clearToken, getToken, initialSession, saveName, saveToken, setRoomInUrl,
} from './session'

function socketUrl(code) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/ws/${code}`
}

/**
 * Owns the WebSocket connection. Components get the latest server state and a
 * `send` function; they never talk to the socket directly.
 */
export function useGame() {
  const [session, setSession] = useState(initialSession) // { code, name } or null
  const [status, setStatus] = useState('idle')           // idle | connecting | connected | reconnecting
  const [state, setState] = useState(null)               // latest snapshot from the server
  const [feedback, setFeedback] = useState(null)         // result of my last answer
  const [error, setError] = useState(null)
  const [clockOffset, setClockOffset] = useState(0)      // serverTime - localTime, in ms
  const wsRef = useRef(null)
  const roundKeyRef = useRef(null)

  useEffect(() => {
    if (!session) return
    let stopped = false
    let attempt = 0
    let retryTimer = null
    let ws = null

    setState(null)
    setFeedback(null)

    const connect = () => {
      setStatus(attempt === 0 ? 'connecting' : 'reconnecting')
      ws = new WebSocket(socketUrl(session.code))
      wsRef.current = ws

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'join', name: session.name, token: getToken(session.code) }))
      }

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'joined') {
          attempt = 0
          saveToken(session.code, msg.token)
          setStatus('connected')
          setError(null)
        } else if (msg.type === 'state') {
          setClockOffset(msg.server_now - Date.now())
          const key = `${msg.phase}:${msg.round}`
          if (roundKeyRef.current !== key) {
            roundKeyRef.current = key
            setFeedback(null) // new phase or round: clear "wrong answer" messages
          }
          setState(msg)
        } else if (msg.type === 'feedback') {
          setFeedback(msg)
        } else if (msg.type === 'error') {
          setError(msg.message)
          if (msg.fatal) {
            stopped = true
            // "replaced" means another tab took over this seat: keep the token for that tab.
            if (msg.reason !== 'replaced') clearToken(session.code)
            setRoomInUrl(null)
            setSession(null)
          }
        }
      }

      ws.onclose = () => {
        if (stopped) return
        attempt += 1
        setStatus('reconnecting')
        retryTimer = setTimeout(connect, Math.min(1000 * 2 ** (attempt - 1), 8000))
      }
    }

    connect()

    return () => {
      stopped = true
      clearTimeout(retryTimer)
      if (ws) {
        ws.onclose = null
        ws.onmessage = null
        ws.close()
      }
      wsRef.current = null
      setStatus('idle')
    }
  }, [session])

  const send = useCallback((type, data = {}) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type, ...data }))
  }, [])

  const joinRoom = useCallback((code, name) => {
    const clean = code.trim().toUpperCase()
    saveName(name.trim())
    setRoomInUrl(clean)
    setError(null)
    setSession({ code: clean, name: name.trim() })
  }, [])

  const createRoom = useCallback(async (name) => {
    setError(null)
    try {
      const res = await fetch('/api/rooms', { method: 'POST' })
      if (!res.ok) throw new Error()
      const { code } = await res.json()
      joinRoom(code, name)
    } catch {
      setError("Couldn't create a room. Is the server running?")
    }
  }, [joinRoom])

  const leave = useCallback(() => {
    if (session) clearToken(session.code)
    setRoomInUrl(null)
    setSession(null)
    setState(null)
  }, [session])

  return { session, status, state, feedback, error, clockOffset, send, joinRoom, createRoom, leave, setError }
}
