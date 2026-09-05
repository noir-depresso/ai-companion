import json

from app.models import InteractionAnalysis
from app.config import SMALL_MODEL
from ollama import chat
ANALYSIS_SYSTEM_PROMPT = """
You classify interactions for a fictional companion relationship system.

Analyze only the user's latest interaction in context.

Return conservative state-change requests.

Rules:
- Classify how the user treated the companion, not whether the topic or emotion was negative.
- Ordinary conversation should usually produce little or no relationship change.
- Never reward generic compliments heavily.
- Never punish ordinary disagreement.
- Do not infer hostility when the message is ambiguous.
- Confusion, questions, corrections, forgetfulness, and harmless teasing are not insults.
- Vulnerability about jealousy, insecurity, sadness, envy, or dissatisfaction is not hostility toward the companion.
- Personal disclosure should usually be neutral or supportive and may increase closeness; it must not reduce trust merely because the disclosed feeling is negative.
- Trust may decrease only for clear deception, a broken promise, a direct personal insult, manipulation, or a boundary violation.
- Challenging the companion's knowledge, asking what they remember, or saying "haha" is neutral unless the wording contains clear contempt.
- If intent is unclear, choose neutral with zero relationship deltas.
- Importance below 0.5 must not request any negative relationship delta.
- Relationship changes should usually be between -2 and +2.
- Values of -3 to +3 should be rare.
- Never use -4, -5, +4, or +5 unless the event is exceptionally significant.
- A mood change may happen without a relationship change.
- Importance must be a number from 0.0 to 1.0.
- Explain the classification briefly and concretely.
""".strip()


def normalize_analysis_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise TypeError("Interaction analysis must be a JSON object.")

    normalized = dict(payload)

    if "importance" in normalized:
        importance = float(normalized["importance"])
        normalized["importance"] = max(0.0, min(importance, 1.0))

    delta_fields = (
        "trust_delta_requested",
        "closeness_delta_requested",
        "respect_delta_requested",
        "comfort_delta_requested",
    )
    for field in delta_fields:
        if field in normalized:
            requested = round(float(normalized[field]))
            normalized[field] = max(-5, min(requested, 5))

    return normalized


def analyze_interaction(
    user_message: str,
    recent_context: str,
) -> InteractionAnalysis:

    prompt = f"""
Recent conversation:
{recent_context}

Latest user message:
{user_message}

Classify the interaction and return the requested structured result.
""".strip()

    response = chat(
        model=SMALL_MODEL,
        messages=[
            {
                "role": "system",
                "content": ANALYSIS_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        format=InteractionAnalysis.model_json_schema(),
        options={
            "temperature": 0,
        },
    )

    payload = json.loads(response.message.content)
    return InteractionAnalysis.model_validate(
        normalize_analysis_payload(payload)
    )
