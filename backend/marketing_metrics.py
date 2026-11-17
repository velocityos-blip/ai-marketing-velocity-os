"""Read-only, company-scoped marketing measurement connections."""
import base64
import hashlib
import json
import math
import os
import re
import secrets
import time
from datetime import date,timedelta
from urllib.parse import urlencode,urlsplit
from urllib.request import urlopen,Request

import httpx
from fastapi import HTTPException
import social

GOOGLE='https://accounts.google.com/o/oauth2/v2/auth'
GTOKEN='https://oauth2.googleapis.com/token'
OAUTH={
 'ga4':('GSC',GOOGLE,GTOKEN,'https://www.googleapis.com/auth/analytics.readonly'),
 'youtube':('GSC',GOOGLE,GTOKEN,'https://www.googleapis.com/auth/youtube.readonly'),
 'x':('X','https://x.com/i/oauth2/authorize','https://api.x.com/2/oauth2/token','users.read tweet.read offline.access'),
 'pinterest':('PINTEREST','https://www.pinterest.com/oauth/','https://api.pinterest.com/v5/oauth/token','user_accounts:read'),
 'tiktok':('TIKTOK','https://www.tiktok.com/v2/auth/authorize/','https://open.tiktokapis.com/v2/oauth/token/','user.info.basic,user.info.stats')
}
NAMES={'ga4':'Google Analytics 4','bing':'Bing Webmaster Tools','clarity':'Microsoft Clarity','youtube':'YouTube','x':'X','tiktok':'TikTok','pinterest':'Pinterest','threads':'Threads'}

def setup(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS metric_auth(state TEXT PRIMARY KEY,org INTEGER,email TEXT,source TEXT,target TEXT,verifier TEXT,expires INTEGER);
    CREATE TABLE IF NOT EXISTS metric_connection(org INTEGER,source TEXT,target TEXT,secret TEXT,rev TEXT,report TEXT,checked INTEGER,due INTEGER,problem TEXT,PRIMARY KEY(org,source));
    """)

def creds(n):
    prefix=OAUTH[n][0]
    return os.getenv(prefix+'_CLIENT_ID'),os.getenv(prefix+'_CLIENT_SECRET')

def state(db,org):
    connected={r['source']:r for r in db.execute('SELECT source,report,checked,problem FROM metric_connection WHERE org=?',(org,))}
    return [dict(source=n,name=name,available=n not in OAUTH or all(creds(n)),connected=n in connected,
                 report=json.loads(connected[n]['report']) if n in connected else None,
                 checked=connected[n]['checked'] if n in connected else None,problem=connected[n]['problem'] if n in connected else None)
            for n,name in NAMES.items()]

def fetch(method,url,**kwargs):
    # The Bing endpoint requires a key in its query. Keep it out of HTTP client request logs.
    if url == 'https://ssl.bing.com/webmaster/api.svc/json/GetRankAndTrafficStats':
        with urlopen(Request(url+'?'+urlencode(kwargs['params'])),timeout=15) as response:
            return json.load(response)
    res=httpx.request(method,url,timeout=15,**kwargs)
    res.raise_for_status()
    return res.json()

def numeric(values):
    out={}
    for k,v in values.items():
        if isinstance(v,bool) or v is None:continue
        try: num=float(v)
        except (TypeError,ValueError):continue
        if math.isfinite(num):out[k]=int(num) if num.is_integer() else num
    return out

def read(n,token,target):
    headers={'Authorization':'Bearer '+token}
    def get(url,**params):return fetch('GET',url,headers=headers,params=params)
    period='Profile snapshot'
    if n=='ga4':
        end=date.today()-timedelta(days=1);start=end-timedelta(days=27)
        fields=['activeUsers','sessions','engagedSessions','keyEvents','totalRevenue']
        report=fetch('POST','https://analyticsdata.googleapis.com/v1beta/properties/'+target+':runReport',headers=headers,
            json={'dateRanges':[{'startDate':str(start),'endDate':str(end)}],'metrics':[{'name':k} for k in fields]})
        rows=report.get('rows',[])
        data=dict(zip(fields,[m['value'] for m in rows[0]['metricValues']])) if rows else {}
        label='Property '+target
        period=f"{start} – {end} · {report.get('metadata',{}).get('currencyCode','property currency')}"
    elif n=='bing':
        rows=fetch('GET','https://ssl.bing.com/webmaster/api.svc/json/GetRankAndTrafficStats',params={'siteUrl':target,'apikey':token})['d']
        dated=[(int(m[1]),row) for row in rows if (m:=re.search(r'/Date\((\d+)',row.get('Date','')))]
        stamp,row=max(dated,key=lambda pair:pair[0]) if dated else (None,{})
        data={k:row.get(k) for k in ['Clicks','Impressions']};label=target
        period=time.strftime('%Y-%m-%d UTC',time.gmtime(stamp/1000)) if stamp is not None else 'No reporting dates'
    elif n=='clarity':
        result=get('https://www.clarity.ms/export-data/api/v1/project-live-insights',numOfDays=1)
        data={}
        for group in result:
            if group['metricName'] in ('Traffic','ScrollDepth','EngagementTime') and len(group.get('information',[]))==1:
                data.update(numeric(group['information'][0]))
        label='Clarity project';period='Previous 24 hours'
    elif n=='youtube':
        accounts=get('https://www.googleapis.com/youtube/v3/channels',part='snippet,statistics',mine='true')['items']
        if len(accounts)!=1:raise ValueError('Select the Google identity for one YouTube channel.')
        account=accounts[0];label=account['snippet']['title'];data=dict(account['statistics'])
        if data.pop('hiddenSubscriberCount',False):data.pop('subscriberCount',None)
    elif n=='x':
        account=get('https://api.x.com/2/users/me',**{'user.fields':'public_metrics'})['data']
        label='@'+account['username'];data=account.get('public_metrics',{})
    elif n=='pinterest':
        account=get('https://api.pinterest.com/v5/user_account');label=account['username']
        data={k:account.get(k) for k in ['follower_count','following_count','pin_count','board_count','monthly_views']}
    elif n=='tiktok':
        account=get('https://open.tiktokapis.com/v2/user/info/',fields='open_id,display_name,follower_count,following_count,likes_count,video_count')['data']['user']
        label=account['display_name'];data={k:account.get(k) for k in ('follower_count','following_count','likes_count','video_count')}
    else:
        account=get('https://graph.threads.com/v1.0/me',fields='id,username')
        label=account['username'];metrics=get('https://graph.threads.com/v1.0/'+account['id']+'/threads_insights',metric='followers_count')['data']
        data={r['name']:r.get('total_value',{}).get('value') for r in metrics}
    return {'account':label,'period':period,'metrics':numeric(data)}

def exchange(n,grant):
    client,secret=creds(n);kw={}
    grant=dict(grant)
    if n in ('x','pinterest'):kw['auth']=(client,secret)
    else:grant.update({('client_key' if n=='tiktok' else 'client_id'):client,'client_secret':secret})
    return fetch('POST',OAUTH[n][2],data=grant,**kw)

def action(db,user,op,d):
    n=d.get('source');org=user['org'];now=int(time.time())
    if n not in NAMES:raise HTTPException(400,'Unknown measurement source.')
    if op=='disconnect':
        with db:
            db.execute('DELETE FROM metric_connection WHERE org=? AND source=?',(org,n))
            db.execute('DELETE FROM metric_auth WHERE org=? AND source=?',(org,n))
        return {'ok':True}
    target=str(d.get('target','')).strip()
    if op=='start' and n in OAUTH:
        if not all(creds(n)):raise HTTPException(503,'Provider app setup required.')
        if n=='ga4' and not re.fullmatch(r'[0-9]{1,20}',target):raise HTTPException(400,'Enter the numeric GA4 property ID.')
        key=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
        with db:
            db.execute('DELETE FROM metric_auth WHERE expires<=? OR (org=? AND email=? AND source=?)',(now,org,user['email'],n))
            db.execute('INSERT INTO metric_auth VALUES(?,?,?,?,?,?,?)',(key,org,user['email'],n,target,verifier,now+900))
        params={('client_key' if n=='tiktok' else 'client_id'):creds(n)[0],'state':key,'scope':OAUTH[n][3],'response_type':'code','redirect_uri':social.CALLBACK}
        if n in ('ga4','youtube'):params.update(access_type='offline',prompt='consent')
        if n=='x':params.update(code_challenge_method='S256',code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='))
        return {'url':OAUTH[n][1]+'?'+urlencode(params)}
    if op=='finish' and n in OAUTH:
        with db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM metric_auth WHERE state=? AND org=? AND email=? AND source=? AND expires>?',(d.get('state'),org,user['email'],n,now)).fetchone()
            if not row:raise HTTPException(400,'Connection expired. Connect again.')
            db.execute('DELETE FROM metric_auth WHERE state=?',(row['state'],))
        target=row['target']
        grant=dict(grant_type='authorization_code',code=d.get('code'),redirect_uri=social.CALLBACK)
        if n=='x':grant['code_verifier']=row['verifier']
        tokens=exchange(n,grant)
        if not tokens.get('refresh_token'):raise HTTPException(400,'Offline access was not granted. Reconnect.')
    elif op=='connect' and n not in OAUTH:
        key=d.get('key')
        if not isinstance(key,str) or not 5<=len(key)<=8192:raise HTTPException(400,'Enter the provider credential.')
        if n=='bing' and (urlsplit(target).scheme not in ('https','http') or not urlsplit(target).hostname):raise HTTPException(400,'Enter the verified Bing website URL.')
        tokens={'access_token':key}
    else:raise HTTPException(404,'Unknown integration operation.')
    report=read(n,tokens['access_token'],target)
    with db:
        db.execute('INSERT OR REPLACE INTO metric_connection VALUES(?,?,?,?,?,?,?,?,NULL)',(org,n,target,social.pack(tokens),secrets.token_hex(16),json.dumps(report),now,now+86400))
    return {'ok':True}

def tick(db):
    now=int(time.time())
    with db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM metric_connection WHERE due<=? ORDER BY due LIMIT 1',(now,)).fetchone()
        if not row:return False
        db.execute('UPDATE metric_connection SET due=? WHERE rev=?',(now+900,row['rev']))
    n=row['source']
    try:
        tokens=social.unpack(row['secret'])
        if n in OAUTH:
            fresh=exchange(n,dict(grant_type='refresh_token',refresh_token=tokens['refresh_token']))
            tokens.update(fresh)
            with db:db.execute('UPDATE metric_connection SET secret=? WHERE rev=?',(social.pack(tokens),row['rev']))
        report=read(n,tokens['access_token'],row['target'])
        with db:db.execute('UPDATE metric_connection SET report=?,checked=?,due=?,problem=NULL WHERE rev=?',(json.dumps(report),now,now+86400,row['rev']))
    except Exception:
        with db:db.execute('UPDATE metric_connection SET problem=?,due=? WHERE rev=?',('Sync failed. Check provider access.',now+21600,row['rev']))
    return True
