# stores all the constants, routes, etc

from pathlib import Path # so this is a python package that treats paths as objects instead of string

BASE_DIR = Path(__file__).resolve().parent.parent #finds the directory: ai companion using this file's parents's parent
DATA_DIR = BASE_DIR / "data" # finds the data directory
DATABASE_PATH = DATA_DIR / "companion.db" # finds the database file for the campanion

CHARACTERS_DIR = BASE_DIR / "characters"
RIN_CHARACTER_PATH = CHARACTERS_DIR / "rin.md"

MODEL_NAME = "gemma3:12b"
SMALL_MODEL = "gemma3:4b"

MESSAGE_LIMIT = 100
MEMORY_EXTRACTION_INTERVAL = 8
MEMORY_EXTRACTION_IDLE_SECONDS = 10
MEMORY_EXTRACTION_FORCE_BACKLOG = 24

MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TEMPERATURE_STEP = 0.01
DEFAULT_TOP_K = 50
DEFAULT_TOP_P = 0.95
DEFAULT_REPEAT_PENALTY = 1.1
DEFAULT_NUM_PREDICT = 80
NUMBER_OF_EXCHANGE = 6

DEFAULT_TRUST = 35
DEFAULT_CLOSENESS = 20
DEFAULT_RESPECT = 50
DEFAULT_COMFORT = 25
DEFAULT_MOOD = "neutral"
DEFAULT_ENERGY = 70
DEFAULT_STRESS = 15
ENERGY_DECAY_RATE = 0.2
STRESS_DECAY_RATE = 0.3 #temporary