import os
import tempfile
import unittest
from unittest.mock import patch

import mongomock
from fastapi.testclient import TestClient


class DashboardTests(unittest.TestCase):
    def test_sign_in_workspace_campaign_and_approval(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
            "VOS_DATA": folder, "MONGO_URL": "mongodb://localhost/vos_test",
            "JWT_SECRET_KEY": "local-test-only-signing-key-more-than-32-bytes",
            "VOS_CMO":"local","VOS_DIGITAL_MARKETING":"local","VOS_CONTENT":"local","VOS_ANALYST":"local"
        }), patch("pymongo.MongoClient", mongomock.MongoClient):
            import server
            with TestClient(server.app) as client:
                def signup(company):
                    body = {"full_name":company,"company_name":company,"email":company+"@example.org","password":"integration-test-password"}
                    self.assertEqual(client.post("/api/auth/register",json=body).status_code,200)
                    login = client.post("/api/auth/login",json=body)
                    self.assertEqual(login.status_code,200)
                    return {"Authorization":"Bearer "+login.json()["access_token"],"X-VOS-Client":"dashboard"}
                route = "/api/campaign-agents"
                self.assertEqual(client.get(route).status_code,401)
                owner, other = signup("Orchid"), signup("Linden")
                brief = {"goal":"Book qualified demos","audience":"Florists","offer":"Inventory software","budget":20}
                self.assertEqual(client.post(route+"/run",headers=owner,json=brief).status_code,200)
                run = client.get(route,headers=owner).json()["runs"][0]
                self.assertEqual([m["role"] for m in run["messages"]],["CMO","Digital Marketing","Content","Analyst"])
                self.assertEqual(client.get(route,headers=other).json()["runs"],[])
                payload = {"id":run["id"],"draft":"Approved copy"}
                self.assertEqual(client.post(route+"/approve",headers=other,json=payload).status_code,404)
                user = client.get("/api/auth/me",headers=owner).json()
                tasks_url = "/api/tasks/workspace/" + user["workspace_id"]
                task = client.post("/api/tasks", headers=owner, json={"title": "Review post"}).json()
                self.assertEqual(client.get(tasks_url, headers=owner).json()[0]["task_id"], task["task_id"])
                self.assertEqual(client.get(tasks_url, headers=other).status_code, 403)
                self.assertEqual(client.put("/api/tasks/" + task["task_id"], headers=other, json={"status":"done"}).status_code, 404)
                server.team_members_collection.update_one({"user_id":user["user_id"]},{"$set":{"role":"member"}})
                self.assertEqual(client.post(route+"/approve",headers=owner,json=payload).status_code,403)
                server.team_members_collection.update_one({"user_id":user["user_id"]},{"$set":{"role":"owner"}})
                self.assertEqual(client.post(route+"/approve",headers=owner,json=payload).status_code,200)
                self.assertEqual(client.get(route,headers=owner).json()["runs"][0]["status"],"approved")
                server.team_members_collection.delete_one({"user_id":user["user_id"]})
                self.assertEqual(client.get(route,headers=owner).status_code,403)

if __name__ == "__main__":
    unittest.main()
