import csv,json
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
from .security import integrity_flags,validate_public_url
from .database import upsert_job
from .config import MAX_FETCH_BYTES,MAX_FETCH_REDIRECTS

def load_json(p):
    d=json.loads(Path(p).read_text(encoding="utf-8"));return d if isinstance(d,list) else [d]
def load_csv(p):
    with open(p,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def normalize(j):
    d=str(j.get("description") or j.get("requirements") or "");flags=integrity_flags(d)
    return {"source":str(j.get("source") or "manual"),"source_id":str(j.get("source_id") or ""),"company":str(j.get("company") or "Unknown"),"role":str(j.get("role") or j.get("title") or "Unknown"),"location":str(j.get("location") or "India"),"url":str(j.get("url") or ""),"description":d[:50000],"posted_at":j.get("posted_at"),"integrity":flags}
def import_jobs(jobs):return [upsert_job(normalize(j)) for j in jobs]

def fetch_url(url, source="url"):
    validate_public_url(url)
    current=url
    headers={"User-Agent":"RNJobSearch/0.6 (+public-job-search; no-auth; no-bypass)","Accept":"text/html,application/xhtml+xml,application/ld+json"}
    timeout=httpx.Timeout(20.0, connect=8.0)
    with httpx.Client(headers=headers,timeout=timeout,follow_redirects=False) as client:
        for _ in range(MAX_FETCH_REDIRECTS+1):
            validate_public_url(current)
            with client.stream("GET",current) as r:
                if r.status_code in {301,302,303,307,308}:
                    location=r.headers.get("location")
                    if not location: raise ValueError("Redirect missing Location")
                    from urllib.parse import urljoin
                    current=urljoin(current,location); continue
                r.raise_for_status();ct=r.headers.get("content-type","").lower()
                if "text/html" not in ct and "application/xhtml+xml" not in ct:raise ValueError("URL is not an HTML page")
                data=b""
                for chunk in r.iter_bytes():
                    data+=chunk
                    if len(data)>MAX_FETCH_BYTES:raise ValueError(f"Response exceeds {MAX_FETCH_BYTES} bytes")
                break
        else: raise ValueError("Too many redirects")
    s=BeautifulSoup(data,"html.parser")
    for tag in s(["script","style","noscript","svg"]):tag.decompose()
    title=s.title.get_text(" ",strip=True) if s.title else "Job"
    text=s.get_text(" ",strip=True)
    return normalize({"source":source,"role":title,"location":"India / check listing","url":current,"description":text})