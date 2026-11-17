import json
import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from unittest.mock import patch
from fastapi import HTTPException
from campaign_routes import engine,Autopilot
import search_audit
import site_crawl


class SearchAuditFlow(unittest.TestCase):
    def test_google_crawl_feedback_loop(self):
        env={"GSC_CLIENT_ID":"client","GSC_CLIENT_SECRET":"secret","JWT_SECRET_KEY":"fixture"}
        def provider(method,url,**kw):
            if url==search_audit.TOKEN:
                if kw["data"]["grant_type"]=="authorization_code":return {"access_token":"temporary","refresh_token":"offline"}
                self.assertEqual(kw["data"]["refresh_token"],"offline")
                return {"access_token":"renewed"}
            if url==search_audit.API:return {"siteEntry":[{"siteUrl":"sc-domain:example.org","permissionLevel":"siteOwner"}]}
            self.assertEqual(kw["headers"]["Authorization"],"Bearer renewed")
            return {"rows":[{"keys":["https://example.org/","flower stock"],"clicks":7,"impressions":32}]}
        def page(url):
            if url.endswith("robots.txt"):return 200,{},b"User-agent: *\nDisallow: /private",False
            self.assertNotIn("private",url)
            return 200,{"Content-Type":"text/html"},b'<title>Flowers</title><img src="x"><a href="/private">Private</a>',False
        with tempfile.TemporaryDirectory() as tmp,patch.object(engine,"DATA",Path(tmp)),patch.dict(os.environ,env),patch("autopilot.Thread.start"),patch.object(search_audit,"google",side_effect=provider),patch.object(site_crawl,"fetch",side_effect=page):
            engine.init()
            pilot=Autopilot(engine)
            pilot.start()
            with closing(engine.db()) as db:
                with db: oid=db.execute("INSERT INTO org(name) VALUES('Test')").lastrowid
                user=dict(org=oid,email="admin@example.org",role="admin",tier="starter",name="Test")
                search_audit.action(db,user,"save",{"site":"example.org"})
                auth=search_audit.action(db,user,"start",{})
                key=parse_qs(urlsplit(auth["url"]).query)["state"][0]
                args={"state":key,"code":"test-code"}
                with self.assertRaises(HTTPException):
                    search_audit.action(db,{**user,"email":"other@example.org"},"finish",args)
                search_audit.action(db,user,"finish",args)
                with self.assertRaises(HTTPException):search_audit.action(db,user,"finish",args)
                pilot.configure(db,user,dict(goal="Generate demos",offer="Software",audience="Florists",budget=0,cadence="once"))
                evidence=[]
                def agent(role,brief,history):
                    evidence.append(brief["website_audit"])
                    return "test","READY" if role=="Analyst" else "Draft"
                with patch.object(engine,"generate",side_effect=agent):self.assertTrue(pilot.tick())
                self.assertEqual(len(evidence),4)
                report=evidence[0]
                self.assertEqual(report["search_console"]["rows"][0]["clicks"],7)
                self.assertEqual(report["crawl"]["skipped"],1)
                self.assertIn("1 images missing alt attributes",report["crawl"]["pages"][0]["findings"])
                self.assertEqual(json.loads(db.execute("SELECT brief FROM runs").fetchone()[0])["website_audit"],report)
                search_audit.action(db,user,"save",{"site":"another.example.org"})
                self.assertIsNone(search_audit.state(db,oid)["property"])
                self.assertIsNone(search_audit.state(db,oid)["report"])
