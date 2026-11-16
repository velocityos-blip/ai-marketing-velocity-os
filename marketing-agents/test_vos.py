import unittest, tempfile
from pathlib import Path
from unittest.mock import patch
import app, agents

class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        p=patch.object(app,'DATA',Path(self.tmp.name));p.start();self.addCleanup(p.stop)
        p=patch.dict('os.environ',{},clear=True);p.start();self.addCleanup(p.stop)
        app.init();self.c=app.db();self.addCleanup(self.c.close)
        self.a=self.signup('one'); self.b=self.signup('two')
        self.brief=dict(goal='Book ten demos',offer='a scheduling app',audience='salons',budget=100)
    def signup(self,name):
        _,token=app.action(self.c,'signup',dict(company=name,email=name+'@example.test',password='long password here'),None,'local')
        return self.c.execute('select users.*,org.name,org.social,org.tier,sessions.hash from users join org on users.org=org.id join sessions on sessions.user=users.id where hash=?',(app.digest(token),)).fetchone()
    def call(self,path,d,user=None): return app.action(self.c,path,d,user or self.a,'local')
    def test_tenant_and_approval(self):
        self.call('run',self.brief)
        r=app.state(self.c,self.a)['runs'][0];self.assertEqual(len(r['messages']),4)
        self.assertEqual(app.state(self.c,self.b)['runs'],[])
        with self.assertRaises(app.Problem):self.call('approve',dict(id=r['id'],draft='secret'),self.b)
        with self.assertRaises(app.Problem):self.call('publish',dict(id=r['id']))
        editor=dict(self.a);editor['role']='editor'
        with self.assertRaises(app.Problem):self.call('approve',dict(id=r['id'],draft='abc'),editor)
        self.call('approve',dict(id=r['id'],draft='Reviewed.'))
        with patch.object(app,'request',side_effect=[{'acct':'salon'},{'url':'https://mastodon.social/@salon/123'}]) as api:
            self.call('connect',dict(token='test'))
            self.call('publish',dict(id=r['id'],social='salon'))
            self.assertEqual(api.call_args.args[2]['status'],'Reviewed.')
            with self.assertRaises(app.Problem):self.call('publish',dict(id=r['id'],social='salon'))
            self.assertEqual(api.call_count,2)
    def test_quota_and_failure(self):
        with patch.object(app,'generate',side_effect=[('demo','assessment'),RuntimeError()]):
            with self.assertRaises(app.Problem):self.call('run',self.brief)
        r=app.state(self.c,self.a)['runs'][0];self.assertEqual((r['status'],len(r['messages'])),('failed',1))
        with patch.dict(app.LIMITS,starter=1):
            with self.assertRaises(app.Problem):self.call('run',self.brief)
            self.call('run',self.brief,self.b)
    def test_handoffs(self):
        seen=[]
        def generator(role,brief,history):
            seen.append([m['role'] for m in history]);return 'test','output '+role
        with patch.object(app,'generate',side_effect=generator):self.call('run',self.brief)
        self.assertEqual(seen,[list(agents.ROLES)[:i] for i in range(4)])
    def test_native_providers(self):
        for provider,reply in [('openai',{'choices':[{'message':{'content':'plan'}}]}),('anthropic',{'content':[{'type':'text','text':'plan'}]}),('gemini',{'candidates':[{'content':{'parts':[{'text':'plan'}]}}]})]:
            with self.subTest(provider=provider),patch.dict('os.environ',{'VOS_CMO':provider,provider.upper()+'_MODEL':'model',provider.upper()+'_API_KEY':'key'}),patch.object(agents,'request',return_value=reply) as req:
                self.assertEqual(agents.generate('CMO',self.brief,[{'body':'prior-output'}])[1],'plan')
                self.assertIn('prior-output',str(req.call_args.args[2]))
if __name__=='__main__': unittest.main()
