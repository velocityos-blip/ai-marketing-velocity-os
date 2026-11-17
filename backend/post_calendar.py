"""Persist one independently editable dispatch per approved destination."""
import time
import social

DAY = 86400


def setup(db):
    db.execute("""CREATE TABLE IF NOT EXISTS scheduled_post(
        id INTEGER PRIMARY KEY, org INTEGER NOT NULL, run INTEGER REFERENCES runs,
        network TEXT NOT NULL, account TEXT, channel_revision TEXT, version INTEGER,
        due INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'scheduled',
        UNIQUE(run,network))""")
    db.execute("CREATE INDEX IF NOT EXISTS scheduled_post_due ON scheduled_post(state,due)")
    db.execute("UPDATE scheduled_post SET state='check delivery' WHERE state='sending'")


def entries(db,org):
    return [dict(r) for r in db.execute("""SELECT p.id,p.run,p.network,p.account,p.due,p.state,r.draft
        FROM scheduled_post p JOIN runs r ON r.id=p.run WHERE p.org=? ORDER BY p.due,p.id""",(org,))]


def enqueue(db,job,run,channels):
    targets=[(c['network'],c['account'],c['revision']) for c in channels]
    if job['destination']:
        targets.append(('mastodon',job['destination'],None))
    if not targets:
        targets.append(('private',None,None))
    with db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM autopilot WHERE org=? AND version=? AND enabled=1',(job['org'],job['version'])).fetchone():
            return False
        due=int(time.time())+DAY
        db.executemany("""INSERT OR IGNORE INTO scheduled_post(org,run,network,account,channel_revision,version,due)
            VALUES(?,?,?,?,?,?,?)""",[(job['org'],run['id'],n,a,v,job['version'],due) for n,a,v in targets])
        if targets[0][0]!='private':
            db.execute("UPDATE runs SET status='scheduled' WHERE id=?",(run['id'],))
    return True


def change(db,engine,user,op,payload):
    engine.admin(user)
    due=payload.get('due')
    if op!='cancel-post' and (type(due) is not int or not int(time.time())<due<253402300799):
        raise engine.Problem('Choose a future date and time.')
    with db:
        db.execute('BEGIN IMMEDIATE')
        if op=='plan-private':
            run=db.execute("SELECT * FROM runs WHERE org=? AND id=? AND status='review' AND draft!=''",(user['org'],payload.get('run'))).fetchone()
            if not run:
                raise engine.Problem('Select an available private draft.',409)
            if not db.execute("""INSERT OR IGNORE INTO scheduled_post(org,run,network,due) VALUES(?,?,'private',?)""",(user['org'],run['id'],due)).rowcount:
                raise engine.Problem('This draft already has a calendar entry.',409)
        else:
            row=db.execute("SELECT * FROM scheduled_post WHERE id=? AND org=? AND state='scheduled' AND due=?",(payload.get('id'),user['org'],payload.get('previous_due'))).fetchone()
            if not row:
                raise engine.Problem('The post changed or is already being delivered. Refresh the calendar.',409)
            if op=='cancel-post':
                db.execute("UPDATE scheduled_post SET state='cancelled' WHERE id=?",(row['id'],))
                summarize(db,row['run'])
            else:
                db.execute("UPDATE scheduled_post SET due=? WHERE id=?",(due,row['id']))
    return {'ok':True}


def summarize(db,run):
    states=[r[0] for r in db.execute("SELECT state FROM scheduled_post WHERE run=? AND network!='private'",(run,))]
    if states:
        status=('scheduled' if any(s in ('sending','scheduled') for s in states) else
                'published' if all(s=='published' for s in states) else
                'partially published' if 'published' in states else
                'cancelled' if all(s=='cancelled' for s in states) else 'check channel')
        db.execute('UPDATE runs SET status=? WHERE id=?',(status,run))


def dispatch(db,engine):
    with db:
        db.execute('BEGIN IMMEDIATE')
        p=db.execute("SELECT * FROM scheduled_post WHERE state='scheduled' AND due<=? ORDER BY due,id LIMIT 1",(int(time.time()),)).fetchone()
        if not p:
            return False
        job=db.execute("SELECT a.*,o.name,o.social,o.token FROM autopilot a JOIN org o ON o.id=a.org WHERE a.org=? AND a.enabled=1 AND a.version=?",(p['org'],p['version'])).fetchone()
        run=db.execute('SELECT * FROM runs WHERE id=? AND org=?',(p['run'],p['org'])).fetchone()
        ch=db.execute("SELECT * FROM social_channel WHERE org=? AND network=? AND account=? AND revision=?",(p['org'],p['network'],p['account'],p['channel_revision'])).fetchone()
        if p['network']=='private':
            state='private draft'
        elif not job or not run or (p['network']=='mastodon' and not (job['destination']==job['social']==p['account'] and job['token'])) or (p['network']!='mastodon' and not ch):
            state='cancelled'
        else:
            state='sending'
        db.execute('UPDATE scheduled_post SET state=? WHERE id=?',(state,p['id']))
        summarize(db,p['run'])
    if state!='sending':
        return True
    try:
        if ch:
            social.deliver(db,job,run,[ch])
            sent=db.execute('SELECT remote FROM social_post WHERE run=? AND network=?',(p['run'],p['network'])).fetchone()
            state='published' if sent and sent[0] else 'check delivery'
        else:
            result=engine.request('https://mastodon.social/api/v1/statuses',
                {'Authorization':'Bearer '+job['token'],'Idempotency-Key':f"vos-calendar-{p['id']}-{p['run']}"},
                {'status':run['draft'],'visibility':'public'})
            with db:
                db.execute('UPDATE runs SET receipt=? WHERE id=?',(result['url'],p['run']))
            state='published'
    except Exception:
        state='check delivery'
    with db:
        db.execute('UPDATE scheduled_post SET state=? WHERE id=?',(state,p['id']))
        summarize(db,p['run'])
    return True
