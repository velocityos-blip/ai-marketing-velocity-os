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
    def test_unsupported_claim_is_revised_with_same_unknown_evidence(self):
        def agent(role, brief, current):
            fixing = 'review_feedback' in brief
            self.assertEqual(brief['channel_evidence']['site_visits_by_channel'], 'unknown')
            if fixing:
                self.assertIn('zero known organic social visits', brief['review_feedback'])
                self.assertFalse(any('zero known' in m['body'] for m in current))
            outputs = {'CMO': 'Baseline unknown.' if fixing else 'Baseline is zero known organic social visits.',
                       'Digital Marketing': 'Measure tagged clicks after posting.',
                       'Content': 'Revised private post' if fixing else 'Initial post', 'Analyst': 'READY'}
            return 'test', outputs[role]
        with patch.object(app,'generate',side_effect=agent):
            self.call('run',self.brief)
        run=app.state(self.c,self.a)['runs'][0]
        self.assertEqual(len(run['messages']),8)
        self.assertTrue(run['messages'][3]['body'].startswith('HOLD'))
        self.assertEqual(run['messages'][-1]['body'],'READY')
        self.assertEqual(run['draft'],'Revised private post')

    def test_unresolved_claim_stays_held_after_two_revisions(self):
        with patch.object(app,'generate',side_effect=lambda role,*args: ('test','READY' if role=='Analyst' else 'Reported 0 visits.')):
            self.call('run',self.brief)
        run=app.state(self.c,self.a)['runs'][0]
        self.assertEqual(len(run['messages']),12)
        self.assertTrue(run['messages'][-1]['body'].startswith('HOLD'))

    def test_cmo_assigns_specialist_and_controls_final_release(self):
        import json
        def agent(role,brief,history):
            if brief.get('cmo_planning'):
                return 'planner',json.dumps({'strategy':'Test a specific audience.','tasks':[
                    {'type':'design','provider':'gemini','instruction':'Propose a visual brief.'},
                    {'type':'implementation','provider':'unavailable','instruction':'Specify tracking.'}]})
            if brief.get('cmo_signoff'):
                return 'planner','READY\nCollect tagged clicks.'
            return 'agent', 'READY' if role=='Analyst' else 'Campaign handoff'
        with patch.object(app,'generate',side_effect=agent),patch.object(app,'available_providers',return_value=['openai','gemini','anthropic']):
            self.call('run',self.brief)
        run=app.state(self.c,self.a)['runs'][0]
        self.assertEqual([m['role'] for m in run['messages']],['CMO','Design','Implementation','Digital Marketing','Content','Analyst','CMO'])
        self.assertEqual([t['provider'] for t in run['messages'][0]['assignments']],['gemini','anthropic','gemini','openai'])
        self.assertTrue(run['messages'][-1]['decision'])
        self.assertIsNone(run['receipt'])

    def test_native_providers(self):
        for provider,reply in [('openai',{'choices':[{'message':{'content':'plan'}}]}),('anthropic',{'content':[{'type':'text','text':'plan'}]}),('gemini',{'candidates':[{'content':{'parts':[{'text':'plan'}]}}]})]:
            with self.subTest(provider=provider),patch.dict('os.environ',{'VOS_CMO':provider,provider.upper()+'_MODEL':'model',provider.upper()+'_API_KEY':'key'}),patch.object(agents,'request',return_value=reply) as req:
                self.assertEqual(agents.generate('CMO',self.brief,[{'body':'prior-output'}])[1],'plan')
                self.assertIn('prior-output',str(req.call_args.args[2]))
if __name__=='__main__': unittest.main()
