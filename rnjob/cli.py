import argparse,json
from pathlib import Path
from .database import init_db,all_jobs,get_job,create_application,applications,update_status,stats,events
from .profile import load_profile
from .resume_parser import import_resume
from .ingest import load_json,load_csv,import_jobs,fetch_url
from .matcher import rank_jobs,score_job
from .ai import available,tailored_resume,cover_letter,interview_pack,skill_gap,fact_check
from .ats import analyze_resume
from .artifacts import export_docx,export_pdf,save_json_artifact
from .config import OUTPUT_DIR

def ai_job(i):
    j=get_job(i)
    if not j:raise SystemExit("Job not found")
    if not available():raise SystemExit("Configure AI_PROVIDER and API key first")
    return load_profile(),j
def preflight(i):
    p=load_profile();j=get_job(i)
    if not j:raise SystemExit("Job not found")
    m=score_job(j,p);ats=analyze_resume(p.get("resume_text",""),j)
    checks={"decision":m["decision"],"hard_failures":m["hard_failures"],"ats":ats,"integrity":json.loads(j.get("integrity_json") or "{}"),"url":j.get("url")}
    checks["ready_to_apply"]=m["decision"]=="APPLY" and not checks["hard_failures"] and checks["integrity"].get("safe",True)
    return checks
def main():
    ap=argparse.ArgumentParser(prog="rnjob");s=ap.add_subparsers(dest="cmd",required=True)
    s.add_parser("init").set_defaults(fn=lambda a:(init_db(),print("Initialized database.")))
    s.add_parser("profile").set_defaults(fn=lambda a:print(json.dumps(load_profile(),indent=2,ensure_ascii=False)))
    p=s.add_parser("profile-import");p.add_argument("path");p.set_defaults(fn=lambda a:print(json.dumps(import_resume(a.path),indent=2,ensure_ascii=False)[:10000]))
    for name,loader in [("import-jobs",load_json),("import-csv",load_csv)]:
        p=s.add_parser(name);p.add_argument("path");p.set_defaults(fn=lambda a,ld=loader:(init_db(),print(f"Imported {len(import_jobs(ld(a.path)))} jobs.")))
    p=s.add_parser("fetch-url");p.add_argument("url");p.set_defaults(fn=lambda a:(init_db(),print(json.dumps(__import__("rnjob.database",fromlist=["upsert_job"]).upsert_job(fetch_url(a.url)),indent=2))))
    p=s.add_parser("jobs");p.add_argument("--min-score",type=float,default=0);p.add_argument("--limit",type=int,default=20);p.add_argument("--include-rejected",action="store_true")
    def jobs(a):
        init_db()
        for j in rank_jobs(all_jobs(),load_profile(),a.min_score,a.include_rejected)[:a.limit]:
            m=j["match"];print(f'[{j["id"]}] {m["decision"]:<10} {m["score"]:>5.1f} | {j["role"]} | {j["company"]} | {j["location"]}');print("  reasons:","; ".join(m["reasons"]) or "—");print("  gaps:","; ".join(m["gaps"]) or "—");print("  hard failures:","; ".join(m["hard_failures"]) or "—")
    p.set_defaults(fn=jobs)
    p=s.add_parser("analyze");p.add_argument("path");p.set_defaults(fn=lambda a:print(json.dumps(score_job({"role":"JD","location":"India","description":Path(a.path).read_text(encoding="utf-8")},load_profile()),indent=2)))
    p=s.add_parser("preflight");p.add_argument("job_id",type=int);p.set_defaults(fn=lambda a:print(json.dumps(preflight(a.job_id),indent=2,ensure_ascii=False)))
    p=s.add_parser("apply");p.add_argument("job_id",type=int);p.add_argument("--resume-version",default="");p.add_argument("--cover-version",default="");p.add_argument("--notes",default="");p.set_defaults(fn=lambda a:(preflight_or_exit(a.job_id),init_db(),create_application(a.job_id,"APPLIED",a.resume_version,a.cover_version,a.notes),print("Application recorded after preflight.")))
    s.add_parser("applications").set_defaults(fn=lambda a:(init_db(),print(json.dumps(applications(),indent=2))))
    p=s.add_parser("events");p.add_argument("job_id",type=int);p.set_defaults(fn=lambda a:print(json.dumps(events(a.job_id),indent=2)))
    p=s.add_parser("status");p.add_argument("job_id",type=int);p.add_argument("status");p.add_argument("--notes",default="");p.set_defaults(fn=lambda a:(init_db(),update_status(a.job_id,a.status,a.notes),print("Updated.")))
    s.add_parser("stats").set_defaults(fn=lambda a:(init_db(),print(json.dumps(stats(),indent=2))))
    for name,func in [("tailor",tailored_resume),("cover",cover_letter),("interview",interview_pack),("gap",skill_gap)]:
        p=s.add_parser(name);p.add_argument("job_id",type=int)
        def make(fn):
            def run(a):
                pr,j=ai_job(a.job_id);obj=fn(pr,j);check=fact_check(obj,pr);folder={"tailor":"resumes","cover":"cover_letters","interview":"interviews","gap":"interviews"}[a.cmd];save_json_artifact({"output":obj,"fact_check":check},folder,f"{a.cmd}_{a.job_id}.json");print(json.dumps({"fact_check":check,"file":str(OUTPUT_DIR/folder/f'{a.cmd}_{a.job_id}.json')},indent=2));
            return run
        p.set_defaults(fn=make(func))
    p=s.add_parser("ats");p.add_argument("job_id",type=int);p.set_defaults(fn=lambda a:print(json.dumps(analyze_resume(load_profile().get("resume_text",""),get_job(a.job_id)),indent=2)))
    p=s.add_parser("export-resume");p.add_argument("source",choices=["master","tailored"]);p.add_argument("--job-id",type=int);p.add_argument("--format",choices=["docx","pdf"],default="docx")
    def ex(a):
        if a.source=="master":t=load_profile().get("resume_text","")
        else:
            if not a.job_id:raise SystemExit("--job-id required for tailored")
            f=OUTPUT_DIR/"resumes"/f"tailor_{a.job_id}.json";d=json.loads(f.read_text());
            if not d["fact_check"]["passed"]:raise SystemExit("Tailored output failed fact check; do not export.")
            t=d["output"]
        if not t:raise SystemExit("No resume content")
        print(export_docx(t,f"resume_{a.source}_{a.job_id or 'master'}.docx") if a.format=="docx" else export_pdf(t,f"resume_{a.source}_{a.job_id or 'master'}.pdf"))
    p.set_defaults(fn=ex)
    a=ap.parse_args();a.fn(a)
def preflight_or_exit(i):
    r=preflight(i)
    if not r["ready_to_apply"]:raise SystemExit("Preflight blocked application: "+json.dumps(r,ensure_ascii=False))
if __name__=="__main__":main()