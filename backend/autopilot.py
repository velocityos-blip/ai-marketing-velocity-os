"""One scheduler per VOS API process. The schedule and handoffs live in SQLite."""
import social
import json
import logging
import time
from contextlib import closing
from threading import Event, Thread

WEEK = 7 * 24 * 3600


class Autopilot:
    def __init__(self, engine):
        self.engine = engine
        self.stop = Event()

    def start(self):
        with closing(self.engine.db()) as db, db:
            social.setup(db)
            db.execute("""CREATE TABLE IF NOT EXISTS autopilot (
                org INTEGER PRIMARY KEY REFERENCES org, brief TEXT NOT NULL,
                cadence TEXT NOT NULL, destination TEXT, enabled INTEGER NOT NULL,
                due INTEGER, version INTEGER NOT NULL, note TEXT NOT NULL)""")
            db.execute("UPDATE autopilot SET note='Server restarted during the campaign. Check activity.' WHERE note='Agents are working.'")
        self.stop.clear()
        self.thread = Thread(target=self.loop, name="vos-campaign-scheduler", daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)

    def configure(self, db, user, data):
        self.engine.admin(user)
        brief = {key: self.engine.field(data, key, length)
                 for key, length in (("goal", 600), ("offer", 200), ("audience", 200))}
        budget = data.get("budget", 0)
        cadence = data.get("cadence")
        if type(budget) is not int or not 0 <= budget <= 100000000 or cadence not in ("weekly", "once"):
            raise self.engine.Problem("Check your budget and campaign frequency.")
        brief["budget"] = budget
        with db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT * FROM autopilot WHERE org=?", (user["org"],)).fetchone()
            dest = data.get("destination") or None
            if dest and dest != db.execute("SELECT social FROM org WHERE id=?", (user["org"],)).fetchone()[0]:
                raise self.engine.Problem("Connect the publishing account first.")
            now = int(time.time())
            due = current["due"] if current and current["enabled"] else now
            if current and current["enabled"] and current["cadence"] == "once" and cadence == "weekly" and due is None:
                due = now + WEEK
            note = current["note"] if current and current["enabled"] else "First campaign queued."
            db.execute("""INSERT INTO autopilot VALUES(?,?,?,?,1,?,1,?)
                ON CONFLICT(org) DO UPDATE SET brief=excluded.brief,cadence=excluded.cadence,
                destination=excluded.destination,enabled=1,due=excluded.due,
                version=autopilot.version+1,note=excluded.note""",
                (user["org"], json.dumps(brief), cadence, dest, due, note))

    def state(self, db, org):
        row = db.execute("SELECT * FROM autopilot WHERE org=?", (org,)).fetchone()
        return {**dict(row), "brief": json.loads(row["brief"])} if row else None

    def tick(self):
        with closing(self.engine.db()) as db:
            now = int(time.time())
            with db:
                db.execute("BEGIN IMMEDIATE")
                job = db.execute("""SELECT a.*,o.name,o.tier FROM autopilot a JOIN org o ON o.id=a.org
                    WHERE enabled=1 AND due<=? ORDER BY due,org LIMIT 1""", (now,)).fetchone()
                if job:
                    due = now + WEEK if job["cadence"] == "weekly" else None
                    db.execute("UPDATE autopilot SET due=?, note='Agents are working.' WHERE org=?", (due, job["org"]))
            if not job:
                return social.collect(db)
            channels = social.targets(db, job["org"])
            feedback = [row for row in social.history(db, job["org"]) if row["metrics"]][:8]
            user = dict(org=job["org"], role="admin", name=job["name"], tier=job["tier"])
            try:
                previous = db.execute("SELECT draft FROM runs WHERE org=? AND draft!='' ORDER BY id DESC LIMIT 1", (job["org"],)).fetchone()
                result, _ = self.engine.action(db, "run", json.loads(job["brief"]), user, "", scheduled=True,
                                               previous=previous["draft"][:500] if previous else "", feedback=feedback)
                run = db.execute("SELECT * FROM runs WHERE id=?", (result["id"],)).fetchone()
                review = json.loads(run["messages"])[-1]["body"].splitlines()[0].strip()
                note = "Campaign prepared."
                if channels:
                    if review == "READY" and 0 < len(run["draft"].strip()) <= 500:
                        social.deliver(db,job,run,channels)
                        if not job["destination"]:
                            delivered = db.execute("SELECT count(*) FROM social_post WHERE run=? AND remote IS NOT NULL", (run["id"],)).fetchone()[0]
                            if delivered:
                                with db:
                                    db.execute("UPDATE runs SET status=? WHERE id=?", ("published" if delivered == len(channels) else "partially published", run["id"]))
                        note = "Campaign finished. See channel deliveries below."
                    else:
                        note = "Post held for review."
                if job["destination"]:
                    if review != "READY" or not 0 < len(run["draft"].strip()) <= 500:
                        note = "Post held for review."
                    else:
                        self.engine.action(db, "approve", {"id": run["id"], "draft": run["draft"]}, user, "")
                        self.engine.action(db, "publish", {"id": run["id"], "social": job["destination"]},
                                           user, "", schedule_version=job["version"])
                        note = "Published to @" + job["destination"] + "."
            except self.engine.Problem as exc:
                note = str(exc)
            with db:
                db.execute("UPDATE autopilot SET note=? WHERE org=? AND version=?", (note, job["org"], job["version"]))
            return True

    def loop(self):
        while not self.stop.is_set():
            try:
                if self.tick():
                    continue
            except Exception:
                logging.exception("Campaign scheduler stopped processing one item")
            self.stop.wait(4)
