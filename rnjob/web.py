from fastapi import FastAPI, Header, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path
import json, re
from urllib.parse import quote_plus
from .sources import SOURCES, source_links, save_selection, selected_config, refresh_selected

from .config import WEB_TOKEN, OUTPUT_DIR
from .database import init_db, all_jobs, applications, stats, get_job, upsert_job, create_application, update_status, events, get_meta, set_meta, source_runs
from .profile import load_profile, save_profile
from .matcher import rank_jobs, score_job
from .security import validate_public_url, integrity_flags
from .ats import analyze_resume
from .resume_parser import import_resume

BASE = Path(__file__).resolve().parent
DASH = BASE / "dashboard"
MAX_RESUME_BYTES = 5 * 1024 * 1024
app = FastAPI(title="AI React Native Job Search India", version="0.6.3")

class JobCreate(BaseModel):
    company: str
    role: str
    location: str = ""
    url: str = ""
    description: str = ""
    source: str = "manual"
    posted_at: str | None = None

class ApplicationUpdate(BaseModel):
    status: str
    notes: str = ""

class SourceSelection(BaseModel):
    selected: list[str]

class ATSRequest(BaseModel):
    job_id: int
    resume_text: str | None = None

class AIRequest(BaseModel):
    job_id: int
    kind: str

@app.on_event("startup")
def start():
    init_db()

def auth(x_token: str | None = None):
    if WEB_TOKEN and x_token != WEB_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def mutation_guard(request: Request):
    origin=request.headers.get("origin")
    if origin and origin not in {"http://127.0.0.1:8000","http://localhost:8000"}:
        raise HTTPException(status_code=403, detail="Cross-origin mutation blocked")

def job_view(j, profile):
    m = score_job(j, profile)
    return {"id":j["id"],"company":j["company"],"role":j["role"],"location":j["location"],"url":j["url"],
            "source":j.get("source","manual"),"posted_at":j.get("posted_at"),"first_seen_at":j.get("first_seen_at"),
            "score":m["score"],"decision":m["decision"],"reasons":m["reasons"],"gaps":m["gaps"],
            "hard_failures":m["hard_failures"],"breakdown":m["breakdown"],"salary_range":m["salary_range"],
            "required_experience":m["required_experience"],"required_notice_days":m["required_notice_days"],
            "description":j.get("description","")}

@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(DASH / "index.html")

@app.get("/dashboard.css")
def css(): return FileResponse(DASH / "dashboard.css", media_type="text/css")

@app.get("/dashboard.js")
def js(): return FileResponse(DASH / "dashboard.js", media_type="application/javascript")

@app.get("/api/profile")
def profile(x_token: str | None = Header(default=None)):
    auth(x_token); return load_profile()

@app.get("/api/sources")
def sources(x_token: str | None = Header(default=None)):
    auth(x_token); return {"sources": SOURCES}

@app.get("/api/source-search-links")
def source_search_links(keywords: str, location: str = "India", x_token: str | None = Header(default=None)):
    auth(x_token)
    templates=source_links(keywords,location)
    return {"links": [{"id":s["id"],"name":s["name"],"url":templates[s["id"]]} for s in SOURCES if s["id"] in templates]}

@app.get("/api/source-selection")
def source_selection(x_token: str | None = Header(default=None)):
    auth(x_token); ids,keywords,location=selected_config(); return {"selected":ids,"keywords":keywords,"location":location,"last_refresh":json.loads(get_meta("last_refresh","null") or "null")}

@app.post("/api/source-selection")
def save_source_selection(body: SourceSelection, request: Request, keywords: str = "React Native TypeScript", location: str = "Delhi NCR, India", x_token: str | None = Header(default=None)):
    auth(x_token); mutation_guard(request)
    allowed={s["id"] for s in SOURCES}
    ids=[x for x in body.selected if x in allowed]
    try:
        save_selection(ids,keywords.strip() or "React Native TypeScript",location.strip() or "India")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok":True,"selected":ids,"keywords":keywords,"location":location}

@app.post("/api/source-refresh")
def source_refresh(request: Request, x_token: str | None = Header(default=None)):
    auth(x_token); mutation_guard(request); return refresh_selected()

@app.get("/api/jobs")
def jobs(limit:int=100, min_score:float=0, decision:str|None=None, source:str|None=None,
         q:str|None=None, x_token:str|None=Header(default=None)):
    auth(x_token)
    p=load_profile(); rows=rank_jobs(all_jobs(),p,min_score=min_score,include_rejected=True)
    if decision: rows=[j for j in rows if j["match"]["decision"]==decision]
    if source: rows=[j for j in rows if j.get("source")==source]
    if q:
        q=q.lower(); rows=[j for j in rows if q in (j.get("company","")+" "+j.get("role","")+" "+j.get("location","")+" "+j.get("description","")).lower()]
    return [job_view(j,p) for j in rows[:max(1,min(limit,500))]]

@app.get("/api/jobs/{job_id}")
def job(job_id:int,x_token:str|None=Header(default=None)):
    auth(x_token); j=get_job(job_id)
    if not j: raise HTTPException(404,"Job not found")
    return job_view(j,load_profile())

@app.post("/api/jobs")
def add_job(body:JobCreate,request: Request,x_token:str|None=Header(default=None)):
    auth(x_token); mutation_guard(request)
    data=body.model_dump()
    if data.get("url"):
        try: validate_public_url(data["url"])
        except ValueError as e: raise HTTPException(status_code=400,detail=str(e))
    data["integrity"]=integrity_flags(data.get("description", ""))
    return upsert_job(data)

@app.get("/api/applications")
def apps(x_token:str|None=Header(default=None)):
    auth(x_token); return applications()

@app.post("/api/applications/{job_id}")
def set_app(job_id:int,body:ApplicationUpdate,request: Request,x_token:str|None=Header(default=None)):
    auth(x_token); mutation_guard(request)
    if not get_job(job_id): raise HTTPException(404,"Job not found")
    update_status(job_id,body.status,body.notes)
    return {"ok":True}

@app.get("/api/applications/{job_id}/events")
def app_events(job_id:int,x_token:str|None=Header(default=None)):
    auth(x_token); return events(job_id)

@app.get("/api/analytics")
def analytics(x_token:str|None=Header(default=None)):
    auth(x_token); p=load_profile(); rows=rank_jobs(all_jobs(),p,include_rejected=True); apps_rows=applications()
    decisions={k:sum(1 for j in rows if j["match"]["decision"]==k) for k in ["APPLY","MAYBE","DON'T APPLY"]}
    sources={}
    for j in rows: sources[j.get("source","manual")]=sources.get(j.get("source","manual"),0)+1
    return {**stats(),"profile":p,"decisions":decisions,"sources":sources,
            "avg_match":round(sum(j["match"]["score"] for j in rows)/len(rows),1) if rows else 0,
            "jobs":len(rows),"recent_applications":apps_rows[:8]}

@app.get("/api/dashboard")
def dashboard(x_token:str|None=Header(default=None)):
    return analytics(x_token)

@app.get("/api/source-runs")
def source_run_history(limit:int=30,x_token: str | None = Header(default=None)):
    auth(x_token); return source_runs(limit)

@app.get("/api/ai/status")
def ai_status(x_token: str | None = Header(default=None)):
    auth(x_token)
    from .ai import available
    from .config import AI_PROVIDER, OPENAI_MODEL, GEMINI_MODEL
    return {"configured":available(),"provider":AI_PROVIDER or None,"model":OPENAI_MODEL if AI_PROVIDER=="openai" else GEMINI_MODEL if AI_PROVIDER=="gemini" else None,
            "pii_allowed":__import__("rnjob.config",fromlist=["AI_ALLOW_PII"]).AI_ALLOW_PII,
            "message":"AI provider configured." if available() else "AI is not configured. Add AI_PROVIDER and the matching API key to your private .env file, then restart the dashboard."}

@app.post("/api/resume/ats")
def resume_ats(body: ATSRequest, request: Request, x_token: str | None = Header(default=None)):
    auth(x_token); mutation_guard(request)
    j=get_job(body.job_id)
    if not j: raise HTTPException(404,"Job not found")
    p=load_profile(); text=(body.resume_text if body.resume_text is not None else p.get("resume_text","")).strip()
    if not text: raise HTTPException(400,"Upload or import a resume first, or paste your resume text.")
    from .ats import analyze_resume
    return {"job_id":body.job_id,"job":j.get("role",""),"company":j.get("company",""),"analysis":analyze_resume(text,j),"resume_characters":len(text)}

@app.post("/api/resume/upload")
async def resume_upload(request: Request, file: UploadFile = File(...), x_token: str | None = Header(default=None)):
    auth(x_token); mutation_guard(request)
    name=(file.filename or "resume").lower()
    ext=Path(name).suffix
    if ext not in {".pdf",".docx",".txt"}:
        raise HTTPException(400,"Supported resume formats: PDF, DOCX and TXT.")
    raw=await file.read(MAX_RESUME_BYTES+1)
    await file.close()
    if len(raw)>MAX_RESUME_BYTES: raise HTTPException(413,"Resume must be 5 MB or smaller.")
    text=""
    try:
        if ext==".pdf":
            import io
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(raw))
            text="\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext==".docx":
            import io
            from docx import Document
            doc=Document(io.BytesIO(raw))
            text="\n".join(p.text for p in doc.paragraphs)
            for table in doc.tables:
                text += "\n" + "\n".join(" | ".join(c.text for c in row.cells) for row in table.rows)
        else:
            text=raw.decode("utf-8-sig")
    except Exception as e:
        raise HTTPException(400,f"Could not read resume: {str(e)[:180]}")
    text=text.strip()
    if len(text)<30: raise HTTPException(400,"No readable resume text found. For scanned PDFs, paste the text manually.")
    p=load_profile(); p["resume_text"]=text
    imported=import_resume_text(text)
    for k in ("experience_years",):
        if imported.get(k) and not p.get(k): p[k]=imported[k]
    current=p.get("skills",{}); extracted=imported.get("skills",{})
    current["core"]=list(dict.fromkeys(current.get("core",[])+extracted.get("core",[])))
    current["secondary"]=list(dict.fromkeys(current.get("secondary",[])+extracted.get("secondary",[])))
    p["skills"]=current; save_profile(p)
    return {"ok":True,"filename":Path(file.filename or "resume").name,"characters":len(text),"sections_detected":imported.get("sections_detected",[]),"skills_detected":current["core"],"experience_years":p.get("experience_years"),"message":"Resume text imported into your local profile."}

def import_resume_text(text):
    from .profile import extract_profile_from_text
    return extract_profile_from_text(text)

@app.post("/api/ai/generate")
def generate_ai(body: AIRequest, request: Request, x_token: str | None = Header(default=None)):
    auth(x_token); mutation_guard(request)
    from .ai import available, tailored_resume, cover_letter, interview_pack, skill_gap, fact_check
    if body.kind not in {"tailor","cover","interview","gap"}: raise HTTPException(400,"Unknown AI action.")
    if not available(): raise HTTPException(503,"AI is not configured. Add AI_PROVIDER and the matching API key to your private .env file, then restart the dashboard.")
    p=load_profile(); j=get_job(body.job_id)
    if not j: raise HTTPException(404,"Job not found")
    if not p.get("resume_text","").strip(): raise HTTPException(400,"Import your master resume first from Resume & ATS.")
    generators={"tailor":tailored_resume,"cover":cover_letter,"interview":interview_pack,"gap":skill_gap}
    try: output=generators[body.kind](p,j)
    except Exception as e: raise HTTPException(502,f"AI generation failed: {str(e)[:240]}")
    check=fact_check(output,p)
    folder={"tailor":"resumes","cover":"cover_letters","interview":"interviews","gap":"interviews"}[body.kind]
    path=OUTPUT_DIR/folder/f"{body.kind}_{body.job_id}.json"; path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({"output":output,"fact_check":check,"job_id":body.job_id,"kind":body.kind},indent=2,ensure_ascii=False),encoding="utf-8")
    result={"ok":True,"kind":body.kind,"job_id":body.job_id,"job":j.get("role"),"company":j.get("company"),"output":output,"fact_check":check,"file":str(path)}
    if body.kind=="tailor":
        from .artifacts import export_docx, export_pdf
        safe_id=body.job_id
        result["exports"]={"docx":str(export_docx(output,f"tailored_resume_{safe_id}.docx")) if check["passed"] else None,
                           "pdf":str(export_pdf(output,f"tailored_resume_{safe_id}.pdf")) if check["passed"] else None}
    return result

@app.get("/api/health")
def health():
    return {"ok":True,"version":"0.6.3","db":"ready"}