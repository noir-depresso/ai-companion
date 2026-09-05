#deals with the database stuff. saves and loads messages into the messages db, conversation db, and state db

import sqlite3
# this is a sql that stores data locally basically on the local server side. it wont be affected by restarts and refreshes. it keeps things consistent
from typing import Any
from app.models import InteractionAnalysis
from app.config import DATABASE_PATH, MESSAGE_LIMIT #where the data is stored.
from app.memorymanagement import Memory, MemoryType, MemoryCandidate, MemoryCandidateStatus
from datetime import datetime
from app.state import (
    CompanionState,
    clamp,
    create_default_state,
    validate_mood,
)



# this connects sqlite to the database
def get_connection() -> sqlite3.Connection: #returns the connection
    """not sure yet??"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True) # creates the db if not already there i think

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row #no idea
    connection.execute("PRAGMA foreign_keys = ON") #no idea what pragma means. but foreign keys is turned on i guess

    return connection


def initialize_database() -> None:
    """creates the conversation db and messages db. then links them up"""
    with get_connection() as connection: #idk what with means

#==============================CONVERSATIONS AND MESSAGES=================================



#-----------------------------conversations-----------------------------------------------
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """ #runs the commands to make a table with the primary key (for keeping stuff in order and identifying) and the time the row is created
            #this is for the table called conversations. it basically isnt even used yet
        )
#-----------------------------messages-----------------------------------------------
        connection.execute( #this is for the messages db
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL, 
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
            """
            #i got no clue what the "on delete cascade:" mean
        )
#=============================STATES===============================================



#-----------------------------states-----------------------------------------------
        default_state = create_default_state()
        
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS companion_state (
                id INTEGER PRIMARY KEY CHECK (id = 1), 
                trust INTEGER NOT NULL CHECK (trust BETWEEN 0 AND 100),
                closeness INTEGER NOT NULL CHECK (closeness BETWEEN 0 AND 100),
                respect INTEGER NOT NULL CHECK (respect BETWEEN 0 AND 100),
                comfort INTEGER NOT NULL CHECK (comfort BETWEEN 0 AND 100),
                mood TEXT NOT NULL,
                energy INTEGER NOT NULL CHECK (energy BETWEEN 0 AND 100),
                stress INTEGER NOT NULL CHECK (stress BETWEEN 0 AND 100),
                last_updated_at TEXT NOT NULL
            )
            """
            #weird primary key check that needs to be fixed
        )

#------------------------add default values to state--------------------------------
        connection.execute(
            """
            INSERT OR IGNORE INTO companion_state (
                id,
                trust,
                closeness,
                respect,
                comfort,
                mood,
                energy,
                stress,
                last_updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                default_state.trust,
                default_state.closeness,
                default_state.respect,
                default_state.comfort,
                default_state.mood,
                default_state.energy,
                default_state.stress,
                default_state.last_updated_at
            ),
            #if state already exists, ignore. but if its empty then choose to put in the default values
        )

#-----------------------------state changes-----------------------------------------------
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS interaction_events (
                id INTEGER PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                importance REAL NOT NULL,
                trust_delta INTEGER NOT NULL,
                closeness_delta INTEGER NOT NULL,
                respect_delta INTEGER NOT NULL,
                comfort_delta INTEGER NOT NULL,
                suggested_mood TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (message_id)
                    REFERENCES messages(id)
                    ON DELETE CASCADE
            )
            """
        )
#=========================MEMORY MANAGEMENT================================


#--------------------------memories-------------------------------------
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL NOT NULL,
                emotional_valence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )


#--------------------------memory sources------------------------------------
        connection.execute(
            """
                CREATE TABLE IF NOT EXISTS memory_sources (
                    memory_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    FOREIGN KEY (memory_id) REFERENCES memories(id),
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                )
            """
        )
#----------------------------memory_candidates--------------------------------
        connection.execute(
            """CREATE TABLE IF NOT EXISTS memory_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL NOT NULL,
                emotional_valence TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL
                )
            """
        )
       





#--------------------------candidate_sources------------------------------
        connection.execute(
            """CREATE TABLE IF NOT EXISTS candidate_sources (
                candidate_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,

                FOREIGN KEY (candidate_id)
                    REFERENCES memory_candidates(id),

                FOREIGN KEY (message_id)
                    REFERENCES messages(id)
            )
            """
        )
#----------------------------last message processed id----------------------------------
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_extraction_progress (
                conversation_id INTEGER PRIMARY KEY,
                last_processed_message_id INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
            """
        )
#===========================END OF INITIALIZATION===========================================



#===================processing message functions=======================
def count_unprocessed_messages(conversation_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS message_count
            FROM messages
            WHERE conversation_id = ?
              AND id > COALESCE(
                  (
                      SELECT last_processed_message_id
                      FROM memory_extraction_progress
                      WHERE conversation_id = ?
                  ),
                  0
              )
            """,
            (conversation_id, conversation_id),
        ).fetchone()

    return int(row["message_count"])


def load_unprocessed_messages(
    conversation_id: int,
    limit: int,
    through_message_id: int | None = None,
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
              AND id > COALESCE(
                  (
                      SELECT last_processed_message_id
                      FROM memory_extraction_progress
                      WHERE conversation_id = ?
                  ),
                  0
               )
              AND (? IS NULL OR id <= ?)
            ORDER BY id ASC
            LIMIT ?
            """,
            (
                conversation_id,
                conversation_id,
                through_message_id,
                through_message_id,
                limit,
            ),
        ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def mark_memory_messages_processed(
    conversation_id: int,
    last_message_id: int,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO memory_extraction_progress (
                conversation_id,
                last_processed_message_id
            )
            VALUES (?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                last_processed_message_id =
                    excluded.last_processed_message_id
            """,
            (conversation_id, last_message_id),
        )


def reset_memory_extraction_progress(conversation_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM memory_extraction_progress
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )

#=========================MEMORY FUNCTIONS=================================

def create_memory(memory: Memory, source_message_ids: list[int]) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO memories (
                memory_type,
                content,
                importance,
                emotional_valence,
                created_at,
                updated_at,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (   
                memory.memory_type,
                memory.content,
                memory.importance,
                memory.emotional_valence,
                memory.created_at,
                memory.updated_at,
                int(memory.is_active),
                ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Memory insert did not return an ID")
        memory_id = int(cursor.lastrowid)
        
        connection.executemany(
            """
            INSERT INTO memory_sources (memory_id, message_id)
            VALUES (?, ?)
            """,
            [
                (memory_id, message_id)
                for message_id in source_message_ids
            ],
        ) #so mysterious
    return memory_id


def get_memory(memory_id: int) -> Memory | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, memory_type, content, importance, emotional_valence, created_at, updated_at, is_active
            FROM memories
            WHERE id = ?
            ORDER BY id ASC
            """,
            (memory_id,),
        ).fetchone()

    if row is None:
            return None

    return Memory(
        id=int(row["id"]),
        memory_type=MemoryType(row["memory_type"]),
        content=row["content"],
        importance=float(row["importance"]),
        emotional_valence=row["emotional_valence"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        is_active=bool(row["is_active"]),
    )


def load_recent_memories(count: int = 1) -> list[Memory]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, memory_type, content, importance, emotional_valence, created_at, updated_at, is_active
            FROM(
                SELECT id, memory_type, content, importance, emotional_valence, created_at, updated_at, is_active
                FROM memories
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (count,),
        ).fetchall()

    return [Memory(
        id=int(row["id"]),
        memory_type=MemoryType(row["memory_type"]),
        content=row["content"],
        importance=float(row["importance"]),
        emotional_valence=row["emotional_valence"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        is_active=bool(row["is_active"]),
    )
        for row in rows
    ]


def get_active_memories() -> list[Memory]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                memory_type,
                content,
                importance,
                emotional_valence,
                created_at,
                updated_at,
                is_active
            FROM memories
            WHERE is_active = 1
            ORDER BY id ASC
            """
        ).fetchall()


        return [
            Memory(
                id=int(row["id"]),
                memory_type=MemoryType(row["memory_type"]),
                content=row["content"],
                importance=float(row["importance"]),
                emotional_valence=row["emotional_valence"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                is_active=bool(row["is_active"])
            )
            for row in rows
        ]


def get_all_memories() -> list[Memory]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                memory_type,
                content,
                importance,
                emotional_valence,
                created_at,
                updated_at,
                is_active
            FROM memories
            ORDER BY id DESC
            """
        ).fetchall()

    return [
        Memory(
            id=int(row["id"]),
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            importance=float(row["importance"]),
            emotional_valence=row["emotional_valence"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_active=bool(row["is_active"]),
        )
        for row in rows
    ]


def add_memory_sources(memory_id: int, message_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO memory_sources(
                memory_id,
                message_id
            )
            VALUES(?,?)
            """,
            (
                memory_id,
                message_id
            )
        )



def get_memory_sources(memory_id: int):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT message_id
            FROM memory_sources
            WHERE memory_id = ?
            ORDER BY message_id ASC
            """
        ,(memory_id,),
        ).fetchall()

    temp = []
    for row in rows:
        temp.append(int(row["message_id"]))
    return temp

#===========================MEMORY CANDIDATES FUNCTIONS================================
def create_candidate(candidate: MemoryCandidate, source_message_ids: list[int]) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO memory_candidates  (
                memory_type,
                content,
                importance,
                emotional_valence,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (   
                candidate.memory_type,
                candidate.content,
                candidate.importance,
                candidate.emotional_valence,
                candidate.status,
                candidate.created_at
                ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Candidate insert did not return an ID")
        candidate_id = int(cursor.lastrowid)
        
        connection.executemany(
            """
            INSERT INTO candidate_sources (candidate_id, message_id)
            VALUES (?, ?)
            """,
            [
                (candidate_id, message_id)
                for message_id in source_message_ids
            ],
        ) 
    return candidate_id


def get_candidate(candidate_id: int) -> MemoryCandidate | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, memory_type, content, importance, emotional_valence, status, created_at
            FROM memory_candidates 
            WHERE id = ?
            ORDER BY id ASC
            """,
            (candidate_id,),
        ).fetchone()

    if row is None:
            return None

    return MemoryCandidate(
        id=int(row["id"]),
        memory_type=MemoryType(row["memory_type"]),
        content=row["content"],
        importance=float(row["importance"]),
        emotional_valence=row["emotional_valence"],
        status=MemoryCandidateStatus(row["status"]),
        created_at=row["created_at"]
    )


def get_all_candidates() -> list[MemoryCandidate]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, memory_type, content, importance, emotional_valence, status, created_at
            FROM memory_candidates 
            ORDER BY id ASC
            """,
        ).fetchall()

    return [
        MemoryCandidate(
            id=int(row["id"]),
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            importance=float(row["importance"]),
            emotional_valence=row["emotional_valence"],
            status=MemoryCandidateStatus(row["status"]),
            created_at=row["created_at"]
        )
        for row in rows
    ]

def set_candidate_status(candidate_id: int, new_status: MemoryCandidateStatus) -> None:
    if get_candidate(candidate_id) == None:
        return
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE memory_candidates
            SET status = ?
            WHERE id = ? 
            """,
            (new_status.value, candidate_id)
        )
    return None
    

def add_candidate_sources(candidate_id: int, message_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO candidate_sources(
                candidate_id,
                message_id
            )
            VALUES(?,?)
            """,
            (
                candidate_id,
                message_id
            )
        )



def get_candidate_sources(candidate_id: int):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT message_id
            FROM candidate_sources
            WHERE candidate_id = ?
            ORDER BY message_id ASC
            """
        ,(candidate_id,),
        ).fetchall()

    return [
        int(row["message_id"])
        for row in rows
    ]


def accept_memory_candidate(candidate_id: int) -> int | None:
    candidate = get_candidate(candidate_id)
    if candidate is not None and candidate.status == MemoryCandidateStatus.PENDING:
        memory = Memory(None, candidate.memory_type, candidate.content, candidate.importance, candidate.emotional_valence, candidate.created_at, datetime.now().isoformat(), True)
        #create a new memory

        memory_id = create_memory(
            memory,
            get_candidate_sources(candidate_id)
        )
        
        set_candidate_status(candidate_id, MemoryCandidateStatus.ACCEPTED)
        return memory_id
    return None


def reject_memory_candidate(candidate_id: int) -> int | None:
    candidate = get_candidate(candidate_id)
    if candidate is None or candidate.status != MemoryCandidateStatus.PENDING:
        return None
    set_candidate_status(
        candidate_id,
        MemoryCandidateStatus.REJECTED,
    )
    return candidate_id
#====================================CONVERSATION AND MESSAGES====================================

# def create_conversation() -> int:
#     with get_connection() as connection:
#         cursor = connection.execute(
#             """
#             INSERT INTO conversations DEFAULT VALUES
#             """
#         )

#         return int(cursor.lastrowid) #returns primary key id for organizing and maybe sorting purposes. but it is inserted into the conversation db


def get_or_create_default_conversation() -> int:
    """returns the conversation id of 1. creates one if there isnt one"""
    #this needs to be changed to different conversation ids...
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM conversations
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        #finds and fetches the conversation with id 1

        if row is not None:
            return int(row["id"])

        #if the row is none. so the first time?
        cursor = connection.execute(
            """
            INSERT INTO conversations DEFAULT VALUES
            """
        )

        return int(cursor.lastrowid)

# isnt actually used for now, its been replaced by the save_exchange
def save_message(
    conversation_id: int,
    role: str,
    content: str,
) -> int:
    """saves content into a row in messages. CURRENTLY UNUSED"""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (conversation_id, role, content),
        )
        #cursor creates this row in messages db and gives it values

        return int(cursor.lastrowid)

def save_exchange(
    conversation_id: int,
    user_message: str,
    assistant_message: str,
) -> tuple[int, int]:
    with get_connection() as connection:
        user_cursor = connection.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (conversation_id, "user", user_message),
        )

        assistant_cursor = connection.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (conversation_id, "assistant", assistant_message),
        )

        return int(user_cursor.lastrowid), int(assistant_cursor.lastrowid)


def load_messages(conversation_id: int) -> list[dict[str, Any]]:
    """returns all the messages from the conversation with id given."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
        #rows fetches all the messages in the message db connected to the conversation id given
    return [
        {
            "id": int(row["id"]),
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    # fancy short-hand for loop that just returns a list of dictionaries for all the messages in message db connected to the conversation id given


#LOAD RECENT MESSAGES ALMOST THE SAME AS GET RECENT MESSAGES 
def load_recent_messages(conversation_id: int, messageLimit = MESSAGE_LIMIT) -> list[dict[str, Any]]:
    """returns all the messages from the conversation with id given."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM (
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (conversation_id, messageLimit,),
        ).fetchall()
        #rows fetches all the messages in the message db connected to the conversation id given
    return [
        {
            "id": int(row["id"]),
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]

def get_recent_messages(conversation_id: int, number_of_exchanges: int) -> str:
    number_of_messages = number_of_exchanges * 2

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT role, content
            FROM (
                SELECT id, role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (conversation_id, number_of_messages),
        ).fetchall()

    lines = []

    for message in rows:
        lines.append(
            f"{message['role']}: {message['content']}"
        )

    return "\n".join(lines)

def last_message_id(conversation_id=-1) -> int:
    """returns the id of the last message in general or in a specific conversation"""
    if(conversation_id==-1):
        with get_connection() as connection:
                row = connection.execute(
                    """
                    SELECT id
                    FROM messages
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                ).fetchone()
        return row["id"]
    
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (conversation_id,),
        ).fetchone()
        #rows fetches all the messages in the message db connected to the conversation id given
    return row["id"]
    # fancy short-hand for loop that just returns a list of dictionaries for all the messages in message db connected to the conversation id given


def delete_messages(conversation_id: int) -> int:
    """deletes all messages from the conversation with id given"""
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM candidate_sources
            WHERE message_id IN (
                SELECT id
                FROM messages
                WHERE conversation_id = ?
            )
            """,
            (conversation_id,),
        )
        connection.execute(
            """
            DELETE FROM memory_sources
            WHERE message_id IN (
                SELECT id
                FROM messages
                WHERE conversation_id = ?
            )
            """,
            (conversation_id,),
        )
        connection.execute(
            """
            DELETE FROM interaction_events
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )
        connection.execute(
            """
            DELETE FROM memory_extraction_progress
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )
        cursor = connection.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ?
            """,
            #goes through all of messages and deletes all the messages with id
            (conversation_id,),
        )

        return cursor.rowcount

def number_of_messages_in_conversation(conversation_id: int) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS message_count
            FROM messages
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()

    return int(row["message_count"])

def get_companion_state() -> CompanionState:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT trust, closeness, respect, comfort, mood, energy, stress, last_updated_at
            FROM companion_state
            WHERE id = 1
            """
        ).fetchone()

    if row is None:
        raise RuntimeError("The companion state row does not exist.") #should never be called. but this is for safety i guess

    return CompanionState(
        trust=int(row["trust"]),
        closeness=int(row["closeness"]),
        respect=int(row["respect"]),
        comfort=int(row["comfort"]),
        mood=row["mood"],
        energy=int(row["energy"]),
        stress=int(row["stress"]),
        last_updated_at=row["last_updated_at"]
    ) #creates the object, but it will be converted into a model


def save_companion_state(state: CompanionState) -> None:
    cleaned_state = CompanionState(
        trust=clamp(state.trust),
        closeness=clamp(state.closeness),
        respect=clamp(state.respect),
        comfort=clamp(state.comfort),
        mood=validate_mood(state.mood),
        energy=clamp(state.energy),
        stress=clamp(state.stress),
        last_updated_at=state.last_updated_at
    )
    #this is kind of duplicated since the pydantic model already prevents this. but its supposed to be like a second wall of verification i guess

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE companion_state
            SET
                trust = ?,
                closeness = ?,
                respect = ?,
                comfort = ?,
                mood = ?,
                energy = ?,
                stress = ?,
                last_updated_at = ?
            WHERE id = 1
            """,
            (
                cleaned_state.trust,
                cleaned_state.closeness,
                cleaned_state.respect,
                cleaned_state.comfort,
                cleaned_state.mood,
                cleaned_state.energy,
                cleaned_state.stress,
                cleaned_state.last_updated_at
            ),
        )


def store_state_change_request(
    conversation_id: int,
    message_id: int,
    analysis: InteractionAnalysis,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO interaction_events (
                conversation_id,
                message_id,
                event_type,
                importance,
                trust_delta,
                closeness_delta,
                respect_delta,
                comfort_delta,
                suggested_mood,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                message_id,
                analysis.event_type,
                analysis.importance,
                analysis.trust_delta_requested,
                analysis.closeness_delta_requested,
                analysis.respect_delta_requested,
                analysis.comfort_delta_requested,
                analysis.suggested_mood,
                analysis.reason,
            ),
        )

        return int(cursor.lastrowid)


def get_recent_interaction_events(
    conversation_id: int,
    limit: int = 12,
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                conversation_id,
                message_id,
                event_type,
                importance,
                trust_delta,
                closeness_delta,
                respect_delta,
                comfort_delta,
                suggested_mood,
                reason,
                created_at
            FROM interaction_events
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        ).fetchall()

    return [dict(row) for row in rows]


