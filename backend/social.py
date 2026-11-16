"""Company-authorized social destinations and post-level performance."""
import base64
import hashlib
import json
import os
import secrets
import time
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException

NETWORKS = ("linkedin", "instagram", "facebook")
PUBLIC = os.getenv("VOS_PUBLIC_URL", "https://viralmarketstrategy.com/vos").rstrip("/")
CALLBACK = PUBLIC + "/dashboard"
GRAPH = "https://graph.facebook.com/" + os.getenv("META_GRAPH_VERSION", "v25.0")
LI = "https://api.linkedin.com/rest"
OAUTH = "https://www.linkedin.com/oauth/v2"


def setup(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS social_media(key TEXT PRIMARY KEY, jpeg BLOB, expires INTEGER);
    CREATE TABLE IF NOT EXISTS social_auth(state TEXT PRIMARY KEY,org INTEGER,email TEXT,network TEXT,expires INTEGER);
    CREATE TABLE IF NOT EXISTS social_choice(key TEXT PRIMARY KEY,org INTEGER,email TEXT,network TEXT,account TEXT,label TEXT,secret TEXT,expires INTEGER);
    CREATE TABLE IF NOT EXISTS social_channel(org INTEGER,network TEXT,account TEXT,label TEXT,secret TEXT,revision TEXT,problem TEXT,PRIMARY KEY(org,network));
    CREATE TABLE IF NOT EXISTS social_post(run INTEGER,org INTEGER,network TEXT,account TEXT,status TEXT,remote TEXT,metrics TEXT,due INTEGER,created INTEGER,PRIMARY KEY(run,network));
    """)


def credentials(network):
    prefix = "LINKEDIN" if network == "linkedin" else "META"
    return os.getenv(prefix+"_CLIENT_ID"), os.getenv(prefix+"_CLIENT_SECRET")


def cipher():
    key = hashlib.sha256(("vos-social-v1/"+os.environ["JWT_SECRET_KEY"]).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def pack(data):
    return cipher().encrypt(json.dumps(data).encode()).decode()


def unpack(secret):
    return json.loads(cipher().decrypt(secret.encode()))


def request(method, url, **kwargs):
    response = httpx.request(method, url, timeout=20, **kwargs)
    response.raise_for_status()
    return response


def linkedin(token):
    return {"Authorization":"Bearer "+token,"LinkedIn-Version":os.getenv("LINKEDIN_VERSION","202609"),
            "X-Restli-Protocol-Version":"2.0.0"}


def state(db, org):
    rows = {r["network"]:dict(r) for r in db.execute("SELECT network,label,problem FROM social_channel WHERE org=?", (org,))}
    return [{"network":n,"available":all(credentials(n)),**rows.get(n,{})} for n in NETWORKS]


def auth(db, user, op, d):
    org,email = user["org"],user["email"]
    now = int(time.time())
    n = d.get("network")
    if n not in NETWORKS:
        raise HTTPException(400,"Unknown social network.")
    client,secret = credentials(n)
    if op == "disconnect":
        with db:
            db.execute("DELETE FROM social_channel WHERE org=? AND network=?",(org,n))
            db.execute("DELETE FROM social_choice WHERE org=? AND network=?",(org,n))
            db.execute("DELETE FROM social_auth WHERE org=? AND network=?",(org,n))
        return {"ok":True}
    if not client or not secret:
        raise HTTPException(503,"The VOS operator must configure the provider app.")
    if op == "start":
        key = secrets.token_urlsafe(32)
        with db:
            db.execute("DELETE FROM social_auth WHERE expires<=?",(now,))
            db.execute("DELETE FROM social_choice WHERE expires<=?",(now,))
            db.execute("INSERT INTO social_auth VALUES(?,?,?,?,?)",(key,org,email,n,now+900))
        scope = {"linkedin":"rw_organization_admin w_organization_social r_organization_social",
                 "facebook":"pages_show_list,pages_manage_posts,pages_read_engagement",
                 "instagram":"pages_show_list,pages_read_engagement,instagram_basic,instagram_content_publish,instagram_manage_insights"}[n]
        base = OAUTH+"/authorization" if n=="linkedin" else "https://www.facebook.com/"+GRAPH.rsplit("/",1)[1]+"/dialog/oauth"
        return {"url":base+"?"+urlencode(dict(client_id=client,redirect_uri=CALLBACK,response_type="code",state=key,scope=scope))}
    if op == "select":
        with db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM social_choice WHERE key=? AND org=? AND email=? AND network=? AND expires>?",
                           (d.get("key"),org,email,n,now)).fetchone()
            if not row:
                raise HTTPException(400,"Account selection expired. Connect again.")
            db.execute("INSERT OR REPLACE INTO social_channel VALUES(?,?,?,?,?,?,NULL)",
                       (org,n,row["account"],row["label"],row["secret"],secrets.token_hex(16)))
            db.execute("DELETE FROM social_choice WHERE org=? AND email=? AND network=?",(org,email,n))
        return {"ok":True}
    if op != "finish":
        raise HTTPException(404,"Unknown action.")
    with db:
        cur=db.execute("DELETE FROM social_auth WHERE state=? AND org=? AND email=? AND network=? AND expires>?",(d.get("state"),org,email,n,now))
        if not cur.rowcount:
            raise HTTPException(400,"Authorization expired. Connect again.")
    grant=dict(client_id=client,client_secret=secret,redirect_uri=CALLBACK,code=d.get("code",""),grant_type="authorization_code")
    choices=[]
    if n=="linkedin":
        tokens=request("POST",OAUTH+"/accessToken",data=grant).json()
        tokens["expires"]=now+tokens.get("expires_in",0)
        headers=linkedin(tokens["access_token"])
        start=0
        while True:
            batch=request("GET",LI+"/organizationAcls",headers=headers,params=dict(q="roleAssignee",role="ADMINISTRATOR",state="APPROVED",start=start,count=50)).json()["elements"]
            for acl in batch:
                account=acl["organization"]
                label=request("GET",LI+"/organizations/"+account.split(":")[-1],headers=headers).json().get("localizedName",account)
                choices.append((account,label,tokens))
            if len(batch)<50: break
            start+=50
    else:
        short=request("POST",GRAPH+"/oauth/access_token",data=grant).json()["access_token"]
        long=request("POST",GRAPH+"/oauth/access_token",data=dict(client_id=client,client_secret=secret,grant_type="fb_exchange_token",fb_exchange_token=short)).json()["access_token"]
        params={"fields":"id,name,access_token"+(",instagram_business_account{id,username}" if n=="instagram" else ""),"limit":100}
        while True:
            page=request("GET",GRAPH+"/me/accounts",headers={"Authorization":"Bearer "+long},params=params).json()
            for item in page["data"]:
                account=item if n=="facebook" else item.get("instagram_business_account")
                if account:
                    choices.append((account["id"],account.get("username") or item["name"],{"access_token":item["access_token"]}))
            if not page.get("paging",{}).get("next"): break
            params["after"]=page["paging"]["cursors"]["after"]
    out=[]
    with db:
        for account,label,tokens in choices:
            key=secrets.token_urlsafe(24)
            db.execute("INSERT INTO social_choice VALUES(?,?,?,?,?,?,?,?)",(key,org,email,n,account,label,pack(tokens),now+900))
            out.append(dict(key=key,label=label))
    return {"choices":out}


def access(db,ch):
    tokens=unpack(ch["secret"])
    if ch["network"]=="linkedin" and tokens.get("expires",0)<time.time()+3600 and tokens.get("refresh_token"):
        client,secret=credentials("linkedin")
        fresh=request("POST",OAUTH+"/accessToken",data=dict(grant_type="refresh_token",refresh_token=tokens["refresh_token"],client_id=client,client_secret=secret)).json()
        tokens.update(fresh,expires=int(time.time())+fresh["expires_in"])
        with db:
            db.execute("UPDATE social_channel SET secret=? WHERE revision=?",(pack(tokens),ch["revision"]))
    return tokens["access_token"]


def publish(ch,token,copy,image):
    n,account=ch["network"],ch["account"]
    if n=="linkedin":
        data=dict(author=account,commentary=copy,visibility="PUBLIC",lifecycleState="PUBLISHED",
                  distribution=dict(feedDistribution="MAIN_FEED",targetEntities=[],thirdPartyDistributionChannels=[]),isReshareDisabledByAuthor=False)
        return request("POST",LI+"/posts",headers=linkedin(token),json=data).headers["x-restli-id"]
    headers={"Authorization":"Bearer "+token}
    if n=="facebook":
        return request("POST",GRAPH+"/"+account+"/feed",headers=headers,data={"message":copy}).json()["id"]
    container=request("POST",GRAPH+"/"+account+"/media",headers=headers,data={"caption":copy,"image_url":image}).json()["id"]
    for _ in range(12):
        status=request("GET",GRAPH+"/"+container,headers=headers,params={"fields":"status_code"}).json()["status_code"]
        if status=="FINISHED": break
        if status!="IN_PROGRESS": raise ValueError("Media processing failed")
        time.sleep(5)
    else: raise ValueError("Media processing timeout")
    return request("POST",GRAPH+"/"+account+"/media_publish",headers=headers,data={"creation_id":container}).json()["id"]


def measure(ch,token,remote):
    n=ch["network"]
    if n=="linkedin":
        field="ugcPosts" if ":ugcPost:" in remote else "shares"
        from urllib.parse import quote
        url=LI+"/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity="+quote(ch["account"],safe="")+"&"+field+"=List("+quote(remote,safe="")+")"
        rows=request("GET",url,headers=linkedin(token)).json()["elements"]
        return rows[0]["totalShareStatistics"] if rows else {}
    headers={"Authorization":"Bearer "+token}
    if n=="instagram":
        rows=request("GET",GRAPH+"/"+remote+"/insights",headers=headers,params={"metric":"reach,likes,comments,saved,shares"}).json()["data"]
        return {r["name"]:r["values"][-1]["value"] for r in rows if r.get("values")}
    data=request("GET",GRAPH+"/"+remote,headers=headers,params={"fields":"reactions.limit(0).summary(true),comments.limit(0).summary(true),shares"}).json()
    return {k:data[k]["summary"]["total_count"] for k in ("reactions","comments") if k in data} | ({"shares":data["shares"]["count"]} if "shares" in data else {})


def targets(db,org):
    return db.execute("SELECT * FROM social_channel WHERE org=?",(org,)).fetchall()


def history(db,org):
    rows=db.execute("""SELECT p.run,p.network,p.status,p.metrics,p.created,p.remote,r.draft FROM social_post p
        JOIN runs r ON r.id=p.run WHERE p.org=? ORDER BY p.run DESC,p.network LIMIT 24""",(org,))
    return [{**dict(row),"metrics":json.loads(row["metrics"]) if row["metrics"] else None} for row in rows]


def deliver(db,job,run,channels):
    for ch in channels:
        n=ch["network"]
        now=int(time.time())
        with db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("""SELECT 1 FROM autopilot a JOIN social_channel s ON a.org=s.org
                WHERE a.org=? AND a.enabled=1 AND a.version=? AND s.revision=?""",(job["org"],job["version"],ch["revision"])).fetchone(): continue
            if not db.execute("INSERT OR IGNORE INTO social_post VALUES(?,?,?,?,?,NULL,NULL,NULL,?)",
                              (run["id"],job["org"],n,ch["account"],"Sending",now)).rowcount: continue
        try:
            image=None
            if n=="instagram":
                image=make_card(db,job["name"],run["draft"])
            remote=publish(ch,access(db,ch),run["draft"],image)
            with db:
                db.execute("UPDATE social_post SET status='Published',remote=?,due=? WHERE run=? AND network=?",(remote,now+900,run["id"],n))
        except Exception as exc:
            status="Check provider before retrying"
            if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code in (401,403): status="Reconnect account or check permissions"
            with db:
                db.execute("UPDATE social_post SET status=? WHERE run=? AND network=?",(status,run["id"],n))
                db.execute("UPDATE social_channel SET problem=? WHERE revision=?",(status,ch["revision"]))


def collect(db):
    now=int(time.time())
    post=db.execute("""SELECT p.* FROM social_post p JOIN social_channel s USING(org,network,account)
               WHERE p.due<=? ORDER BY p.due LIMIT 1""",(now,)).fetchone()
    if not post: return False
    ch=db.execute("SELECT * FROM social_channel WHERE org=? AND network=? AND account=?",(post["org"],post["network"],post["account"])).fetchone()
    due=now+21600 if now-post["created"]<30*86400 else None
    try:
        values=measure(ch,access(db,ch),post["remote"])
        with db:
            db.execute("UPDATE social_post SET metrics=?,due=?,status='Published' WHERE run=? AND network=?",
                       (json.dumps(values) if values else post["metrics"],due,post["run"],post["network"]))
    except Exception:
        with db:
            db.execute("UPDATE social_post SET due=?,status='Metrics unavailable' WHERE run=? AND network=?",(due,post["run"],post["network"]))
    return True


def make_card(db,company,copy):
    from io import BytesIO
    import textwrap
    from PIL import Image,ImageDraw,ImageFont
    img=Image.new("RGB",(1080,1080),"#12152c")
    draw=ImageDraw.Draw(img)
    font=lambda size:ImageFont.load_default(size=size)
    draw.rectangle((64,80,186,88),fill="#78ffe2")
    draw.text((64,120),company[:50],font=font(30),fill="#78ffe2")
    lines=textwrap.wrap(copy,width=36)
    size=min(44,740//max(1,len(lines)))
    draw.multiline_text((64,230),"\n".join(lines),font=font(size),spacing=9,fill="#ffffff")
    out=BytesIO()
    img.save(out,"JPEG",quality=88)
    key=secrets.token_urlsafe(32)
    with db:
        db.execute("DELETE FROM social_media WHERE expires<?",(int(time.time()),))
        db.execute("INSERT INTO social_media VALUES(?,?,?)",(key,out.getvalue(),int(time.time())+86400))
    return PUBLIC+"/api/social-media/"+key
