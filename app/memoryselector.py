import json

from app.memorymanagement import MemoryCandidate, Memory, MemoryCandidateStatus
from app.config import MODEL_NAME
from ollama import chat
from typing import Any
from datetime import datetime
from app.models import MemoryExtractionResult, ProposedMemory
from app.database import create_candidate
EXTRACTION_PROMPT = """
Identify only information that would still be useful
in a future conversation after the original messages
are no longer available.

Do not create a memory merely because something
was mentioned.

Prefer no memory over a weak memory.

Importance must be a number from 0.0 to 1.0.


USER_FACT
A reasonably stable factual detail about the user.

SHARED_EVENT
A meaningful event or interaction worth remembering
as part of the relationship history.

CHARACTER_INTERPRETATION
A tentative interpretation Rin has formed based on
evidence. Avoid unsupported psychological claims.
""".strip() #improve this prompt


def normalize_extraction_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("Memory extraction must be a JSON object.")

    normalized = dict(payload)
    normalized_memories = []

    for proposed_memory in normalized.get("memories", []):
        if not isinstance(proposed_memory, dict):
            raise TypeError("Each proposed memory must be a JSON object.")

        memory = dict(proposed_memory)
        if "importance" in memory:
            importance = float(memory["importance"])
            if 1.0 < importance <= 5.0:
                importance /= 5.0
            memory["importance"] = max(0.0, min(importance, 1.0))

        normalized_memories.append(memory)

    normalized["memories"] = normalized_memories
    return normalized


def extract_memory(
    extraction_messages: list[dict[str, Any]],
    recent_memories: list[Memory] | None
) -> MemoryExtractionResult:

    conversation_lines = []

    for message in extraction_messages:
        conversation_lines.append(
            f'[{message["id"]}] {message["role"].upper()}: '
            f'{message["content"]}'
        )

    conversation_text = "\n".join(conversation_lines)
    memories = []
    if not recent_memories:
        memories_text = "None."
    else:
        for memory in recent_memories:
            memories.append(memory.content) #for now
        memories_text = "\n".join(memories)

    prompt = f"""
        Recent memories (may not be relevant):
        {memories_text}

        Latest conversation messages:
        {conversation_text}

        consider what memories to keep and return the requested structured result.
        """.strip()
    response = chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": EXTRACTION_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        format=MemoryExtractionResult.model_json_schema(),
        options={
            "temperature": 0.1,
        },
    )
    #what if it needs to create multiple memories?
    payload = json.loads(response.message.content)
    return MemoryExtractionResult.model_validate(
        normalize_extraction_payload(payload)
    )



def validate_proposal(proposal, extraction_messages) -> bool:
    if len(proposal.content.strip()) < 10:
        return False

    valid_ids = {
        message["id"]
        for message in extraction_messages
    }
    proposed_ids = set(proposal.source_message_ids)

    if not proposed_ids:
        return False

    return proposed_ids.issubset(valid_ids)

def extract_and_store_candidates(
    extraction_messages: list[dict[str, Any]],
    recent_memories: list[Memory] | None,
) -> list[int]:
    result = extract_memory(extraction_messages, recent_memories)
    candidate_ids = []

    for proposal in result.memories:
        if validate_proposal(proposal, extraction_messages):
            candidate = proposal_to_candidate(proposal)
            candidate_ids.append(
                create_candidate(candidate, proposal.source_message_ids)
            )

    return candidate_ids



def proposal_to_candidate(proposal: ProposedMemory) -> MemoryCandidate:

    return MemoryCandidate(
        id = None,
        memory_type=proposal.memory_type,
        content=proposal.content,
        importance=proposal.importance,
        emotional_valence=proposal.emotional_valence,
        status=MemoryCandidateStatus.PENDING,
        created_at=datetime.now().isoformat()
    )
