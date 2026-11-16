"""Use the existing VOS identity and team directory for all agent operations."""
from contextlib import closing
from importlib import import_module
from pathlib import Path
import sys

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
    @app.on_event("startup")
    def prepare():
        engine.init()
        with closing(engine.db()) as connection, connection:
            connection.execute("create table if not exists vos_workspace(workspace_id text primary key, org integer unique references org)")

    def identity(user=Depends(current_user)):
        member = members.find_one({"user_id": user["user_id"]})
        if not member:
            raise HTTPException(403, "Join a company workspace before starting a campaign.")
        workspace = workspaces.find_one({"workspace_id": member["workspace_id"]})
        if not workspace:
            raise HTTPException(403, "Your company workspace is unavailable.")
        with closing(engine.db()) as connection:
            return company_context(connection, workspace, member, user["email"])

    @app.get("/api/campaign-agents")
    def dashboard(company=Depends(identity)):
        with closing(engine.db()) as connection:
            return engine.state(connection, company)

    @app.post("/api/campaign-agents/{operation}")
    def campaign_action(operation: str, payload: dict, request: Request, company=Depends(identity)):
        if operation not in ACTIONS:
            raise HTTPException(404, "Unknown campaign action.")
        if request.headers.get("X-VOS-Client") != "dashboard":
            raise HTTPException(403, "Open the campaign in your VOS dashboard.")
        with closing(engine.db()) as connection:
            try:
                result, _ = engine.action(connection, operation, payload, company, "")
                return result
            except engine.Problem as error:
                raise HTTPException(error.status, str(error)) from error
