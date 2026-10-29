import re
from datetime import datetime,timezone
WEIGHTS={"rn":30,"react":7,"js":7,"ts":9,"state":5,"navigation":4,"animation":4,"testing":5,"platform":6,"cicd":4,"performance":4,"architecture":5,"title":4,"salary":3,"location":2,"notice":1}
CHECKS={"rn":["react native","reactnative"],"react":["react","react.js","reactjs"],"js":["javascript","ecmascript"],"ts":["typescript"],"state":["redux","mobx","zustand"],"navigation":["react navigation","navigation"],"animation":["reanimated","gesture handler","animation"],"testing":["jest","testing library","unit testing"],"platform":["android","ios"],"cicd":["ci/cd","continuous integration","github actions","azure devops"],"performance":["performance optimization","profiling","performance"],"architecture":["architecture","system design","native modules"]}
def blob(j): return " ".join(str(j.get(k,"")) for k in ["role","description","requirements","location"])
def has(t,terms): return any(re.search(r"(?<!\w)"+re.escape(x.lower())+r"(?!\w)",t.lower()) for x in terms)
def years(t):
    vals=[float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",t,re.I)]
    return max(vals,default=0)
def salary(t):
    s=t.lower().replace(",","")
    vals=[]
    for a,b in re.findall(r"(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:-|to)\s*(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?)",s): vals.append((float(a),float(b)))
    if vals:return min(x[0] for x in vals),max(x[1] for x in vals)
    one=[float(x) for x in re.findall(r"(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lacs?)",s)]
    return (min(one),max(one)) if one else (None,None)
def parse_notice(t):
    m=re.search(r"(\d+)\s*(?:days?|day)\s*(?:notice|notice period)",t,re.I)
    if m:return int(m.group(1))
    if re.search(r"immediate(?:ly)?\s*(?:joiner|joining)?",t,re.I): return 0
    return None
def title_fit(role):
    r=role.lower(); good=["react native","mobile engineer","mobile developer","react native engineer","frontend engineer"]
    return any(x in r for x in good)
def location_fit(loc,p):
    loc=loc.lower(); prefs=[str(x).lower() for x in p.get("locations",[])]; remote=p.get("preferences",{}).get("remote_ok",True)
    if "remote" in loc and remote:return True
    aliases={"gurugram":["gurgaon","gurugram"],"delhi ncr":["delhi","gurgaon","gurugram","noida","ghaziabad","ncr"]}
    for x in prefs:
        if x in loc:return True
        for a in aliases.get(x,[]):
            if a in loc:return True
    return not prefs
def score_job(j,p):
    t=blob(j); b={}; reasons=[]; gaps=[]
    for k,terms in CHECKS.items(): b[k]=WEIGHTS[k] if has(t,terms) else 0
    role=str(j.get("role","")); b["title"]=WEIGHTS["title"] if title_fit(role) else 0
    if b["rn"]: reasons.append("React Native role relevance")
    else:gaps.append("React Native is not clearly required")
    req=years(t); exp=float(p.get("experience_years") or 0); seniority_ok=(not req or exp>=req)
    if req and seniority_ok: reasons.append(f"Experience meets {req:g}+ years")
    if req and not seniority_ok:gaps.append(f"Requires {req:g}+ years; profile has {exp:g}")
    smin,smax=salary(t); target=float(p.get("minimum_lpa") or 0); salary_ok=not(target and smax) or smax>=target
    b["salary"]=WEIGHTS["salary"] if salary_ok else 0
    if smax and target and salary_ok: reasons.append(f"Salary range reaches {target:g} LPA target")
    if smax and target and not salary_ok:gaps.append(f"Salary may not reach {target:g} LPA target")
    loc_ok=location_fit(str(j.get("location","")),p); b["location"]=WEIGHTS["location"] if loc_ok else 0
    if not loc_ok:gaps.append("Location/remote preference mismatch")
    notice_req=parse_notice(t); notice_ok=True; candidate_notice=p.get("notice_period_days")
    if notice_req is not None and candidate_notice is not None: notice_ok=int(candidate_notice)<=notice_req
    b["notice"]=WEIGHTS["notice"] if notice_ok else 0
    raw=sum(b.values()); score=round(100*raw/sum(WEIGHTS.values()),1)
    hard=[]
    if not b["rn"]:hard.append("Not clearly a React Native role")
    if not seniority_ok:hard.append("Insufficient experience")
    if p.get("minimum_lpa") and smax is not None and smax<float(p["minimum_lpa"]):hard.append("Salary ceiling below target")
    if not loc_ok and p.get("strict_location"):hard.append("Strict location mismatch")
    if not notice_ok:hard.append("Notice period mismatch")
    decision="DON'T APPLY" if hard else ("APPLY" if score>=p.get("apply_score_threshold",70) else "MAYBE")
    return {"score":score,"decision":decision,"breakdown":b,"reasons":reasons,"gaps":gaps,"hard_failures":hard,"seniority_ok":seniority_ok,"salary_ok":salary_ok,"location_ok":loc_ok,"notice_ok":notice_ok,"salary_range":[smin,smax],"required_experience":req,"required_notice_days":notice_req}
def rank_jobs(jobs,p,min_score=0,include_rejected=False):
    out=[]
    for j in jobs:
        m=score_job(j,p)
        if m["score"]>=min_score and (include_rejected or not m["hard_failures"]):out.append({**j,"match":m})
    return sorted(out,key=lambda x:(x["match"]["decision"]!="APPLY",-x["match"]["score"]))