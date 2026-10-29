import sqlite3,hashlib,json
from datetime import datetime,timezone
from .config import DB_PATH
STATUSES={"SAVED","REVIEW","READY","APPLIED","SCREENING","INTERVIEW","OFFER","REJECTED","WITHDRAWN"}
SCHEMA="""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,fingerprint TEXT UNIQUE,source TEXT DEFAULT 'manual',source_id TEXT DEFAULT '',company TEXT,role TEXT,location TEXT,url TEXT,description TEXT,posted_at TEXT,first_seen_at TEXT,last_seen_at TEXT,raw_json TEXT,integrity_json TEXT);
CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER UNIQUE,status TEXT DEFAULT 'SAVED',notes TEXT DEFAULT '',recruiter TEXT DEFAULT '',resume_version TEXT DEFAULT '',cover_version TEXT DEFAULT '',applied_at TEXT,updated_at TEXT,FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS application_events(id INTEGER PRIMARY KEY AUTOINCREMENT,application_id INTEGER,event TEXT,notes TEXT,created_at TEXT,FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS source_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,source TEXT NOT NULL,status TEXT,started_at TEXT,finished_at TEXT,jobs_found INTEGER DEFAULT 0,jobs_new INTEGER DEFAULT 0,error TEXT DEFAULT '',duration_ms INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
"""
def now():return datetime.now(timezone.utc).isoformat()
def conn():
    c=sqlite3.connect(DB_PATH,timeout=15);c.row_factory=sqlite3.Row;c.execute("PRAGMA foreign_keys=ON");c.execute("PRAGMA busy_timeout=15000");return c
def get_meta(key, default=None):
    with conn() as c:r=c.execute("SELECT value FROM meta WHERE key=?",(key,)).fetchone()
    return r[0] if r else default
def set_meta(key,value):
    with conn() as c:c.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))
def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        c.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('schema_version','3')")
        c.execute("UPDATE meta SET value='3' WHERE key='schema_version'")
def fingerprint(j):
    url=(j.get("url") or "").strip().lower()
    if url: key=url.split("#",1)[0].rstrip("/")
    else: key="|".join(str(j.get(k,"")).strip().lower() for k in ["company","role","location"])
    return hashlib.sha256(key.encode()).hexdigest()
def upsert_job(j):
    fp=fingerprint(j); stamp=now()
    integrity=j.get("integrity",{})
    with conn() as c:
        existing=c.execute("SELECT id,first_seen_at FROM jobs WHERE fingerprint=?",(fp,)).fetchone()
        if existing:
            c.execute("""UPDATE jobs SET source=?,source_id=?,company=?,role=?,location=?,url=?,description=?,posted_at=COALESCE(?,posted_at),last_seen_at=?,raw_json=?,integrity_json=? WHERE fingerprint=?""",
                      (j.get("source","manual"),j.get("source_id",""),j.get("company",""),j.get("role",""),j.get("location",""),j.get("url",""),j.get("description",""),j.get("posted_at"),stamp,json.dumps(j,ensure_ascii=False),json.dumps(integrity,ensure_ascii=False),fp))
        else:
            c.execute("INSERT INTO jobs(fingerprint,source,source_id,company,role,location,url,description,posted_at,first_seen_at,last_seen_at,raw_json,integrity_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (fp,j.get("source","manual"),j.get("source_id",""),j.get("company",""),j.get("role",""),j.get("location",""),j.get("url",""),j.get("description",""),j.get("posted_at"),stamp,stamp,json.dumps(j,ensure_ascii=False),json.dumps(integrity,ensure_ascii=False)))
        r=c.execute("SELECT * FROM jobs WHERE fingerprint=?",(fp,)).fetchone()
    return dict(r)
def all_jobs():
    with conn() as c:return [dict(r) for r in c.execute("SELECT * FROM jobs ORDER BY id DESC")]
def get_job(i):
    with conn() as c:r=c.execute("SELECT * FROM jobs WHERE id=?",(i,)).fetchone()
    return dict(r) if r else None
def create_application(i,status="SAVED",resume_version="",cover_version="",notes=""):
    if not get_job(i):raise ValueError("Job not found")
    if status not in STATUSES:raise ValueError(f"Invalid status: {status}")
    stamp=now()
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO applications(job_id,status,notes,resume_version,cover_version,updated_at) VALUES(?,?,?,?,?,?)",(i,status,notes,resume_version,cover_version,stamp));a=c.execute("SELECT * FROM applications WHERE job_id=?",(i,)).fetchone();c.execute("INSERT INTO application_events(application_id,event,notes,created_at) VALUES(?,?,?,?)",(a["id"],status,notes,stamp))
def update_status(i,status,notes=""):
    status=status.upper()
    if status not in STATUSES:raise ValueError(f"Invalid status. Use: {', '.join(sorted(STATUSES))}")
    stamp=now()
    with conn() as c:
        a=c.execute("SELECT * FROM applications WHERE job_id=?",(i,)).fetchone()
        if not a:
            if not c.execute("SELECT id FROM jobs WHERE id=?",(i,)).fetchone(): raise ValueError("Job not found")
            c.execute("INSERT INTO applications(job_id,status,notes,updated_at) VALUES(?,?,?,?)",(i,status,notes,stamp));a=c.execute("SELECT * FROM applications WHERE job_id=?",(i,)).fetchone()
        applied=stamp if status=="APPLIED" and not a["applied_at"] else a["applied_at"]
        c.execute("UPDATE applications SET status=?,notes=?,updated_at=?,applied_at=? WHERE job_id=?",(status,notes,stamp,applied,i));c.execute("INSERT INTO application_events(application_id,event,notes,created_at) VALUES(?,?,?,?)",(a["id"],status,notes,stamp))
def applications():
    with conn() as c:return [dict(r) for r in c.execute("SELECT a.*,j.company,j.role,j.location,j.url FROM applications a JOIN jobs j ON j.id=a.job_id ORDER BY a.updated_at DESC")]
def stats():
    with conn() as c:
        total=c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0];apps=c.execute("SELECT COUNT(*) FROM applications").fetchone()[0];rows=c.execute("SELECT status,COUNT(*) n FROM applications GROUP BY status").fetchall()
    return {"jobs":total,"applications":apps,"pipeline":{r["status"]:r["n"] for r in rows}}
def events(job_id):
    with conn() as c:return [dict(r) for r in c.execute("SELECT e.* FROM application_events e JOIN applications a ON a.id=e.application_id WHERE a.job_id=? ORDER BY e.created_at",(job_id,))]
def record_source_run(source,item):
    with conn() as c:c.execute("INSERT INTO source_runs(source,status,started_at,finished_at,jobs_found,jobs_new,error,duration_ms) VALUES(?,?,?,?,?,?,?,?)",(source,item.get("status"),item.get("started_at") or now(),now(),item.get("jobs_found",0),item.get("jobs_new",0),item.get("error","") or "",item.get("duration_ms",0)))
def source_runs(limit=50):
    with conn() as c:return [dict(r) for r in c.execute("SELECT * FROM source_runs ORDER BY id DESC LIMIT ?",(max(1,min(limit,500)),))]