"""Live RLS check for public.glucose_readings on the Supabase project, using ONLY the public anon key
and two confirmed test users (credentials in the gitignored .env.glucose-test-users.local). Creates and
deletes its own rows. Usage: SUPABASE_ANON_KEY=<anon key> python3 supabase/tests/live_rls_check.py"""
import json,os,sys,urllib.request,uuid,datetime
URL=os.environ.get("SUPABASE_URL", "https://zlxefqhzceiloplyszje.supabase.co")
ANON=os.environ["SUPABASE_ANON_KEY"]  # public anon key only
env={}
for l in open(os.environ.get("GLUCOSE_TEST_USERS_FILE", ".env.glucose-test-users.local")):
    if "=" in l and not l.startswith("#"): k,v=l.strip().split("=",1); env[k]=v
def req(method,path,token=None,body=None,headers=None):
    h={"apikey":ANON,"Content-Type":"application/json","Authorization":f"Bearer {token or ANON}"}
    h.update(headers or {})
    r=urllib.request.Request(URL+path,method=method,headers=h,data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r) as resp: t=resp.read().decode(); return resp.status,(json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        t=e.read().decode(); 
        try: return e.code,json.loads(t)
        except: return e.code,t
def login(tag):
    s,d=req("POST","/auth/v1/token?grant_type=password",body={"email":env[f"GLUCOSE_TEST_USER_{tag}_EMAIL"],"password":env[f"GLUCOSE_TEST_USER_{tag}_PASSWORD"]})
    assert s==200,(s,d); return d["access_token"],d["user"]["id"]
res=[]
def check(name,ok,detail=""):
    res.append((name,ok)); print(("PASS" if ok else "FAIL"),name,detail)
ta,ida=login("A"); tb,idb=login("B"); check("sign-in A and B (email/password)",True)
T="/rest/v1/glucose_readings"; R={"Prefer":"return=representation"}
now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
row={"measured_at":(now-datetime.timedelta(hours=2)).isoformat(),"tz_offset_minutes":300,"value_original":112,"unit_original":"mg/dL","meal_context":"fasting","note":"rls-check"}
s,d=req("POST",T,ta,row,R); check("A insert own manual",s==201 and d[0]["user_id"]==ida,f"{s}"); aid=d[0]["id"] if s==201 else None
imp={"measured_at":(now-datetime.timedelta(hours=3)).isoformat(),"tz_offset_minutes":300,"value_original":6.2,"unit_original":"mmol/L","source_type":"ocr","source_provider":"rls-check","source_record_id":"rls-"+uuid.uuid4().hex[:8],"source_meta":{"engine":"check"},"import_batch_id":"rls-batch","dedupe_key":"x|111.71"}
s,d=req("POST",T,ta,imp,R); check("A insert own ocr import (value_mg_dl generated)",s==201 and float(d[0]["value_mg_dl"])==111.71,f"{s} {d[0].get('value_mg_dl') if s==201 else d}"); iid=d[0]["id"] if s==201 else None
s,d=req("POST",T,ta,imp,R); check("A re-import same source record rejected (unique import idx)",s==409,f"{s}")
s,d=req("GET",T+f"?id=eq.{aid}",ta); check("A read own",s==200 and len(d)==1)
s,d=req("PATCH",T+f"?id=eq.{aid}",ta,{"value_original":118},R); check("A update own manual",s==200 and len(d)==1 and float(d[0]["value_original"])==118)
s,d=req("PATCH",T+f"?id=eq.{iid}",ta,{"value_original":7},R); check("A update imported value blocked by trigger",s>=400,f"{s}")
s,d=req("POST",T,ta,{**row,"user_id":idb},R); check("A insert as B denied",s in (401,403),f"{s}")
s,d=req("GET",T+f"?id=eq.{aid}",tb); check("B read A's row returns nothing",s==200 and d==[],f"{s} {d}")
s,d=req("GET",T,tb); check("B list sees no A rows",s==200 and all(x["user_id"]==idb for x in d))
s,d=req("PATCH",T+f"?id=eq.{aid}",tb,{"note":"hacked"},R); check("B update A's row affects 0 rows",s==200 and d==[],f"{s} {d}")
s,d=req("DELETE",T+f"?id=eq.{aid}",tb,headers=R); check("B delete A's row affects 0 rows",s==200 and d==[],f"{s} {d}")
s,d=req("GET",T+f"?id=eq.{aid}",ta); check("A row intact after B attempts",s==200 and len(d)==1 and d[0]["note"]=="rls-check")
s,d=req("GET",T); check("anon select denied",s in (401,403),f"{s}")
s,d=req("POST",T,None,row,R); check("anon insert denied",s in (401,403),f"{s}")
s,d=req("DELETE",T+f"?id=eq.{aid}",None,headers=R); check("anon delete denied",s in (401,403),f"{s}")
for i in (aid,iid):
    s,d=req("DELETE",T+f"?id=eq.{i}",ta,headers=R); check("A delete own",s==200 and len(d)==1)
print(f"{sum(o for _,o in res)}/{len(res)} passed"); sys.exit(0 if all(o for _,o in res) else 1)
