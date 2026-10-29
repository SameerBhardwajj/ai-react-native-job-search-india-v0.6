import re
from .matcher import CHECKS
def analyze_resume(text,j):
    low=text.lower();jd=(j.get("description","")+" "+j.get("role","")).lower();
    present=[];missing=[]
    for k,terms in CHECKS.items():
        if any(x in low for x in terms):present.append(k)
        elif any(x in jd for x in terms):missing.append(k)
    bullets=[x.strip() for x in re.split(r"[\n•]",text) if len(x.strip())>30]
    action=re.findall(r"\b(?:built|led|designed|implemented|optimized|reduced|increased|migrated|automated|delivered|improved)\b",low)
    quantified=len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:%|x|ms|s|lpa|million|k)\b",low))
    return {"keyword_coverage":round(100*len(present)/(len(present)+len(missing) or 1),1),"present":present,"missing":missing,"bullet_count":len(bullets),"action_verb_count":len(action),"quantified_impact_count":quantified,"warnings":(["Few quantified impact statements"] if quantified<3 else [])}