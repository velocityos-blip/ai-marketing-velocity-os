"""Workspace website, Google authorization and reusable SEO audit evidence."""
import json
import os
import re
import secrets
import time
from datetime import date,timedelta
from urllib.parse import quote,urlencode,urlsplit

import httpx
from fastapi import HTTPException
import social
from site_crawl import website,crawl

API="https://www.googleapis.com/webmasters/v3/sites"
TOKEN="https://oauth2.googleapis.com/token"
SCOPE="https://www.googleapis.com/auth/webmasters.readonly"
WEEK=7*86400


def setup(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS search_site(org INTEGER PRIMARY KEY,site TEXT NOT NULL,version TEXT NOT NULL,
        property TEXT,secret TEXT,due INTEGER NOT NULL,report TEXT);
    CREATE TABLE IF NOT EXISTS search_auth(state TEXT PRIMARY KEY,org INTEGER,email TEXT,version TEXT,expires INTEGER);
    """)


def credentials():
    return {"client_id":os.getenv("GSC_CLIENT_ID"),"client_secret":os.getenv("GSC_CLIENT_SECRET")}


def state(db,org):
    row=db.execute("SELECT site,property,report FROM search_site WHERE org=?",(org,)).fetchone()
    return dict(available=all(credentials().values()),site=row["site"] if row else "",
                property=row["property"] if row else None,report=json.loads(row["report"]) if row and row["report"] else None)


def google(method,url,**kw):
    response=httpx.request(method,url,timeout=12,**kw)
    response.raise_for_status()
    return response.json()


def match(site,prop):
    host=urlsplit(site).hostname
    if prop.startswith("sc-domain:"):
        domain=prop[len("sc-domain:"):].lower()
        return host==domain or host.endswith("."+domain)
    p=urlsplit(prop)
    return p.scheme=="https" and p.netloc==host and site.startswith(prop)


def action(db,user,op,data):
    org=user["org"]
    now=int(time.time())
    if op=="save":
        try: site=website(data.get("site"))
        except (UnicodeError,ValueError):
            raise HTTPException(400,"Enter a valid public HTTPS website.")
        with db:
            db.execute("""INSERT INTO search_site(org,site,version,due) VALUES(?,?,?,0)
                ON CONFLICT(org) DO UPDATE SET site=excluded.site,version=excluded.version,property=NULL,
                secret=NULL,due=0,report=NULL WHERE search_site.site!=excluded.site""",(org,site,secrets.token_hex(16)))
        return {"ok":True}
    row=db.execute("SELECT * FROM search_site WHERE org=?",(org,)).fetchone()
    if not row:raise HTTPException(400,"Save your website first.")
    if op=="remove":
        with db:
            db.execute("DELETE FROM search_site WHERE org=?",(org,))
            db.execute("DELETE FROM search_auth WHERE org=?",(org,))
        return {"ok":True}
    if op=="disconnect":
        with db:
            db.execute("UPDATE search_site SET property=NULL,secret=NULL,report=NULL,version=?,due=0 WHERE org=?",(secrets.token_hex(16),org))
        return {"ok":True}
    creds=credentials()
    if not all(creds.values()):raise HTTPException(503,"Google OAuth app setup required.")
    if op=="start":
        key=secrets.token_urlsafe(32)
        with db:
            db.execute("DELETE FROM search_auth WHERE expires<=? OR (org=? AND email=?)",(now,org,user["email"]))
            db.execute("INSERT INTO search_auth VALUES(?,?,?,?,?)",(key,org,user["email"],row["version"],now+900))
        return {"url":"https://accounts.google.com/o/oauth2/v2/auth?"+urlencode(dict(client_id=creds["client_id"],
                redirect_uri=social.CALLBACK,response_type="code",scope=SCOPE,access_type="offline",prompt="consent",state=key))}
    if op!="finish": raise HTTPException(404,"Unknown search action.")
    with db:
        consumed=db.execute("DELETE FROM search_auth WHERE state=? AND org=? AND email=? AND version=? AND expires>?",
                            (data.get("state"),org,user["email"],row["version"],now)).rowcount
    if not consumed:raise HTTPException(400,"Google authorization expired. Connect again.")
    tokens=google("POST",TOKEN,data={**creds,"code":data.get("code",""),"grant_type":"authorization_code","redirect_uri":social.CALLBACK})
    if not tokens.get("refresh_token"):raise HTTPException(400,"Google did not grant offline access. Reconnect.")
    props=google("GET",API,headers={"Authorization":"Bearer "+tokens["access_token"]}).get("siteEntry",[])
    matches=[p["siteUrl"] for p in props if p.get("permissionLevel")!="siteUnverifiedUser" and match(row["site"],p["siteUrl"])]
    if not matches:raise HTTPException(400,"Google returned no accessible property matching the saved website.")
    prop=max(matches,key=lambda s:(not s.startswith("sc-domain:"),len(s)))
    with db:
        changed=db.execute("UPDATE search_site SET property=?,secret=?,version=?,due=0,report=NULL WHERE org=? AND version=?",
                   (prop,social.pack({"refresh":tokens["refresh_token"]}),secrets.token_hex(16),org,row["version"])).rowcount
    if not changed:raise HTTPException(409,"Website settings changed. Connect again.")
    return {"ok":True}


def analytics(row):
    fresh=google("POST",TOKEN,data={**credentials(),"grant_type":"refresh_token","refresh_token":social.unpack(row["secret"])["refresh"]})
    end=date.today()-timedelta(days=3)
    start=end-timedelta(days=27)
    body=dict(startDate=str(start),endDate=str(end),dimensions=["page","query"],rowLimit=12,
              dimensionFilterGroups=[{"filters":[{"dimension":"page","operator":"includingRegex","expression":"^"+re.escape(row["site"])}]}])
    rows=google("POST",API+"/"+quote(row["property"],safe="")+"/searchAnalytics/query",
                headers={"Authorization":"Bearer "+fresh["access_token"]},json=body).get("rows",[])
    return {"status":"available","start":str(start),"end":str(end),"rows":rows}


def refresh(db,org):
    row=db.execute("SELECT * FROM search_site WHERE org=?",(org,)).fetchone()
    if not row:return None
    if row["due"]>time.time() and row["report"]:return json.loads(row["report"])
    report={"checked":int(time.time()),"crawl":crawl(row["site"]),"search_console":{"status":"not connected"}}
    if row["secret"]:
        try:report["search_console"]=analytics(row)
        except Exception:report["search_console"]={"status":"unavailable; check Google access"}
    retry=report["search_console"]["status"].startswith("unavailable") or not report["crawl"]["pages"]
    with db:
        changed=db.execute("UPDATE search_site SET report=?,due=? WHERE org=? AND version=?",
            (json.dumps(report),int(time.time())+(21600 if retry else WEEK),org,row["version"])).rowcount
    return report if changed else None


def tick(db):
    row=db.execute("SELECT org FROM search_site WHERE due<=? ORDER BY due LIMIT 1",(int(time.time()),)).fetchone()
    if not row:return False
    refresh(db,row["org"])
    return True
