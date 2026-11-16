"""VOS single-process, self-hosted pilot."""
import hashlib, hmac, json, os, re, secrets, sqlite3, time
from contextlib import closing
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
if __package__:
    from .agents import generate, request, ROLES
else:
    from agents import generate, request, ROLES

ROOT = Path(__file__).resolve().parent
DATA = Path(os.getenv('VOS_DATA', ROOT/'private'))
LIMITS = {'starter':10, 'growth':100}
ORIGIN = os.getenv('VOS_ORIGIN','http://127.0.0.1:8787')
class Problem(Exception):
    def __init__(self, msg, status=400): self.status=status; super().__init__(msg)

def db():
    c=sqlite3.connect(DATA/'vos.sqlite', timeout=10)
    c.row_factory=sqlite3.Row
    c.execute('pragma foreign_keys=on')
    return c

def init():
    DATA.mkdir(mode=0o700,parents=True,exist_ok=True)
    with closing(db()) as c:
        c.executescript("""
        pragma journal_mode=WAL;
        create table if not exists org(id integer primary key,name text not null,tier text default 'starter',social text,token text);
        create table if not exists users(id integer primary key,org integer references org,email text unique,pw text,role text);
        create table if not exists sessions(hash text primary key,user integer references users,expires integer);
        create table if not exists runs(id integer primary key,org integer references org,created text default current_timestamp,brief text,status text,messages text default '[]',draft text default '',receipt text);
        create index if not exists runs_org on runs(org,created);
        create table if not exists attempts(ip text primary key,start integer,n integer);
        update runs set status='interrupted' where status='working';
        update runs set status='check channel' where status='publishing';
        """)
def field(d,k,n):
    v=d.get(k)
    if not isinstance(v,str) or not v.strip() or len(v)>n: raise Problem(f'Check {k} (1–{n} characters).')
    return v.strip()
def password(p,s): return hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def account(d):
    email=field(d,'email',240).lower(); pw=d.get('password')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or not isinstance(pw,str) or not 12<=len(pw)<=256: raise Problem('Enter an email and a password of 12–256 characters.')
    salt=secrets.token_hex(16)
    return email,salt+':'+password(pw,salt)
def admin(u):
    if u['role']!='admin': raise Problem('Company admin required.',403)
def action(c,path,d,u,ip,*,scheduled=False,previous="",feedback=None,schedule_version=None):
    if path in ('signup','login'):
        now=int(time.time())
        with c:
            c.execute('delete from attempts where start<?',(now-600,))
            c.execute('insert into attempts values(?,?,1) on conflict(ip) do update set n=n+1',(ip,now))
            n=c.execute('select n from attempts where ip=?',(ip,)).fetchone()[0]
        if n>25: raise Problem('Try again in ten minutes.',429)
        if path=='signup':
            name=field(d,'company',80); email,pw=account(d)
            with c:
                oid=c.execute('insert into org(name) values(?)',(name,)).lastrowid
                uid=c.execute("insert into users(org,email,pw,role) values(?,?,?,'admin')",(oid,email,pw)).lastrowid
        else:
            email=field(d,'email',240).lower(); p=d.get('password','')
            if not isinstance(p,str) or len(p)>256: raise Problem('Invalid credentials.',401)
            row=c.execute('select id,pw from users where email=?',(email,)).fetchone()
            salt,expected=(row['pw'] if row else '00'*16+':'+'00'*64).split(':')
            if not hmac.compare_digest(password(p,salt),expected) or not row: raise Problem('Invalid credentials.',401)
            uid=row['id']
        token=secrets.token_urlsafe(32)
        with c:
            c.execute('delete from sessions where expires<?',(now,))
            c.execute('insert into sessions values(?,?,?)',(digest(token),uid,now+86400))
        return {'ok':True},token
    if not u: raise Problem('Sign in to continue.',401)
    oid=u['org']
    if path=='logout':
        with c: c.execute('delete from sessions where hash=?',(u['hash'],))
    elif path=='member':
        admin(u); email,pw=account(d)
        with c: c.execute("insert into users(org,email,pw,role) values(?,?,?,'editor')",(oid,email,pw))
    elif path=='connect':
        admin(u); token=field(d,'token',500)
        try:
            social=request('https://mastodon.social/api/v1/accounts/verify_credentials',{'Authorization':'Bearer '+token})['acct']
        except Exception: raise Problem('Could not verify that mastodon.social account.')
        with c: c.execute('update org set social=?,token=? where id=?',(social,token,oid))
    elif path=='disconnect':
        admin(u)
        with c: c.execute('update org set social=null,token=null where id=?',(oid,))
    elif path=='run':
        brief={k:field(d,k,n) for k,n in [('goal',600),('offer',200),('audience',200)]}
        budget=d.get('budget')
        if type(budget) is not int or not 0<=budget<=100000000: raise Problem('Budget must be a nonnegative whole USD amount.')
        brief.update(budget=budget,company=u['name'],channel='Organic social')
        if scheduled and feedback:
            brief['measured_prior_posts'] = [{k:row[k] for k in ('network','draft','metrics','created')} for row in feedback]
        with c:
            c.execute('begin immediate')
            used=c.execute("select count(*) from runs where org=? and created>=date('now','start of month')",(oid,)).fetchone()[0]
            if used>=LIMITS[u['tier']]: raise Problem('Monthly run allowance reached.',429)
            rid=c.execute("insert into runs(org,brief,status) values(?,?,'working')",(oid,json.dumps(brief))).lastrowid
        if scheduled:
            brief['automated_review'] = True
            if previous: brief['previous_post_to_avoid_repeating'] = previous
        history=[]
        try:
            for role in ROLES:
                model,body=generate(role,brief,history)
                history.append(dict(role=role,model=model,body=body))
                with c: c.execute('update runs set messages=? where id=?',(json.dumps(history),rid))
            with c: c.execute("update runs set status='review',draft=? where id=?",(history[2]['body'],rid))
        except Exception:
            with c: c.execute("update runs set status='failed' where id=?",(rid,))
            raise Problem('Agent run stopped. Check provider settings; completed handoffs are saved.',502)
        return {'ok':True,'id':rid},None
    elif path in ('approve','publish'):
        admin(u); rid=d.get('id')
        with c:
            c.execute('begin immediate')
            row=c.execute('select * from runs where id=? and org=?',(rid,oid)).fetchone()
            if not row: raise Problem('Run not found.',404)
            if path=='approve':
                if row['status']!='review': raise Problem('Draft is not awaiting approval.',409)
                c.execute("update runs set draft=?,status='approved' where id=?",(field(d,'draft',500),rid))
            else:
                if row['status']!='approved': raise Problem('An approved, unpublished draft is required.',409)
                if schedule_version is not None and not c.execute("select 1 from autopilot where org=? and version=? and enabled=1 and destination=?",(oid,schedule_version,d.get('social'))).fetchone():
                    raise Problem('Automatic publishing settings changed.',409)
                channel=c.execute('select token,social from org where id=?',(oid,)).fetchone()
                if not channel['token'] or channel['social']!=d.get('social'): raise Problem('Check the destination and try again.',409)
                c.execute("update runs set status='publishing' where id=?",(rid,))
        if path=='publish':
            try:
                result=request('https://mastodon.social/api/v1/statuses',{'Authorization':'Bearer '+channel['token'],'Idempotency-Key':f'vos-{oid}-{rid}-{digest(row["created"])[:12]}'},{'status':row['draft'],'visibility':'public'})
                receipt=str(result['url'])
            except Exception as e:
                state='approved' if isinstance(e,HTTPError) and 400<=e.code<500 else 'check channel'
                with c: c.execute('update runs set status=? where id=?',(state,rid))
                raise Problem('Delivery not confirmed. Inspect the channel before retrying.',502)
            with c: c.execute("update runs set status='published',receipt=? where id=?",(receipt,rid))
    else: raise Problem('Unknown action.',404)
    return {'ok':True},None

def state(c,u):
    if not u: return {'signedIn':False}
    rows=c.execute('select id,created,brief,status,messages,draft,receipt from runs where org=? order by id desc limit 50',(u['org'],))
    runs=[{**dict(r),'brief':json.loads(r['brief']),'messages':json.loads(r['messages'])} for r in rows]
    used=c.execute("select count(*) from runs where org=? and created>=date('now','start of month')",(u['org'],)).fetchone()[0]
    return dict(signedIn=True,company=u['name'],companyId=u['org'],email=u['email'],role=u['role'],tier=u['tier'],limit=LIMITS[u['tier']],used=used,social=u['social'],runs=runs)

class Handler(BaseHTTPRequestHandler):
    def reply(self,status,body,content='application/json',cookie=None):
        b=json.dumps(body).encode() if content=='application/json' else body
        self.send_response(status)
        for k,v in {'Content-Type':content,'Content-Length':str(len(b)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items(): self.send_header(k,v)
        if cookie is not None:
            self.send_header('Set-Cookie','vos='+cookie+'; HttpOnly; SameSite=Strict; Path=/; Max-Age='+('86400' if cookie else '0')+('; Secure' if ORIGIN.startswith('https:') else ''))
        self.end_headers(); self.wfile.write(b)
    def serve(self,post):
        try:
            if not post and self.path in ('/','/ui.js','/style.css'):
                name,typ={'/':('index.html','text/html; charset=utf-8'),'/ui.js':('ui.js','text/javascript'),'/style.css':('style.css','text/css')}[self.path]
                return self.reply(200,(ROOT/name).read_bytes(),typ)
            with closing(db()) as c:
                cookies=SimpleCookie(self.headers.get('Cookie',''))
                raw=cookies['vos'].value if 'vos' in cookies else ''
                u=c.execute('select users.*,org.name,org.social,org.tier,sessions.hash from sessions join users on users.id=sessions.user join org on org.id=users.org where sessions.hash=? and expires>?',(digest(raw),time.time())).fetchone()
                if not post and self.path=='/api/state': return self.reply(200,state(c,u))
                if not post or not self.path.startswith('/api/'): raise Problem('Not found.',404)
                if self.headers.get('Origin')!=ORIGIN or self.headers.get_content_type()!='application/json': raise Problem('Invalid request origin or type.',403)
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=16384: raise Problem('Invalid request size.',413)
                d=json.loads(self.rfile.read(size))
                if not isinstance(d,dict): raise Problem('Object required.')
                res,token=action(c,self.path[5:],d,u,self.client_address[0])
                self.reply(200,res,cookie='' if self.path=='/api/logout' else token)
        except Problem as e: self.reply(e.status,{'error':str(e)})
        except sqlite3.IntegrityError: self.reply(409,{'error':'Account could not be created.'})
        except (ValueError,TypeError): self.reply(400,{'error':'Invalid input.'})
        except Exception: self.reply(500,{'error':'Unexpected server error.'})
    def do_GET(self): self.serve(False)
    def do_POST(self): self.serve(True)

if __name__=='__main__':
    os.umask(0o077); init()
    print('VOS available at '+ORIGIN,flush=True)
    ThreadingHTTPServer(('127.0.0.1',int(os.getenv('VOS_PORT','8787'))),Handler).serve_forever()
