#this file communicates with the llm directly after receiving the prompt
#it builds the final prompt and returns the response from the llm


import time
from typing import Any #typing means many types of variable. not typing on keyboard
from ollama import chat

from app.config import (
    DEFAULT_NUM_PREDICT,
    DEFAULT_REPEAT_PENALTY,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    MODEL_NAME,
)
#config should have all the default values, so not everything is hardcoded in as numerical values
from app.state import CompanionState
from app.promptbuilder import build_system_prompt


#this is like the backend stuff that directly talks to the llm to get an output

def build_messages(conversation_messages: list[dict[str, Any]], state: CompanionState) -> list[dict[str, str]]:
    """create the prompt to be given to the llm"""
    # list[dict[str, Any] means getting a list of dictionaries composed of string keys and Any values (string or integer or other)
    #gets the numerical values of the states
    system_prompt = build_system_prompt(state)
    #converts the numerical values into words that can be interpreted by the llm and adds the original character card

    messages = [
        {"role": "system", "content": system_prompt},
    ]
    #creates the first message in the list to be sent to the llm: the system prompt

    for message in conversation_messages:
        role = message["role"]
        if role not in {"user", "assistant"}:
            continue
        #temporarily skip anything that isnt user or llm

        messages.append(
            {
                "role": role,
                "content": message["content"],
            }
        )

    return messages


def get_assistant_response(
    conversation_messages: list[dict[str, Any]],
    temperature: float,
    state: CompanionState
) -> tuple[str, float]:
    """returns the llm message from the backend after giving it the prompt"""
    messages = build_messages(conversation_messages, state)
    #builds the final prompt to be sent

    start_time = time.perf_counter()

    response = chat(
        model=MODEL_NAME,
        messages=messages,
        options={
            "temperature": temperature,
            "top_k": DEFAULT_TOP_K,
            "top_p": DEFAULT_TOP_P,
            "repeat_penalty": DEFAULT_REPEAT_PENALTY,
            "num_predict": DEFAULT_NUM_PREDICT,
        },
        think=False,
    )

    elapsed_time = time.perf_counter() - start_time

    return response.message.content, elapsed_time


