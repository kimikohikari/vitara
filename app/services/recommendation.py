"""
Rule-based supplement recommendation engine.

This is the single source of truth — the frontend JS mirrors it for
instant UX, but the backend validates and persists the canonical result.

Adding a new supplement: add an entry to SUPPLEMENTS and implement
its trigger function. No other changes needed.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List
from app.schemas.quiz import QuizAnswers, SupplementInfo


@dataclass
class Supplement:
    key: str
    name: str
    latin: str
    emoji: str
    reason: str
    price: str
    trigger: Callable[[QuizAnswers], bool]
    # higher = shown first when multiple match
    priority: int = 0


# ── Supplement catalogue ─────────────────────────────────────────────────────

SUPPLEMENTS: List[Supplement] = [
    Supplement(
        key="magnesium",
        name="Magnesium Glycinate",
        latin="Magnesium bisglycinate chelate",
        emoji="🌙",
        reason="Supports deep sleep and calms the nervous system. Glycinate form is highly absorbable with minimal digestive side effects.",
        price="€24.90/month",
        priority=10,
        trigger=lambda a: a.sleep != "good" or a.stress in ("high", "extreme"),
    ),
    Supplement(
        key="ashwagandha",
        name="Ashwagandha KSM-66",
        latin="Withania somnifera root extract",
        emoji="🌿",
        reason="An adaptogen clinically shown to reduce cortisol levels and improve stress resilience. Best-studied extract form.",
        price="€22.90/month",
        priority=9,
        trigger=lambda a: a.stress in ("moderate", "high", "extreme"),
    ),
    Supplement(
        key="vitamin_b",
        name="Vitamin B Complex",
        latin="B1, B2, B3, B5, B6, B9, B12",
        emoji="⚡",
        reason="Directly fuels energy metabolism at the cellular level. Essential if you rely on caffeine or eat an unbalanced diet.",
        price="€18.90/month",
        priority=8,
        trigger=lambda a: a.energy in ("low", "slump", "crashes") or a.focus == "caffeine" or a.diet == "poor",
    ),
    Supplement(
        key="omega3",
        name="Omega-3 EPA/DHA",
        latin="Fish oil concentrate (IFOS certified)",
        emoji="🐟",
        reason="Supports brain clarity, mood and cardiovascular health. Especially important for those eating few fatty fish.",
        price="€26.90/month",
        priority=7,
        trigger=lambda a: a.focus in ("fog", "poor") or a.diet in ("poor", "vegan"),
    ),
    Supplement(
        key="vitamin_d3",
        name="Vitamin D3 + K2",
        latin="Cholecalciferol + menaquinone MK-7",
        emoji="☀️",
        reason="Most people in northern latitudes are deficient in D3. K2 ensures calcium goes to bones, not arteries.",
        price="€16.90/month",
        priority=6,
        trigger=lambda a: a.activity in ("low", "none") or a.energy == "low",
    ),
    Supplement(
        key="rhodiola",
        name="Rhodiola Rosea",
        latin="Rhodiola rosea root, 3% rosavins",
        emoji="🧠",
        reason="Reduces mental fatigue and improves cognitive performance under stress. Popular with students and knowledge workers.",
        price="€21.90/month",
        priority=5,
        trigger=lambda a: a.focus in ("poor", "fog") or a.energy == "crashes" or a.stress == "high",
    ),
    Supplement(
        key="creatine",
        name="Creatine Monohydrate",
        latin="Creatine monohydrate, micronised",
        emoji="💪",
        reason="Proven to boost physical performance and increasingly shown to enhance working memory and mental energy.",
        price="€19.90/month",
        priority=4,
        trigger=lambda a: a.activity in ("high", "moderate"),
    ),
    Supplement(
        key="iron_b12",
        name="Iron + B12 Complex",
        latin="Ferrous bisglycinate + methylcobalamin",
        emoji="🌱",
        reason="Plant-based diets often lack haem iron and B12, leading to fatigue and brain fog. This combination corrects both.",
        price="€23.90/month",
        priority=3,
        trigger=lambda a: a.diet == "vegan",
    ),
]

# Fallback order when fewer than MAX_RECS match
_FALLBACK_KEYS = ["vitamin_d3", "vitamin_b", "omega3"]
MAX_RECS = 3


def get_recommendations(answers: QuizAnswers) -> List[SupplementInfo]:
    """
    Run all triggers and return top MAX_RECS matches by priority.
    Always returns exactly MAX_RECS items — fills with fallbacks if needed.
    """
    matched = sorted(
        [s for s in SUPPLEMENTS if s.trigger(answers)],
        key=lambda s: s.priority,
        reverse=True,
    )

    result: List[Supplement] = matched[:MAX_RECS]

    if len(result) < MAX_RECS:
        matched_keys = {s.key for s in result}
        for fk in _FALLBACK_KEYS:
            if len(result) >= MAX_RECS:
                break
            if fk not in matched_keys:
                fallback = next((s for s in SUPPLEMENTS if s.key == fk), None)
                if fallback:
                    result.append(fallback)

    return [
        SupplementInfo(
            key=s.key,
            name=s.name,
            latin=s.latin,
            emoji=s.emoji,
            reason=s.reason,
            price=s.price,
        )
        for s in result
    ]


def build_summary(answers: QuizAnswers) -> str:
    issues: List[str] = []
    if answers.energy in ("low", "slump", "crashes"):
        issues.append("low energy")
    if answers.sleep != "good":
        issues.append("sleep challenges")
    if answers.stress in ("high", "extreme"):
        issues.append("high stress")
    if answers.focus in ("poor", "fog"):
        issues.append("focus issues")
    if answers.diet == "vegan":
        issues.append("plant-based diet gaps")
    if not issues:
        issues.append("general wellness optimisation")
    return f"Based on your answers we identified: {', '.join(issues)}."
