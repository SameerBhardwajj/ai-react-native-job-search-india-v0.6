import json, re, time
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

from .config import MAX_FETCH_BYTES, MAX_FETCH_REDIRECTS
from .database import get_meta, set_meta, upsert_job, record_source_run
from .ingest import fetch_url
from .security import validate_public_url

SOURCES = [
    {"id":"linkedin","name":"LinkedIn","type":"job-board","enabled":True},
    {"id":"naukri","name":"Naukri","type":"job-board","enabled":True},
    {"id":"indeed","name":"Indeed India","type":"job-board","enabled":True},
    {"id":"foundit","name":"Foundit (Monster)","type":"job-board","enabled":True},
    {"id":"instahyre","name":"Instahyre","type":"job-board","enabled":True},
    {"id":"hirist","name":"Hirist","type":"job-board","enabled":True},
    {"id":"cutshort","name":"Cutshort","type":"job-board","enabled":True},
    {"id":"wellfound","name":"Wellfound","type":"job-board","enabled":True},
    {"id":"company-careers","name":"Company Career Pages","type":"direct","enabled":True},
]

SOURCE_DOMAINS = {
    "linkedin": {"linkedin.com", "www.linkedin.com"},
    "naukri": {"naukri.com", "www.naukri.com"},
    "indeed": {"in.indeed.com", "indeed.com"},
    "foundit": {"foundit.in", "www.foundit.in"},
    "instahyre": {"instahyre.com", "www.instahyre.com"},
    "hirist": {"hirist.tech", "www.hirist.tech"},
    "cutshort": {"cutshort.io", "www.cutshort.io"},
    "wellfound": {"wellfound.com", "www.wellfound.com"},
}


def source_links(keywords, location):
    q, loc = quote_plus(keywords), quote_plus(location)
    return {
        "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}",
        "naukri": f"https://www.naukri.com/{q.replace('+','-')}-jobs-in-{loc.replace('+','-')}",
        "indeed": f"https://in.indeed.com/jobs?q={q}&l={loc}",
        "foundit": f"https://www.foundit.in/srp/results?query={q}&locations={loc}",
        "instahyre": f"https://www.instahyre.com/search-jobs/?q={q}",
        "hirist": f"https://www.hirist.tech/search/{q}",
        "cutshort": f"https://cutshort.io/jobs/search?q={q}&location={loc}",
        "wellfound": f"https://wellfound.com/jobs?query={q}&location={loc}",
        "company-careers": f"https://www.google.com/search?q={q}+jobs+careers+{loc}",
    }


def selected_config():
    ids=json.loads(get_meta("source_selection","[]") or "[]")
    keywords=get_meta("search_keywords","React Native TypeScript") or "React Native TypeScript"
    location=get_meta("search_location","Delhi NCR, India") or "Delhi NCR, India"
    return ids, keywords, location


def save_selection(ids, keywords, location):
    allowed={s["id"] for s in SOURCES}
    ids=[x for x in ids if x in allowed]
    if not ids:
        raise ValueError("Select at least one job source")
    if len(keywords.strip()) < 2 or len(keywords) > 300:
        raise ValueError("Keywords must be between 2 and 300 characters")
    if len(location.strip()) < 2 or len(location) > 200:
        raise ValueError("Location must be between 2 and 200 characters")
    set_meta("source_selection", json.dumps(ids))
    set_meta("search_keywords", keywords.strip())
    set_meta("search_location", location.strip())


def _same_source_domain(sid, url):
    host=(urlparse(url).hostname or "").lower()
    return host in SOURCE_DOMAINS.get(sid, set())


def _safe_get(url, max_redirects=MAX_FETCH_REDIRECTS):
    """Fetch a public page while validating every redirect target to prevent redirect-based SSRF."""
    current=url
    headers={"User-Agent":"RNJobSearch/0.6 (+public-job-search; no-auth; no-bypass)","Accept":"text/html,application/xhtml+xml,application/ld+json"}
    timeout=httpx.Timeout(20.0, connect=8.0)
    with httpx.Client(headers=headers, timeout=timeout, follow_redirects=False) as client:
        for _ in range(max_redirects+1):
            validate_public_url(current)
            r=client.get(current)
            if r.status_code in {301,302,303,307,308}:
                location=r.headers.get("location")
                if not location: raise ValueError("Redirect response missing Location header")
                current=urljoin(current, location)
                continue
            r.raise_for_status()
            ct=r.headers.get("content-type","").lower()
            if "html" not in ct and "xhtml" not in ct:
                raise ValueError("Search page is not HTML")
            if len(r.content)>MAX_FETCH_BYTES:
                raise ValueError(f"Response exceeds {MAX_FETCH_BYTES} bytes")
            return current, r.text
    raise ValueError("Too many redirects")


def _clean_text(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _jsonld_jobs(soup):
    jobs=[]
    for tag in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        raw=tag.string or tag.get_text()
        try: data=json.loads(raw)
        except Exception: continue
        stack=data if isinstance(data,list) else [data]
        while stack:
            x=stack.pop()
            if isinstance(x,dict) and "@graph" in x and isinstance(x["@graph"],list): stack.extend(x["@graph"])
            elif isinstance(x,list): stack.extend(x)
            elif isinstance(x,dict):
                typ=x.get("@type")
                types=typ if isinstance(typ,list) else [typ]
                if any(str(t).lower()=="jobposting" for t in types): jobs.append(x)
    return jobs


def _job_from_jsonld(x, sid, page_url):
    org=x.get("hiringOrganization") or {}
    loc=x.get("jobLocation") or x.get("jobLocationType") or ""
    if isinstance(loc,list): loc=loc[0] if loc else ""
    if isinstance(loc,dict):
        addr=loc.get("address") or {}
        if isinstance(addr,dict):
            loc=", ".join(str(v) for v in [addr.get("addressLocality"),addr.get("addressRegion"),addr.get("addressCountry")] if v)
        else: loc=str(addr)
    salary=x.get("baseSalary") or {}
    desc=BeautifulSoup(str(x.get("description") or ""),"html.parser").get_text(" ",strip=True)
    return {
        "source":sid,
        "source_id":str(x.get("identifier") or x.get("url") or ""),
        "company":_clean_text(org.get("name") if isinstance(org,dict) else str(org)) or "Unknown",
        "role":_clean_text(x.get("title") or "Unknown"),
        "location":_clean_text(str(loc)) or "India / check listing",
        "url":str(x.get("url") or page_url),
        "description":desc,
        "posted_at":x.get("datePosted"),
        "salary_raw":salary,
    }


def _anchor_candidates(html, base_url, sid, limit=30):
    soup=BeautifulSoup(html,"html.parser")
    out=[]; seen=set()
    for a in soup.find_all("a", href=True):
        href=urljoin(base_url,a.get("href","").strip())
        text=_clean_text(a.get_text(" ",strip=True))
        if not href or not text or len(text)<8 or href in seen: continue
        if not href.startswith(("http://","https://")): continue
        if sid != "company-careers" and not _same_source_domain(sid,href): continue
        low=(href+" "+text).lower()
        if any(k in low for k in ("/job","/jobs/","job-") ):
            seen.add(href); out.append((href,text[:200]))
        if len(out)>=limit: break
    return out


def _extract_candidates(sid, html, final_url):
    soup=BeautifulSoup(html,"html.parser")
    structured=[_job_from_jsonld(x,sid,final_url) for x in _jsonld_jobs(soup)]
    # Structured data is preferred; anchor extraction is a fallback for boards that don't expose JSON-LD.
    if structured:
        return structured[:30]
    return [{"source":sid,"url":u,"role":a,"company":"Unknown","location":"India / check listing","description":""}
            for u,a in _anchor_candidates(html,final_url,sid)]


def refresh_selected():
    ids, keywords, location = selected_config()
    if not ids: return {"status":"no_sources","sources":{},"jobs_added":0}
    links=source_links(keywords,location)
    started=datetime.now(timezone.utc).isoformat()
    result={"started_at":started,"finished_at":None,"keywords":keywords,"location":location,"sources":{},"jobs_added":0,"skipped":0}
    for sid in ids:
        url=links.get(sid)
        item={"url":url,"status":"not_checked","jobs_found":0,"jobs_new":0,"error":""}
        t0=time.monotonic()
        try:
            final_url, html=_safe_get(url)
            candidates=_extract_candidates(sid,html,final_url)
            added=0
            for raw in candidates[:30]:
                try:
                    if not raw.get("url"): continue
                    # For detail pages, only fetch same-source URLs. Google discovery is allowed to resolve company pages,
                    # but candidate links are still validated as public URLs before fetch.
                    if sid != "company-careers" and not _same_source_domain(sid,raw["url"]): continue
                    if not raw.get("description") or raw.get("company")=="Unknown":
                        detail=fetch_url(raw["url"], source=sid)
                        detail.update({k:v for k,v in raw.items() if v and k not in {"description","company","role"}})
                        raw=detail
                    else:
                        raw["integrity"]={"safe":True,"prompt_injection_hits":[],"hidden_unicode":[]}
                    before=get_meta(f"source_seen:{sid}:{raw.get('url','')}")
                    job=upsert_job(raw)
                    if not before: added+=1
                    set_meta(f"source_seen:{sid}:{raw.get('url','')}",job["last_seen_at"])
                except Exception:
                    continue
            item.update(status="ok",jobs_found=len(candidates),jobs_new=added)
            result["jobs_added"]+=added
        except Exception as e:
            item.update(status="blocked_or_unavailable",error=str(e)[:300])
        item["duration_ms"]=round((time.monotonic()-t0)*1000)
        result["sources"][sid]=item
        record_source_run(sid,item)
    result["finished_at"]=datetime.now(timezone.utc).isoformat()
    set_meta("last_refresh",json.dumps(result,ensure_ascii=False))
    return result