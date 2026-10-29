from pathlib import Path
from .profile import load_profile,save_profile,extract_profile_from_text
def read_pdf(p):
    from pypdf import PdfReader
    return "\n".join(x.extract_text() or "" for x in PdfReader(str(p)).pages)
def read_docx(p):
    from docx import Document
    d=Document(str(p)); a=[x.text for x in d.paragraphs]
    for t in d.tables:
        for r in t.rows: a.append(" | ".join(c.text for c in r.cells))
    return "\n".join(a)
def extract_text(p):
    p=Path(p)
    if p.suffix.lower()==".pdf": return read_pdf(p)
    if p.suffix.lower()==".docx": return read_docx(p)
    if p.suffix.lower() in {".txt",".md"}: return p.read_text(encoding="utf-8",errors="ignore")
    raise ValueError("Supported resume formats: PDF, DOCX, TXT, MD")
def import_resume(path):
    text=extract_text(path); p=load_profile(); e=extract_profile_from_text(text)
    p["resume_text"]=text; p["resume_source"]=str(path)
    if e.get("experience_years"): p["experience_years"]=e["experience_years"]
    p["skills"]["core"]=sorted(set(p.get("skills",{}).get("core",[])+e["skills"]["core"]))
    p["sections_detected"]=e["sections_detected"]; save_profile(p); return p