"""Use the existing VOS identity and team directory for all agent operations."""
from contextlib import closing
from importlib import import_module
from pathlib import Path
import sys

import post_calendar
import search_audit
import social
import time
from fastapi.responses import Response
from autopilot import Autopilot
from fastapi import Depends, HTTPException, Request

# The agent package is shared with the self-hosted edition in this repository.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
engine = import_module("marketing-agents.app")
ACTIONS = {"run", "approve", "publish", "connect", "disconnect"}


def company_context(connection, workspace, member, email):
    with connection:
        connection.execute("begin immediate")
        row = connection.execute(
            "select org from vos_workspace where workspace_id=?", (workspace["workspace_id"],)
        ).fetchone()
        if row:
            org_id = row["org"]
            connection.execute("update org set name=? where id=?", (workspace["name"], org_id))
        else:
            org_id = connection.execute("insert into org(name) values(?)", (workspace["name"],)).lastrowid
            connection.execute("insert into vos_workspace values(?,?)", (workspace["workspace_id"], org_id))
        org = dict(connection.execute("select name,tier,social from org where id=?", (org_id,)).fetchone())
    role = "admin" if member["role"] in {"owner", "admin"} else "editor"
    return {**org, "org": org_id, "role": role, "email": email}


def register_campaign_routes(app, current_user, members, workspaces):
    pilot = Autopilot(engine)
    app.on_event("shutdown")(pilot.close)

    @app.on_event("startup")
    def prepare():
        engine.init()
        with closing(engine.db()) as connection, connection:
            connection.execute("create table if not exists vos_workspace(workspace_id text primary key, org integer unique references org)")

        pilot.start()

    def identity(user=Depends(current_user)):
        member = members.find_one({"user_id": user["user_id"]})
        if not member:
            raise HTTPException(403, "Join a company workspace before starting a campaign.")
        workspace = workspaces.find_one({"workspace_id": member["workspace_id"]})
        if not workspace:
            raise HTTPException(403, "Your company workspace is unavailable.")
        with closing(engine.db()) as connection:
            return company_context(connection, workspace, member, user["email"])

    @app.get("/api/marketing-skills")
    def skill_library(company=Depends(identity)):
        return list(engine.catalog().values())

    @app.get("/api/campaign-agents")
    def dashboard(company=Depends(identity)):
        with closing(engine.db()) as connection:
            return {**engine.state(connection, company), "calendar":post_calendar.entries(connection,company["org"]), "seo":search_audit.state(connection,company["org"]), "channels":social.state(connection,company["org"]), "deliveries":social.history(connection,company["org"]), "autopilot":pilot.state(connection, company["org"])}

    @app.get("/api/social-media/{key}")
    def media(key: str):
        with closing(engine.db()) as db:
            row=db.execute("SELECT jpeg FROM social_media WHERE key=? AND expires>?",(key,int(time.time()))).fetchone()
        if not row:
            raise HTTPException(404,"Image expired.")
        return Response(row[0],media_type="image/jpeg")

    @app.post("/api/search-audit/{operation}")
    def search_action(operation: str,payload: dict,request: Request,company=Depends(identity)):
        if company["role"]!="admin" or request.headers.get("X-VOS-Client")!="dashboard":
            raise HTTPException(403,"Company administrator access required.")
        with closing(engine.db()) as db:
            try:
                return search_audit.action(db,company,operation,payload)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(502,"Google authorization failed. Check app and property access.") from None

    @app.post("/api/social/{operation}")
    def connection_action(operation: str, payload: dict, request: Request, company=Depends(identity)):
        if company["role"]!="admin" or request.headers.get("X-VOS-Client")!="dashboard":
            raise HTTPException(403,"Company administrator access required.")
        with closing(engine.db()) as db:
            try:
                return social.auth(db,company,operation,payload)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(502,"Provider authorization failed. Check app permissions and try again.") from None

    @app.post("/api/campaign-agents/{operation}")
    def campaign_action(operation: str, payload: dict, request: Request, company=Depends(identity)):
        if operation not in ACTIONS | {"configure", "pause", "run-skill","reschedule-post","cancel-post","plan-private"}:
            raise HTTPException(404, "Unknown campaign action.")
        if request.headers.get("X-VOS-Client") != "dashboard":
            raise HTTPException(403, "Open the campaign in your VOS dashboard.")
        with closing(engine.db()) as connection:
            try:
                if operation in {"reschedule-post","cancel-post","plan-private"}:
                    return post_calendar.change(connection,engine,company,operation,payload)
                if operation == "run-skill":
                    engine.admin(company)
                    profile = pilot.state(connection, company["org"])
                    if not profile:
                        raise engine.Problem("Save your company brief in the dashboard first.")
                    slug = payload.get("skill")
                    if not isinstance(slug, str) or slug not in engine.catalog():
                        raise engine.Problem("Unknown marketing skill.",404)
                    result, _ = engine.action(connection,"run",profile["brief"],company,"",skill=slug,evidence=payload.get("evidence",""))
                    return result
                if operation == "configure":
                    pilot.configure(connection, company, payload)
                    return {"ok": True}
                if operation == "pause":
                    engine.admin(company)
                    with connection:
                        connection.execute("UPDATE autopilot SET enabled=0,due=NULL,version=version+1,note='Paused.' WHERE org=?", (company["org"],))
                    return {"ok": True}
                result, _ = engine.action(connection, operation, payload, company, "")
                if operation in ("connect", "disconnect"):
                    with connection:
                        connection.execute("UPDATE autopilot SET destination=NULL,version=version+1 WHERE org=?", (company["org"],))
                return result
            except engine.Problem as error:
                raise HTTPException(error.status, str(error)) from error
