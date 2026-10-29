from html import escape
from .config import OUTPUT_DIR
def _text(obj):
    if isinstance(obj,str):return obj
    if isinstance(obj,dict):
        out=[]
        for k,v in obj.items():out.append(k.replace("_"," ").title()+":");out.append(_text(v))
        return "\n".join(out)
    if isinstance(obj,list):return "\n".join(("• "+_text(x)) for x in obj)
    return str(obj)
def save_json_artifact(obj,folder,filename):
    import json
    out=OUTPUT_DIR/folder/filename;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8");return out
def export_docx(text,filename="tailored_resume.docx"):
    from docx import Document
    out=OUTPUT_DIR/"resumes"/filename;out.parent.mkdir(parents=True,exist_ok=True);d=Document()
    for line in _text(text).splitlines():d.add_paragraph(line)
    d.save(out);return out
def export_pdf(text,filename="tailored_resume.pdf"):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    out=OUTPUT_DIR/"resumes"/filename;out.parent.mkdir(parents=True,exist_ok=True);doc=SimpleDocTemplate(str(out),pagesize=A4);st=getSampleStyleSheet();story=[]
    for line in _text(text).splitlines():story.append(Paragraph(escape(line),st["Normal"]) if line.strip() else Spacer(1,6))
    doc.build(story);return out