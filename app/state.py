from dataclasses import dataclass
from datetime import datetime

from app.config import DEFAULT_TRUST, DEFAULT_CLOSENESS, DEFAULT_RESPECT, DEFAULT_COMFORT, DEFAULT_MOOD, DEFAULT_ENERGY, DEFAULT_STRESS

# current mood list. TBD
ALLOWED_MOODS = {
    "neutral",
    "annoyed",
    "soft",
    "stressed",
}

#data class is basically just helping programmers write common boiler plate functions like init, repl, eql, etc
@dataclass
class CompanionState:
    trust: int
    closeness: int
    respect: int
    comfort: int
    mood: str
    energy: int
    stress: int
    last_updated_at: str


def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(value, maximum))


def validate_mood(mood: str) -> str:
    normalized_mood = mood.strip().lower()

    if normalized_mood not in ALLOWED_MOODS:
        raise ValueError(f"Invalid mood: {mood}")

    return normalized_mood


def create_default_state() -> CompanionState:
    return CompanionState(
        trust=DEFAULT_TRUST,
        closeness=DEFAULT_CLOSENESS,
        respect=DEFAULT_RESPECT,
        comfort=DEFAULT_COMFORT,
        mood=DEFAULT_MOOD,
        energy=DEFAULT_ENERGY,
        stress=DEFAULT_STRESS,
        last_updated_at=datetime.now().isoformat()
    )
