from contextlib import asynccontextmanager
from json import JSONDecodeError
import logging
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from threading import Lock, Timer
from ollama import ResponseError
from pydantic import ValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.interactionanalyzer import analyze_interaction
from app.statechange import apply_analysis, enforce_relationship_policy
from app.state import ALLOWED_MOODS, create_default_state
from app.config import (
    DEFAULT_NUM_PREDICT,
    DEFAULT_REPEAT_PENALTY,
    DEFAULT_TEMPERATURE,
    DEFAULT_TEMPERATURE_STEP,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    MODEL_NAME,
    NUMBER_OF_EXCHANGE,
    MEMORY_EXTRACTION_INTERVAL,
    MEMORY_EXTRACTION_IDLE_SECONDS,
    MEMORY_EXTRACTION_FORCE_BACKLOG,
)
from app.memoryselector import extract_and_store_candidates
from app.memorymanagement import Memory, MemoryCandidate, MemoryCandidateStatus

from app.llm import get_assistant_response
from app.models import (
    ChatRequest,
    ChatResponse,
    CompanionStateModel,
    ConversationHistoryOut,
    DeleteHistoryResponse,
    GenerationSettingsOut,
    MessageOut,
    MemoryCandidateOut,
    MemoryOut,
    InteractionEventOut,
    PromptPreview,
    model_to_state,
    state_to_model,
)
from app.promptbuilder import build_system_prompt

from app.database import (
    delete_messages,
    get_or_create_default_conversation,
    initialize_database,
    load_messages,
    save_exchange,
    get_companion_state,
    save_companion_state,
    get_recent_messages,
    store_state_change_request,
    save_message,
    number_of_messages_in_conversation,
    load_recent_memories,
    get_all_candidates,
    get_candidate,
    get_candidate_sources,
    get_all_memories,
    get_memory_sources,
    accept_memory_candidate,
    reject_memory_candidate,
    load_recent_messages,
    get_recent_interaction_events,
    count_unprocessed_messages,
    load_unprocessed_messages,
    mark_memory_messages_processed,
) #imports all the functions from database.py


logger = logging.getLogger(__name__)


memory_extraction_lock = Lock()
memory_scheduler_lock = Lock()

memory_extraction_timers: dict[int, Timer] = {}
conversation_activity_versions: dict[int, int] = {}

def register_conversation_activity(
    conversation_id: int,
) -> int:
    with memory_scheduler_lock:
        existing_timer = memory_extraction_timers.pop(
            conversation_id,
            None,
        )

        if existing_timer is not None:
            existing_timer.cancel()

        version = (
            conversation_activity_versions.get(
                conversation_id,
                0,
            )
            + 1
        )

        conversation_activity_versions[
            conversation_id
        ] = version

        return version


def activity_is_current(
    conversation_id: int,
    activity_version: int,
) -> bool:
    with memory_scheduler_lock:
        return (
            conversation_activity_versions.get(
                conversation_id
            )
            == activity_version
        )


def run_memory_extraction_batch(
    conversation_id: int,
    through_message_id: int | None = None,
) -> list[int] | None:
    if not memory_extraction_lock.acquire(
        blocking=False
    ):
        return None

    try:
        messages = load_unprocessed_messages(
            conversation_id=conversation_id,
            limit=MEMORY_EXTRACTION_INTERVAL,
            through_message_id=through_message_id,
        )

        if len(messages) < MEMORY_EXTRACTION_INTERVAL:
            return []

        candidate_ids = extract_and_store_candidates(
            messages,
            load_recent_memories(2),
        )

        mark_memory_messages_processed(
            conversation_id,
            messages[-1]["id"],
        )

        logger.info(
            "Memory extraction processed messages through "
            "%s and created %s candidates.",
            messages[-1]["id"],
            len(candidate_ids),
        )
        return candidate_ids
    except Exception:
        logger.exception("Memory extraction failed.")
        raise
    finally:
        memory_extraction_lock.release()


def run_idle_memory_extraction(
    conversation_id: int,
    through_message_id: int,
    activity_version: int,
) -> None:
    with memory_scheduler_lock:
        memory_extraction_timers.pop(
            conversation_id,
            None,
        )

    if not activity_is_current(
        conversation_id,
        activity_version,
    ):
        return

    run_memory_extraction_batch(
        conversation_id,
        through_message_id,
    )


def schedule_memory_extraction(
    conversation_id: int,
    through_message_id: int,
    activity_version: int,
) -> None:
    if not activity_is_current(
        conversation_id,
        activity_version,
    ):
        return

    backlog = count_unprocessed_messages(
        conversation_id
    )

    if backlog < MEMORY_EXTRACTION_INTERVAL:
        return

    if backlog >= MEMORY_EXTRACTION_FORCE_BACKLOG:
        run_memory_extraction_batch(
            conversation_id,
            through_message_id,
        )
        return

    timer = Timer(
        MEMORY_EXTRACTION_IDLE_SECONDS,
        run_idle_memory_extraction,
        args=(
            conversation_id,
            through_message_id,
            activity_version,
        ),
    )
    timer.daemon = True

    with memory_scheduler_lock:
        previous_timer = memory_extraction_timers.get(
            conversation_id
        )

        if previous_timer is not None:
            previous_timer.cancel()

        memory_extraction_timers[
            conversation_id
        ] = timer

    timer.start()

def candidate_to_output(candidate: MemoryCandidate) -> MemoryCandidateOut:
    if candidate.id is None:
        raise ValueError("Stored candidate is missing its ID.")

    return MemoryCandidateOut(
        id=candidate.id,
        memory_type=candidate.memory_type,
        content=candidate.content,
        importance=candidate.importance,
        emotional_valence=candidate.emotional_valence,
        status=candidate.status,
        created_at=candidate.created_at,
        source_message_ids=get_candidate_sources(candidate.id),
    )


def memory_to_output(memory: Memory) -> MemoryOut:
    if memory.id is None:
        raise ValueError("Stored memory is missing its ID.")

    return MemoryOut(
        id=memory.id,
        memory_type=memory.memory_type,
        content=memory.content,
        importance=memory.importance,
        emotional_valence=memory.emotional_valence,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        is_active=memory.is_active,
        source_message_ids=get_memory_sources(memory.id),
    )

@asynccontextmanager
async def lifespan(_: FastAPI):
    #server opens
    initialize_database()
    yield
    #means does server stuff
    #after shut down, this code (currently nothing) executes

#does stuff quickly until yield and when shuts off connections, execute code after yield

app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def disable_frontend_asset_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response

# ok so this connects the static files from my folder/directory (on this computer) as in app/static 
# to the server route /static (like localhost:8000/static or something)
#this way the server uses the files to load the webpage
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


# index.html is actually just the main page for routes/things. and when the client requests GET at the root (/), a file (file response) would be returned
# the file returned is on my computer at app/static/index.html
#kind of similar to the mounting but this is for a file and that was for a folder
# this is for the / page, not the /static page. so the server sends you to /static when you go to /
@app.get("/", response_class=FileResponse)
async def index() -> FileResponse:
    return FileResponse("app/static/index.html")


# python decorator. so, when the server receives a GET request, it will call this functiond
# also /health is the url path for the endpoint. so, if you go to localhost:8000/health, it will return the json
@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "model": MODEL_NAME,
    }

#communicates front end js and back end llm
@app.get("/settings", response_model=GenerationSettingsOut)
def get_generation_settings() -> GenerationSettingsOut:
    return GenerationSettingsOut(
        model=MODEL_NAME,
        minimum_temperature=MIN_TEMPERATURE,
        maximum_temperature=MAX_TEMPERATURE,
        default_temperature=DEFAULT_TEMPERATURE,
        temperature_step=DEFAULT_TEMPERATURE_STEP,
        top_k=DEFAULT_TOP_K,
        top_p=DEFAULT_TOP_P,
        repeat_penalty=DEFAULT_REPEAT_PENALTY,
        num_predict=DEFAULT_NUM_PREDICT,
    )

@app.get(
    "/conversations/default/messages",
    response_model=ConversationHistoryOut,
)
def get_default_conversation_messages() -> ConversationHistoryOut:
    conversation_id = get_or_create_default_conversation()
    messages = load_messages(conversation_id)

    return ConversationHistoryOut(
        conversation_id=conversation_id,
        messages=messages,
    )


#this is setting up for the future which has multiple conversations with their unique id
@app.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationHistoryOut,
) #when accessing this path, use this response model and this function
def get_conversation_messages(conversation_id: int) -> ConversationHistoryOut:
    messages = load_messages(conversation_id) #this load all the messages in the conversation db with id. so including the history

    return ConversationHistoryOut(
        conversation_id=conversation_id,
        messages=messages,
    )


@app.delete(
    "/conversations/default/messages",
    response_model=DeleteHistoryResponse,
)
def delete_default_conversation_messages() -> DeleteHistoryResponse:
    conversation_id = get_or_create_default_conversation() #still using the default id = 1
    deleted_messages = delete_messages(conversation_id)

    return DeleteHistoryResponse(
        conversation_id=conversation_id,
        deleted_messages=deleted_messages, #how many deleted
    )


@app.delete(
    "/conversations/{conversation_id}/messages",
    response_model=DeleteHistoryResponse,
)
def delete_conversation_messages(conversation_id: int) -> DeleteHistoryResponse:
    deleted_messages = delete_messages(conversation_id)

    return DeleteHistoryResponse(
        conversation_id=conversation_id,
        deleted_messages=deleted_messages,
    )


# here it takes the ouput as chat request and returns a chat response. it also handles errors
@app.post("/chat", response_model=ChatResponse)
def chat_route(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
) -> ChatResponse:
    """takes a chatrequest, processes it, and returns the chatreponse"""
    #removes whitespace
    user_message = request.message.strip()
    
    #error if empty message
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    conversation_id = get_or_create_default_conversation()

    activity_version = register_conversation_activity(
        conversation_id
    )

    try:
        conversation_messages = load_messages(conversation_id)
        recent_context = get_recent_messages(
            conversation_id,
            number_of_exchanges=NUMBER_OF_EXCHANGE,
        )
        try:
            analysis = analyze_interaction(
                user_message=user_message,
                recent_context=recent_context,
            )
            analysis = enforce_relationship_policy(analysis)
        except (JSONDecodeError, ValidationError, TypeError, ValueError) as error:
            logger.exception("Interaction analyzer returned invalid structured data.")
            raise HTTPException(
                status_code=502,
                detail="Interaction analyzer returned invalid structured data.",
            ) from error

        state = get_companion_state()
        updated_state = apply_analysis(state, analysis)
        save_companion_state(updated_state)

        user_message_id = save_message(conversation_id, "user", user_message)
        store_state_change_request(conversation_id, user_message_id, analysis)

        conversation_messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        assistant_message, elapsed_time = get_assistant_response(
            conversation_messages,
            request.temperature,
            updated_state
        )
                
        assistant_message_id = save_message(
            conversation_id,
            "assistant",
            assistant_message,
        )

        background_tasks.add_task(
            schedule_memory_extraction,
            conversation_id,
            assistant_message_id,
            activity_version,
    )

 
    except ResponseError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama error: {error}",
        ) from error
    except ConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to Ollama.",
        ) from error
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Unexpected error while processing chat.")
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while processing chat.",
        ) from error



    #reformats the response to match the ChatResponse model or the ouptput format spcified
    return ChatResponse(
        response=assistant_message,
        model=MODEL_NAME,
        #model name from the config.py file
        elapsed_seconds=elapsed_time,
        conversation_id=conversation_id,
        temperature=request.temperature,
    )

@app.get(
    "/developer/state",
    response_model=CompanionStateModel,
)
def get_developer_state() -> CompanionStateModel:
    state = get_companion_state()
    return state_to_model(state)


@app.get(
    "/developer/interaction-events",
    response_model=list[InteractionEventOut],
)
def get_developer_interaction_events(
    limit: int = Query(default=12, ge=1, le=50),
) -> list[InteractionEventOut]:
    conversation_id = get_or_create_default_conversation()
    return [
        InteractionEventOut(**event)
        for event in get_recent_interaction_events(conversation_id, limit)
    ]

@app.post(
    "/developer/state/reset",
    response_model=CompanionStateModel,
)
def reset_developer_state() -> CompanionStateModel:
    state = create_default_state()
    save_companion_state(state)

    return state_to_model(state)


@app.get(
    "/developer/prompt",
    response_model=PromptPreview,
)
def get_prompt_preview() -> PromptPreview:
    state = get_companion_state()
    prompt = build_system_prompt(state)

    return PromptPreview(prompt=prompt)


@app.put(
    "/developer/state",
    response_model=CompanionStateModel,
)
def update_developer_state(
    state_model: CompanionStateModel,
) -> CompanionStateModel:
    if state_model.mood not in ALLOWED_MOODS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mood: {state_model.mood}",
        )

    save_companion_state(model_to_state(state_model))
    return state_model


@app.get(
    "/developer/memory/candidates",
    response_model=list[MemoryCandidateOut],
)
def get_memory_candidates() -> list[MemoryCandidateOut]:
    return [
        candidate_to_output(candidate)
        for candidate in get_all_candidates()
    ]


@app.get(
    "/developer/memories",
    response_model=list[MemoryOut],
)
def get_developer_memories() -> list[MemoryOut]:
    return [
        memory_to_output(memory)
        for memory in get_all_memories()
    ]


@app.post(
    "/developer/memory/extract",
    response_model=list[MemoryCandidateOut],
)
def extract_developer_memory_candidates() -> list[MemoryCandidateOut]:
    candidate_ids = run_memory_extraction_batch(
        get_or_create_default_conversation()
    )

    if candidate_ids is None:
        raise HTTPException(
            status_code=409,
            detail="Memory extraction is already running.",
        )

    candidates = [
        get_candidate(candidate_id)
        for candidate_id in candidate_ids
    ]

    return [
        candidate_to_output(candidate)
        for candidate in candidates
        if candidate is not None
    ]



@app.post(
    "/developer/memory/candidates/{candidate_id}/accept",
    response_model=MemoryCandidateOut,
)
def accept_candidate(candidate_id: int) -> MemoryCandidateOut:
    candidate = get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    if candidate.status != MemoryCandidateStatus.PENDING:
        raise HTTPException(status_code=409, detail="Candidate is already reviewed.")

    accept_memory_candidate(candidate_id)
    updated_candidate = get_candidate(candidate_id)
    if updated_candidate is None:
        raise HTTPException(status_code=500, detail="Candidate could not be reloaded.")

    return candidate_to_output(updated_candidate)



@app.post(
    "/developer/memory/candidates/{candidate_id}/reject",
    response_model=MemoryCandidateOut,
) 
def reject_candidate(candidate_id: int) -> MemoryCandidateOut:
    candidate = get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    if candidate.status != MemoryCandidateStatus.PENDING:
        raise HTTPException(status_code=409, detail="Candidate is already reviewed.")

    reject_memory_candidate(candidate_id)
    updated_candidate = get_candidate(candidate_id)
    if updated_candidate is None:
        raise HTTPException(status_code=500, detail="Candidate could not be reloaded.")

    return candidate_to_output(updated_candidate)
