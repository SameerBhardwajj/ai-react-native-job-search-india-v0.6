import sys,uvicorn
from .cli import main
if len(sys.argv)>1 and sys.argv[1]=="web":
    host="127.0.0.1"
    if "--host" in sys.argv: host=sys.argv[sys.argv.index("--host")+1]
    uvicorn.run("rnjob.web:app",host=host,port=8000)
else: main()