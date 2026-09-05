MAX_RELATIONSHIP_DELTA = 3
from app.state import CompanionState, clamp
from app.models import InteractionAnalysis
from datetime import datetime
from app.config import DEFAULT_STRESS, DEFAULT_ENERGY, ENERGY_DECAY_RATE, STRESS_DECAY_RATE


EVENT_ALLOWED_MOODS = {
    "neutral": {"neutral"},
    "compliment": {"neutral", "soft"},
    "affection": {"neutral", "soft"},
    "sincere_apology": {"neutral", "soft"},
    "broken_promise": {"neutral", "annoyed"},
    "insult": {"annoyed", "stressed"},
    "disagreement": {"neutral", "annoyed"},
    "boundary_respected": {"neutral", "soft"},
    "boundary_violation": {"annoyed", "stressed"},
    "supportive_action": {"neutral", "soft"},
    "dismissive_action": {"neutral", "annoyed"},
    "joke": {"neutral", "soft"},
}

EVENT_STRESS_EFFECTS = {
    "neutral": 0,
    "compliment": -4,
    "affection": -8,
    "sincere_apology": -20,
    "broken_promise": 25,
    "insult": 40,
    "disagreement": 8,
    "boundary_respected": -8,
    "boundary_violation": 45,
    "supportive_action": -15,
    "dismissive_action": 25,
    "joke": -5,
}

TRUST_LOSS_EVENTS = {
    "broken_promise",
    "insult",
    "boundary_violation",
    "dismissive_action",
}

NON_PUNITIVE_EVENTS = {
    "neutral",
    "compliment",
    "affection",
    "sincere_apology",
    "disagreement",
    "boundary_respected",
    "supportive_action",
    "joke",
}

MINIMUM_NEGATIVE_IMPORTANCE = 0.6


def enforce_relationship_policy(
    analysis: InteractionAnalysis,
) -> InteractionAnalysis:
    data = analysis.model_dump()
    delta_fields = (
        "trust_delta_requested",
        "closeness_delta_requested",
        "respect_delta_requested",
        "comfort_delta_requested",
    )
    changed = False

    if analysis.event_type == "neutral":
        for field in delta_fields:
            if data[field] != 0:
                data[field] = 0
                changed = True

    if analysis.importance < MINIMUM_NEGATIVE_IMPORTANCE:
        for field in delta_fields:
            if data[field] < 0:
                data[field] = 0
                changed = True

    if analysis.event_type in NON_PUNITIVE_EVENTS:
        for field in delta_fields:
            if data[field] < 0:
                data[field] = 0
                changed = True

    if (
        data["trust_delta_requested"] < 0
        and analysis.event_type not in TRUST_LOSS_EVENTS
    ):
        data["trust_delta_requested"] = 0
        changed = True

    if changed:
        data["reason"] = (
            f'{analysis.reason} Relationship policy removed unsupported '
            "negative deltas."
        )

    return InteractionAnalysis.model_validate(data)

def apply_stress_effect(
    state: CompanionState,
    analysis: InteractionAnalysis,
) -> None:
    maximum_effect = EVENT_STRESS_EFFECTS[
        analysis.event_type
    ]

    if maximum_effect > 0 and analysis.importance < MINIMUM_NEGATIVE_IMPORTANCE:
        maximum_effect = 0

    actual_effect = round(
        maximum_effect * analysis.importance
    )

    state.stress = clamp(
        state.stress + actual_effect
    )

def choose_mood(
    current_mood: str,
    analysis: InteractionAnalysis,
) -> str:
    if analysis.event_type == "neutral":
        return current_mood

    allowed = EVENT_ALLOWED_MOODS[
        analysis.event_type
    ]

    if analysis.suggested_mood in allowed:
        return analysis.suggested_mood

    return current_mood

def get_allowed_delta(importance: float) -> int:
    if importance < 0.3:
        return 0

    if importance < 0.6:
        return 1

    if importance < 0.85:
        return 2

    return 3


def limit_delta(
    requested: int,
    importance: float,
) -> int:
    maximum = get_allowed_delta(importance)

    return max(
        -maximum,
        min(requested, maximum),
    )


def apply_analysis(
    state: CompanionState,
    analysis: InteractionAnalysis,
) -> CompanionState:
    hours = hours_since(state.last_updated_at)
    state.energy = decay_toward_baseline(state.energy, DEFAULT_ENERGY, ENERGY_DECAY_RATE, hours)
    state.stress = decay_toward_baseline(state.stress, DEFAULT_STRESS, STRESS_DECAY_RATE, hours)
    apply_stress_effect(state, analysis)
    state.mood = decay_mood(state)
    state.mood = choose_mood(state.mood, analysis)

    # state.energy = calculate_energy(datetime.now().hour) #NEEDS TO IMPROVED

    trust_delta = limit_delta(
        analysis.trust_delta_requested,
        analysis.importance,
    )

    closeness_delta = limit_delta(
        analysis.closeness_delta_requested,
        analysis.importance,
    )

    respect_delta = limit_delta(
        analysis.respect_delta_requested,
        analysis.importance,
    )

    comfort_delta = limit_delta(
        analysis.comfort_delta_requested,
        analysis.importance,
    )

    state.trust = clamp(
        state.trust + trust_delta
    )

    state.closeness = clamp(
        state.closeness + closeness_delta
    )

    state.respect = clamp(
        state.respect + respect_delta
    )

    state.comfort = clamp(
        state.comfort + comfort_delta
    )
    state.last_updated_at = datetime.now().isoformat()
    return state


def decay_toward_baseline(
    value: float,
    baseline: float,
    rate: float,
    hours: float,
) -> float:
    difference = value - baseline

    return round(baseline + difference * ((1 - rate) ** hours))

def decay_mood(state: CompanionState):
    #VERY SIMPLIFIED. WILL NEED TO BE EXPANDED UPON
    if state.stress >= 65:
        return "annoyed"

    elif state.stress >= 40:
        return "annoyed" #something else has to be added

    else:
        return "neutral"

def calculate_energy(hour: int) -> int:
    #also very simplified
    if 0 <= hour < 7:
        return 25
    elif 7 <= hour < 11:
        return 60
    elif 11 <= hour < 18:
        return 75
    elif 18 <= hour < 23:
        return 60
    else:
        return 40



def hours_since(timestamp: str) -> float:
    previous = datetime.fromisoformat(timestamp)
    now = datetime.now()

    elapsed = now - previous

    return max(0.0, elapsed.total_seconds() / 3600)


