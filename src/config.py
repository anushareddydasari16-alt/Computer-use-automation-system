# Loads project settings from the local .env file.

import os

from dotenv import load_dotenv


load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

TARGET_URL = os.getenv(
    "TARGET_URL",
    "http://127.0.0.1:8000"
)

MAX_STEPS = int(
    os.getenv("MAX_STEPS", "15")
)

RUN_TIMEOUT_SECONDS = int(
    os.getenv("RUN_TIMEOUT_SECONDS", "120")
)

HEADLESS = os.getenv(
    "HEADLESS",
    "false"
).lower() == "true"