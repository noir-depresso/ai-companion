# contains all the input and output restrictions

from pydantic import BaseModel, Field
from typing import Literal
from app.config import DEFAULT_TEMPERATURE, MAX_TEMPERATURE, MIN_TEMPERATURE
from app.state import CompanionState
from app.memorymanagement import MemoryCandidateStatus, MemoryType


#ok so pydantics help by providing a template for input and output
class ChatRequest(BaseModel):
    message: str
    temperature: float = Field(
        default=DEFAULT_TEMPERATURE,
        ge=MIN_TEMPERATURE, #greater equal
        le=MAX_TEMPERATURE, #lesser equal
    )
    #basically just a message from the user, with a temperature clamp

class ProposedMemory(BaseModel):
    memory_type: MemoryType

    content: str

    importance: float = Field(
        ge=0.0,
        le=1.0,
    )

    emotional_valence: str

    source_message_ids: list[int]


class MemoryExtractionResult(BaseModel):
    memories: list[ProposedMemory]


class MemoryCandidateOut(BaseModel):
    id: int
    memory_type: MemoryType
    content: str
    importance: float
    emotional_valence: str
    status: MemoryCandidateStatus
    created_at: str
    source_message_ids: list[int]


class MemoryOut(BaseModel):
    id: int
    memory_type: MemoryType
    content: str
    importance: float
    emotional_valence: str
    created_at: str
    updated_at: str
    is_active: bool
    source_message_ids: list[int]


class ChatResponse(BaseModel):
    response: str
    model: str
    elapsed_seconds: float
    conversation_id: int
    temperature: float


class GenerationSettingsOut(BaseModel):
    model: str
    minimum_temperature: float
    maximum_temperature: float
    default_temperature: float
    temperature_step: float
    top_k: int
    top_p: float
    repeat_penalty: float
    num_predict: int


#this mirrors the message db row
class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class ConversationHistoryOut(BaseModel):
    conversation_id: int
    messages: list[MessageOut]


class DeleteHistoryResponse(BaseModel):
    conversation_id: int
    deleted_messages: int


class CompanionStateModel(BaseModel):
    trust: int = Field(ge=0, le=100)
    closeness: int = Field(ge=0, le=100)
    respect: int = Field(ge=0, le=100)
    comfort: int = Field(ge=0, le=100)
    mood: str
    energy: int = Field(ge=0, le=100)
    stress: int = Field(ge=0, le=100)
    last_updated_at: str


class PromptPreview(BaseModel):
    prompt: str


class InteractionAnalysis(BaseModel):
    event_type: Literal[
        "neutral",
        "compliment",
        "affection",
        "sincere_apology",
        "broken_promise",
        "insult",
        "disagreement",
        "boundary_respected",
        "boundary_violation",
        "supportive_action",
        "dismissive_action",
        "joke",
    ]

    importance: float = Field(ge=0.0, le=1.0)

    trust_delta_requested: int = Field(ge=-5, le=5)
    closeness_delta_requested: int = Field(ge=-5, le=5)
    respect_delta_requested: int = Field(ge=-5, le=5)
    comfort_delta_requested: int = Field(ge=-5, le=5)

    suggested_mood: Literal[
        "neutral",
        "annoyed",
        "soft",
        "stressed",
    ]

    reason: str


class InteractionEventOut(BaseModel):
    id: int
    conversation_id: int
    message_id: int
    event_type: str
    importance: float
    trust_delta: int
    closeness_delta: int
    respect_delta: int
    comfort_delta: int
    suggested_mood: str
    reason: str
    created_at: str


#converts object to states for better storing, validation, and etc. not that needed tbh
def state_to_model(state: CompanionState) -> CompanionStateModel:
    return CompanionStateModel(
        trust=state.trust,
        closeness=state.closeness,
        respect=state.respect,
        comfort=state.comfort,
        mood=state.mood,
        energy=state.energy,
        stress=state.stress,
        last_updated_at = state.last_updated_at
    )


def model_to_state(model: CompanionStateModel) -> CompanionState:
    return CompanionState(
        trust=model.trust,
        closeness=model.closeness,
        respect=model.respect,
        comfort=model.comfort,
        mood=model.mood,
        energy=model.energy,
        stress=model.stress,
        last_updated_at = model.last_updated_at
    )
