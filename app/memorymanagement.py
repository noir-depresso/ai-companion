from dataclasses import dataclass
from enum import Enum
class MemoryType(str, Enum):
    USER_FACT = "USER_FACT"
    SHARED_EVENT = "SHARED_EVENT"
    CHARACTER_INTERPRETATION = "CHARACTER_INTERPRETATION"

@dataclass
class Memory:
    id: int | None
    memory_type: MemoryType
    content: str
    importance: float
    emotional_valence: str
    created_at: str
    updated_at: str
    is_active: bool


class MemoryCandidateStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass
class MemoryCandidate:
    id: int | None
    memory_type: MemoryType
    content: str
    importance: float
    emotional_valence: str
    status: MemoryCandidateStatus
    created_at: str


