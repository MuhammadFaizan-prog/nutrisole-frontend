"""Consume Figma's single-use upload URLs for independent content assets."""
from pathlib import Path
import json, urllib.request, concurrent.futures, sys
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/sys.argv[1]
jobs=json.loads(source.read_text())
def upload(job):
    data=(ROOT/job['path']).read_bytes()
    request=urllib.request.Request(job['submitUrl'],data=data,headers={'Content-Type':'image/png'},method='POST')
    with urllib.request.urlopen(request,timeout=90) as response:
        body=response.read()
        return {'asset':job['asset'],'nodeId':job['targetNodeId'],'status':response.status,'bytes':len(data)}
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(upload,jobs))
    (ROOT/sys.argv[2]).write_text(json.dumps(results,indent=2))
    print('Uploaded',len(results),'independent assets. All requests succeeded.')
finally:
    source.unlink(missing_ok=True)
