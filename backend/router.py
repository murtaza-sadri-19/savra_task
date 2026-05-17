"""
Smart Model Router
------------------
Routes each PPT request to the cheapest model that can handle it well.
This is the primary cost-reduction lever.

Cost comparison (Groq pricing, May 2026):
  llama-3.1-8b-instant  → $0.05 / 1M tokens  (~₹0.02 per PPT)
  llama-3.3-70b-versatile → $0.59 / 1M tokens (~₹0.25 per PPT)
  Gemini 3.1 Pro (current) → ~₹15 per PPT

Target: 80% of requests routed to 8b, 20% to 70b
Blended cost target: ~₹0.07/PPT vs ₹15 current = 99.5% reduction
"""

import os
from dataclasses import dataclass

# Groq model identifiers (from environment)
MODEL_FAST = os.environ.get("FAST_MODEL", "llama-3.1-8b-instant")
MODEL_SMART = os.environ.get("SMART_MODEL", "llama-3.3-70b-versatile")

# Approximate tokens per PPT request (input prompt + output)
AVG_TOKENS = int(os.environ.get("AVG_TOKENS", "5000"))

# Pricing configuration (USD per 1M tokens)
COST_PER_M = {
    MODEL_FAST:  float(os.environ.get("FAST_MODEL_COST_USD", "0.05")),
    MODEL_SMART: float(os.environ.get("SMART_MODEL_COST_USD", "0.59")),
}

INR_PER_USD = float(os.environ.get("INR_PER_USD", "83.5"))


@dataclass
class RoutingDecision:
    model: str
    score: int
    reasons: list[str]
    estimated_cost_inr: float


def compute_complexity_score(topic: str, grade: int, slides: int, subject: str) -> tuple[int, list[str]]:
    """
    Score 0-10. Higher = more complex = use the bigger model.
    Threshold: score >= 4 → 70b model
    """
    score = 0
    reasons = []

    # Slide volume
    if slides > 15:
        score += 3
        reasons.append(f"{slides} slides — high volume, structure matters")
    elif slides > 10:
        score += 2
        reasons.append(f"{slides} slides — moderate volume")

    # Grade level (higher grade = denser curriculum)
    if grade >= 11:
        score += 3
        reasons.append(f"Grade {grade} — board-level complexity")
    elif grade >= 9:
        score += 2
        reasons.append(f"Grade {grade} — secondary level")
    elif grade >= 7:
        score += 1

    # Subject difficulty
    hard_subjects = {
        "Physics", "Chemistry", "Mathematics", "Biology",
        "Computer Science", "Economics", "Accountancy"
    }
    if subject in hard_subjects:
        score += 1
        reasons.append(f"{subject} — technical subject")

    # Topic keyword complexity — catches things like "Organic Chemistry", "Quantum Mechanics"
    complex_keywords = [
        "quantum", "calculus", "organic", "thermodynamic", "genetics",
        "algorithm", "integration", "differentiation", "electrochemistry",
        "nuclear", "relativity", "trigonometry", "probability"
    ]
    topic_lower = topic.lower()
    matched = [kw for kw in complex_keywords if kw in topic_lower]
    if matched:
        score += 2
        reasons.append(f"Complex topic terms: {', '.join(matched)}")

    return score, reasons


def route(topic: str, grade: int, slides: int, subject: str) -> RoutingDecision:
    score, reasons = compute_complexity_score(topic, grade, slides, subject)

    model = MODEL_SMART if score >= 4 else MODEL_FAST

    cost_usd = (AVG_TOKENS / 1_000_000) * COST_PER_M[model]
    cost_inr = cost_usd * INR_PER_USD

    if not reasons:
        reasons = ["Standard request — fast model sufficient"]

    return RoutingDecision(
        model=model,
        score=score,
        reasons=reasons,
        estimated_cost_inr=round(cost_inr, 4),
    )


def cost_savings_vs_current(cost_inr: float, current_cost_inr: float = 15.0) -> dict:
    saved = current_cost_inr - cost_inr
    pct = (saved / current_cost_inr) * 100
    return {
        "current_cost_inr": current_cost_inr,
        "new_cost_inr": cost_inr,
        "saved_inr": round(saved, 4),
        "savings_pct": round(pct, 1),
    }