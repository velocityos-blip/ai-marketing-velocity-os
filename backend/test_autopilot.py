from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from campaign_routes import engine, Autopilot

class AutomationTests(unittest.TestCase):
    def test_scheduled_delivery_pause_and_no_duplicate_after_save(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, 'DATA', Path(tmp)), patch('autopilot.Thread.start'), patch('autopilot.time.time',return_value=1000):
            engine.init()
            pilot=Autopilot(engine)
            pilot.start()
            with closing(engine.db()) as db, db:
                oid=db.execute("INSERT INTO org(name,social,token) VALUES('Flower shop','flowers','test')").lastrowid
                db.commit()
                admin=dict(org=oid,name='Flower shop',role='admin',tier='starter')
                profile=dict(goal='Book 10 demos',audience='Florists',offer='Inventory software',budget=0,cadence='weekly',destination='flowers')
                with self.assertRaises(engine.Problem):
                    pilot.configure(db,{**admin,'role':'editor'},profile)
                pilot.configure(db,admin,profile)
                def generate(role,brief,history):
                    return 'mock', 'READY\nReviewed.' if role=='Analyst' else 'A short post'
                with patch.object(engine,'generate',side_effect=generate), patch.object(engine,'request',return_value={'url':'https://example.org/post'}) as publish:
                    self.assertTrue(pilot.tick())
                    self.assertEqual(publish.call_count,1)
                    self.assertEqual(db.execute('SELECT status FROM runs').fetchone()[0],'published')
                    pilot.configure(db,admin,profile)
                    self.assertFalse(pilot.tick())
                    self.assertEqual(pilot.state(db,oid)['due'],1000+7*86400)
                    db.execute('UPDATE autopilot SET due=0')
                    db.commit()
                    with patch.object(engine,'generate',return_value=('mock','HOLD')):
                        self.assertTrue(pilot.tick())
                    self.assertEqual(publish.call_count,1)
                    db.execute('UPDATE autopilot SET due=0, enabled=0')
                    db.commit()
                    self.assertFalse(pilot.tick())
