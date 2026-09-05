# AI Companion

A local AI companion project built with Python, FastAPI, SQLite, and Ollama. Chat with Rin through a browser while the app tracks conversation history and changes to her emotional and relationship state.

## Features

- Browser chat interface with adjustable temperature and response timing.
- Local SQLite storage for conversations, companion state, and interaction events.
- Interaction analysis that updates Rin's state before she responds.
- Emotional decay and character guidance based on the current state.
- Memory candidate extraction with developer controls to accept or reject candidates.
- Developer tools for viewing and editing state, inspecting prompts, and reviewing interaction events.

## Setup

Install Python 3.10 or newer and Ollama, then run these commands from the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull gemma3:12b
ollama pull gemma3:4b
```

Make sure Ollama is running, then start the application:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 to chat. Interactive API documentation is available at http://127.0.0.1:8000/docs.

The app creates `data/companion.db` on startup. Local databases and chat history are excluded from Git.

## Project structure

| Path | Description |
| --- | --- |
| `app/main.py` | FastAPI routes and chat workflow. |
| `app/llm.py` | Sends conversation context to Ollama. |
| `app/database.py` | SQLite storage and queries. |
| `app/state*.py` | Companion state, state changes, decay, and prompt guidance. |
| `app/interactionanalyzer.py` | Classifies incoming interactions. |
| `app/memory*.py` | Memory types and candidate extraction. |
| `app/promptbuilder.py` | Combines the character prompt with current state guidance. |
| `app/static/` | HTML, CSS, and JavaScript for the browser interface. |
| `app/config.py` | Model names, generation settings, and state defaults. |
| `characters/rin.md` | Rin's character definition. |
| `notes/` | Development journal and learning notes. |
| `main1.py`, `config1.py`, `test/` | Early experiments and learning examples. |

## Status

An ongoing personal learning project intended for local use. Model names and defaults can be changed in `app/config.py`. Memory extraction and review are implemented; accepted memories are not currently included in the chat system prompt.
