// Small helpers for what the browser remembers between refreshes.
// The room code lives in the URL (?room=ABCD) so it can be shared as a link.

const NAME_KEY = 'pr:name'
const tokenKey = (code) => `pr:token:${code}`

function read(key) {
  try { return localStorage.getItem(key) } catch { return null }
}
function write(key, value) {
  try { value == null ? localStorage.removeItem(key) : localStorage.setItem(key, value) } catch { /* private mode */ }
}

export const getSavedName = () => read(NAME_KEY) || ''
export const saveName = (name) => write(NAME_KEY, name)
export const getToken = (code) => read(tokenKey(code))
export const saveToken = (code, token) => write(tokenKey(code), token)
export const clearToken = (code) => write(tokenKey(code), null)

export function getRoomFromUrl() {
  const code = new URLSearchParams(window.location.search).get('room')
  return code ? code.toUpperCase() : null
}

export function setRoomInUrl(code) {
  const url = new URL(window.location.href)
  if (code) url.searchParams.set('room', code)
  else url.searchParams.delete('room')
  window.history.replaceState(null, '', url)
}

export function shareLink(code) {
  return `${window.location.origin}${window.location.pathname}?room=${code}`
}

// On page load: if the URL has a room and we know our name, rejoin automatically.
export function initialSession() {
  const code = getRoomFromUrl()
  const name = getSavedName()
  return code && name && getToken(code) ? { code, name } : null
}
