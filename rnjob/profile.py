import json,re
from pathlib import Path
from .config import PROFILE_PATH
ALIASES={"rn":"React Native","react native":"React Native","reactnative":"React Native","ts":"TypeScript","typescript":"TypeScript","js":"JavaScript","javascript":"JavaScript","reactjs":"React","redux":"Redux","react navigation":"React Navigation","reanimated":"Reanimated","gesture handler":"Gesture Handler","flashlist":"FlashList","jest":"Jest","react native testing library":"React Native Testing Library","firebase":"Firebase","push notifications":"Push Notifications","ci/cd":"CI/CD","android":"Android","ios":"iOS","performance":"Performance Optimization","deep linking":"Deep Linking","ota":"OTA Updates","codepush":"OTA Updates","hermes":"Hermes","native modules":"Native Modules","next.js":"Next.js","node.js":"Node.js","fastapi":"FastAPI","postgresql":"PostgreSQL","docker":"Docker"}
def load_profile(path=PROFILE_PATH): return json.loads(Path(path).read_text(encoding="utf-8"))
def save_profile(p,path=PROFILE_PATH):
    Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(p,indent=2,ensure_ascii=False),encoding="utf-8")
def extract_years(t):
    vals=[float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",t,re.I)]
    return max(vals,default=None)
def extract_skills(t):
    low=t.lower(); out=[]
    for a,c in ALIASES.items():
        if re.search(r"(?<!\w)"+re.escape(a)+r"(?!\w)",low) and c not in out: out.append(c)
    return out
def extract_profile_from_text(text):
    y=extract_years(text); headings=[]
    for h in ["summary","professional summary","experience","work experience","skills","technical skills","education","projects"]:
        if re.search(rf"(?im)^\s*{re.escape(h)}\s*:?\s*$",text): headings.append(h)
    return {"headline":"Senior React Native Developer","experience_years":int(y) if y and y.is_integer() else y,"skills":{"core":extract_skills(text),"secondary":[]},"sections_detected":headings,"resume_text":text,"source":"resume-import"}
def truth_claims(p):
    return {"experience_years":p.get("experience_years"),"skills":sorted(set(p.get("skills",{}).get("core",[])+p.get("skills",{}).get("secondary",[]))),"employers":[x.get("company") for x in p.get("experience",[]) if x.get("company")],"roles":[x.get("title") for x in p.get("experience",[]) if x.get("title")],"projects":[x.get("name") for x in p.get("projects",[]) if x.get("name")]}