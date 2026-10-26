import TextAnswerPuzzle from './TextAnswerPuzzle'

// Maps a puzzle `type` (from the server) to the component that renders it.
// When you add a new puzzle on the backend, register its UI here.
const REGISTRY = {
  quick_maths: TextAnswerPuzzle,
  anagram: TextAnswerPuzzle,
}

export function getPuzzleComponent(type) {
  return REGISTRY[type] || TextAnswerPuzzle
}
