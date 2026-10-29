import os,time,json
from pathlib import Path
from datetime import datetime,timezone
from .database import init_db,set_meta
from .sources import refresh_selected
from .config import ROOT

LOCK=ROOT/".refresh.lock"

def acquire_lock(max_age=50*60):
    now=time.time()
    try:
        if LOCK.exists() and now-LOCK.stat().st_mtime<max_age:
            return False
        LOCK.write_text(json.dumps({"pid":os.getpid(),"started_at":datetime.now(timezone.utc).isoformat()}),encoding="utf-8")
        return True
    except OSError:
        return False

def release_lock():
    try: LOCK.unlink(missing_ok=True)
    except OSError: pass

if __name__=='__main__':
    init_db()
    if not acquire_lock():
        print("Another refresh is already running; exiting safely.")
        raise SystemExit(0)
    try:
        result=refresh_selected()
        set_meta("scheduler_last_run",json.dumps(result,ensure_ascii=False))
        print(json.dumps(result,ensure_ascii=False))
    finally:
        release_lock()