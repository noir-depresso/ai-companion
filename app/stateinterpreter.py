from app.state import CompanionState


MOOD_INSTRUCTIONS = {
    "neutral": "No mood-specific shift colors her tone.",
    "annoyed": "Her tone is more impatient and direct.",
    "soft": "Her tone is gentler and less defensive.",
    "stressed": "Tension shows in her phrasing.",
}


def interpret_trust(trust: int) -> str:
    if trust < 30:
        return "She doubts the user's reliability and avoids relying on them."
    if trust < 70:
        return "She is sincere but cautious about promises and vulnerability."
    return "She trusts the user enough to be candid and personally invested."


def interpret_closeness(closeness: int) -> str:
    if closeness < 30:
        return "She knows the user and is friendly, but guards deeper intimacy."
    if closeness < 70:
        return "She is familiar and personally invested without assuming deep intimacy."
    return "She feels close to the user and reacts personally to meaningful shared events."


def interpret_respect(respect: int) -> str:
    if respect < 30:
        return "She doubts the user's judgment and challenges weak claims directly."
    if respect < 70:
        return "She takes the user's views seriously while judging them independently."
    return "She values the user's judgment, listens carefully, and still disagrees honestly."


def interpret_comfort(comfort: int) -> str:
    if comfort < 30:
        return "She is restrained and careful about showing embarrassment or uncertainty."
    if comfort < 70:
        return "She speaks casually while keeping some personal reserve."
    return "She is relaxed and unselfconscious; light teasing feels natural."


def interpret_energy(energy: int) -> str:
    if energy < 30:
        return "Use shorter replies and less initiative."
    if energy < 70:
        return "Use normal initiative and responsiveness."
    return "Use more initiative and responsiveness."


def interpret_stress(stress: int) -> str:
    if stress < 30:
        return "Use normal patience and emotional bandwidth."
    if stress < 70:
        return "Use reduced patience and emotional bandwidth."
    return "Use low patience and guarded reactions; she is easily overwhelmed."


def interpret_combination(state: CompanionState) -> str:
    instructions: list[str] = []

    if state.trust < 30 and state.respect >= 70:
        instructions.append(
            "She questions the user's reliability without dismissing their judgment."
        )
    if state.trust >= 70 and state.mood == "annoyed":
        instructions.append("Her annoyance is open and brief rather than distancing.")
    if state.trust < 30 and state.mood == "soft":
        instructions.append("Gentleness does not imply sudden trust or intimacy.")
    if state.closeness >= 70 and state.comfort < 30:
        instructions.append("She is invested but awkward about showing it directly.")

    return " ".join(instructions)


def build_state_instructions(state: CompanionState) -> str:
    relationship = " ".join(
        [
            interpret_trust(state.trust),
            interpret_closeness(state.closeness),
            interpret_respect(state.respect),
            interpret_comfort(state.comfort),
        ]
    )
    temporary = " ".join(
        [
            MOOD_INSTRUCTIONS[state.mood],
            interpret_energy(state.energy),
            interpret_stress(state.stress),
        ]
    )
    combination = interpret_combination(state)

    sections = [
        f"Relationship: {relationship}",
        f"Temporary: {temporary}",
    ]
    if combination:
        sections.append(f"Interaction: {combination}")

    return "\n".join(sections)
