import os
import sqlite3
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
from fastapi import HTTPException
import marketing_metrics as mm

class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close);mm.setup(self.db)
        keys=patch.dict(os.environ,dict(JWT_SECRET_KEY='test',GSC_CLIENT_ID='id',GSC_CLIENT_SECRET='secret'))
        keys.start();self.addCleanup(keys.stop)
        self.user=dict(org=1,email='admin@example.test')

    def test_consent_bound_to_workspace_and_offline_refresh(self):
        data=dict(source='ga4',target='12345')
        url=mm.action(self.db,self.user,'start',data)['url']
        state=parse_qs(urlsplit(url).query)['state'][0]
        finish=dict(source='ga4',state=state,code='fixture')
        with self.assertRaises(HTTPException):mm.action(self.db,{**self.user,'org':2},'finish',finish)
        with patch.object(mm,'fetch',side_effect=[{'access_token':'a','refresh_token':'private-refresh-token'},{'rows':[]}]):
            mm.action(self.db,self.user,'finish',finish)
        row=self.db.execute('select * from metric_connection').fetchone()
        self.assertNotIn('private-refresh-token',row['secret'])
        self.assertFalse(mm.state(self.db,2)[0]['connected'])
        self.assertEqual(mm.state(self.db,1)[0]['report']['metrics'],{})
        self.db.execute('update metric_connection set due=0');self.db.commit()
        with patch.object(mm,'fetch',side_effect=[{'access_token':'b'},{'rows':[{'metricValues':[{'value':'0'},{'value':'10'}]}]}]):
            self.assertTrue(mm.tick(self.db))
        self.assertEqual(mm.state(self.db,1)[0]['report']['metrics'],{'activeUsers':0,'sessions':10})
        with self.assertRaises(HTTPException):mm.action(self.db,self.user,'finish',finish)
        mm.action(self.db,self.user,'disconnect',data)
        self.assertFalse(mm.state(self.db,1)[0]['connected'])

    def test_source_adapters(self):
        cases=[
            ('bing',[{'d':[{'Date':'/Date(1000)/','Clicks':0,'Impressions':12}]}],{'Clicks':0,'Impressions':12}),
            ('clarity',[[{'metricName':'Traffic','information':[{'totalSessionCount':'3'}]}]],{'totalSessionCount':3}),
            ('youtube',[{'items':[{'snippet':{'title':'Studio'},'statistics':{'viewCount':'10','subscriberCount':'4','hiddenSubscriberCount':True}}]}],{'viewCount':10}),
            ('x',[{'data':{'username':'studio','public_metrics':{'followers_count':2}}}],{'followers_count':2}),
            ('tiktok',[{'data':{'user':{'display_name':'Studio','open_id':'123','likes_count':5}}}],{'likes_count':5}),
            ('pinterest',[{'username':'studio','pin_count':4}],{'pin_count':4}),
            ('threads',[{'id':'123','username':'studio'},{'data':[{'name':'followers_count','total_value':{'value':6}}]}],{'followers_count':6})]
        for n,fixtures,metrics in cases:
            with self.subTest(n=n),patch.object(mm,'fetch',side_effect=fixtures):
                self.assertEqual(mm.read(n,'token','https://example.test/')['metrics'],metrics)
