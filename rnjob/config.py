import os
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parent.parent
load_dotenv(ROOT/".env")
DB_PATH=os.getenv("DB_PATH",str(ROOT/"jobsearch.db"))
PROFILE_PATH=ROOT/"profile"/"profile.json"
OUTPUT_DIR=ROOT/"output"
AI_PROVIDER=os.getenv("AI_PROVIDER","").lower().strip()
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY","")
OPENAI_MODEL=os.getenv("OPENAI_MODEL","gpt-5")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
AI_ALLOW_PII=os.getenv("AI_ALLOW_PII","false").lower() in {"1","true","yes"}
WEB_HOST=os.getenv("WEB_HOST","127.0.0.1")
WEB_PORT=int(os.getenv("WEB_PORT","8000"))
WEB_TOKEN=os.getenv("WEB_TOKEN","")
MAX_FETCH_BYTES=int(os.getenv("MAX_FETCH_BYTES","2000000"))
MAX_FETCH_REDIRECTS=int(os.getenv("MAX_FETCH_REDIRECTS","3"))
JOB_FRESH_DAYS=int(os.getenv("JOB_FRESH_DAYS","30"))