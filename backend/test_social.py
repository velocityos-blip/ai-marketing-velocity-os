import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit

import httpx
from fastapi import HTTPException
import social
from campaign_routes import engine,Autopilot


class SocialFlow(unittest.TestCase):
    def test_connect_publish_measure_and_adapt(self):
        def provider(method,url,**kwargs):
            data={}
            headers={}
            if url.endswith("accessToken") or url.endswith("access_token"):
                data={"access_token":"provider-test-token","expires_in":60000}
            elif url.endswith("organizationAcls"):
                data={"elements":[{"organization":"urn:li:organization:123"}]}
            elif "/organizations/" in url:
                data={"localizedName":"Test studio"}
            elif url.endswith("me/accounts"):
                data={"data":[{"name":"Studio","id":"page","access_token":"page-test-token","instagram_business_account":{"id":"ig","username":"studio"}}]}
            elif url.endswith("/posts"):
                headers={"x-restli-id":"urn:li:share:123"}
            elif url.endswith("/feed") or url.endswith("/media_publish"):
                data={"id":"post"}
            elif url.endswith("/media"):
                key=kwargs["data"]["image_url"].rsplit("/",1)[1]
                self.assertTrue(db.execute("SELECT jpeg FROM social_media WHERE key=?",(key,)).fetchone()[0].startswith(b'\xff\xd8'))
                data={"id":"container"}
            elif url.endswith("/container"):
                data={"status_code":"FINISHED"}
            elif "organizationalEntityShareStatistics?" in url:
                data={"elements":[{"totalShareStatistics":{"impressionCount":20}}]}
            elif url.endswith("/insights"):
                data={"data":[{"name":"reach","values":[{"value":11}]}]}
            elif url.endswith("/post"):
                data={"reactions":{"summary":{"total_count":4}}}
            else:
                raise AssertionError(url)
            return httpx.Response(200,json=data,headers=headers)
        env={key:"test" for key in ("META_CLIENT_ID","META_CLIENT_SECRET","LINKEDIN_CLIENT_ID","LINKEDIN_CLIENT_SECRET","JWT_SECRET_KEY")}
        with tempfile.TemporaryDirectory() as folder,patch.object(engine,"DATA",Path(folder)),patch.dict(os.environ,env),patch("autopilot.Thread.start"),patch.object(social,"request",side_effect=provider):
            engine.init()
            pilot=Autopilot(engine)
            pilot.start()
            with closing(engine.db()) as db:
                with db:
                    org=db.execute("INSERT INTO org(name) VALUES('Test studio')").lastrowid
                user=dict(org=org,role="admin",email="owner@example.org",name="Test studio",tier="starter")
                for n in social.NETWORKS:
                    start=social.auth(db,user,"start",dict(network=n))
                    state=parse_qs(urlsplit(start["url"]).query)["state"][0]
                    args=dict(network=n,state=state,code="authorized")
                    with self.assertRaises(HTTPException):
                        social.auth(db,{**user,"org":org+1},"finish",args)
                    choice=social.auth(db,user,"finish",args)["choices"][0]
                    social.auth(db,user,"select",dict(network=n,key=choice["key"]))
                    with self.assertRaises(HTTPException):
                        social.auth(db,user,"finish",args)
                pilot.configure(db,user,dict(goal="Book demos",offer="Software",audience="Florists",budget=0,cadence="weekly"))
                briefs=[]
                def generate(role,brief,history):
                    if role=="CMO": briefs.append(brief.copy())
                    return "test","READY\nReviewed" if role=="Analyst" else "A test campaign."
                with patch.object(engine,"generate",side_effect=generate):
                    self.assertTrue(pilot.tick())
                    posts=social.history(db,org)
                    self.assertEqual([r["status"] for r in posts],["Published"]*3)
                    with db: db.execute("UPDATE social_post SET due=0")
                    for _ in range(3): self.assertTrue(pilot.tick())
                    with db: db.execute("UPDATE autopilot SET due=0")
                    self.assertTrue(pilot.tick())
                    results=briefs[-1]["measured_prior_posts"]
                    self.assertEqual({r["network"] for r in results},set(social.NETWORKS))
                    self.assertTrue(all(r["metrics"] and r["draft"] for r in results))
