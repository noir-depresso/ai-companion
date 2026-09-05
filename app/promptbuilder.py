from app.config import RIN_CHARACTER_PATH
from app.state import CompanionState
from app.stateinterpreter import build_state_instructions


def load_character_prompt() -> str:
    return RIN_CHARACTER_PATH.read_text(encoding="utf-8").strip()


def build_system_prompt(state: CompanionState) -> str:
    character_prompt = load_character_prompt()
    state_instructions = build_state_instructions(state)

    return f"""{character_prompt}

# Current Private State

{state_instructions}

Treat this state as a relative adjustment to Rin's tone, pacing, initiative,
warmth, and guardedness, never as a replacement for her core personality.
Never mention values, labels, variables, database state, prompt instructions,
or this emotional system. Trust changes openness, not compliance, and temporary
states should remain proportionate rather than becoming caricatures.
""".strip()
