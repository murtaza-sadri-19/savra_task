/**
 * Client-side mirror of backend/router.py
 * Used to show live routing preview before the user submits.
 * Must stay in sync with the backend logic.
 */

const HARD_SUBJECTS = new Set([
  'Physics', 'Chemistry', 'Mathematics',
  'Biology', 'Computer Science', 'Economics', 'Accountancy',
])

const COMPLEX_KEYWORDS = [
  'quantum', 'calculus', 'organic', 'thermodynam', 'genetic',
  'algorithm', 'integration', 'differentiat', 'electrochemist',
  'nuclear', 'relativity', 'trigonometry', 'probability',
]

export const MODEL_FAST  = 'llama-3.1-8b-instant'
export const MODEL_SMART = 'llama-3.3-70b-versatile'

const COST_PER_M = { [MODEL_FAST]: 0.05, [MODEL_SMART]: 0.59 }
const AVG_TOKENS = 5000
const INR_PER_USD = 83.5
const CURRENT_COST_INR = 15

export function computeRouting(topic, grade, slides, subject) {
  let score = 0
  const reasons = []

  if (slides > 15)      { score += 3; reasons.push(`${slides} slides — high volume`) }
  else if (slides > 10) { score += 2; reasons.push(`${slides} slides — moderate volume`) }

  if (grade >= 11)      { score += 3; reasons.push(`Grade ${grade} — board-level`) }
  else if (grade >= 9)  { score += 2; reasons.push(`Grade ${grade} — secondary level`) }
  else if (grade >= 7)  { score += 1 }

  if (HARD_SUBJECTS.has(subject)) {
    score += 1
    reasons.push(`${subject} — technical subject`)
  }

  const tl = (topic ?? '').toLowerCase()
  const hit = COMPLEX_KEYWORDS.find(k => tl.includes(k))
  if (hit) { score += 2; reasons.push(`Complex term: "${hit}"`) }

  const model = score >= 4 ? MODEL_SMART : MODEL_FAST
  const costUSD = (AVG_TOKENS / 1_000_000) * COST_PER_M[model]
  const costINR = costUSD * INR_PER_USD
  const savedINR = CURRENT_COST_INR - costINR
  const savingsPct = ((savedINR / CURRENT_COST_INR) * 100).toFixed(1)

  return {
    model,
    score,
    reasons: reasons.length ? reasons : ['Standard request — fast model sufficient'],
    costINR: +costINR.toFixed(4),
    savedINR: +savedINR.toFixed(2),
    savingsPct,
    isSmart: score >= 4,
  }
}
