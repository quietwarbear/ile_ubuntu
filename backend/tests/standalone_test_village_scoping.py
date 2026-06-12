"""Phase 1 functional check: village scoping of courses/live sessions.

STANDALONE — run directly, not via pytest:
    PYTHONPATH=backend python3 backend/tests/standalone_test_village_scoping.py
(It monkeypatches pymongo.MongoClient with mongomock before importing
database.py, which would poison the HTTP-based suites if collected together.
Deliberately named without the test_ prefix so pytest skips it.)
Requires: pip install mongomock httpx
"""
import mongomock, pymongo
pymongo.MongoClient = mongomock.MongoClient  # patch BEFORE database import

import database
from fastapi import FastAPI
from fastapi.testclient import TestClient
from middleware import get_current_user
import routes.villages as villages, routes.courses as courses, routes.live_sessions as live_sessions

app = FastAPI()
for m in (villages, courses, live_sessions):
    app.include_router(m.router)

USERS = {
    "fac":   {"id": "fac",   "email": "f@x.co", "name": "Faculty",  "role": "faculty", "subscription_tier": "elder_circle"},
    "alice": {"id": "alice", "email": "a@x.co", "name": "Alice",    "role": "student", "subscription_tier": "elder_circle"},
    "bob":   {"id": "bob",   "email": "b@x.co", "name": "Bob",      "role": "student", "subscription_tier": "elder_circle"},
}
for u in USERS.values():
    database.users_col.insert_one(dict(u))

current = {"u": USERS["fac"]}
app.dependency_overrides[get_current_user] = lambda: current["u"]
c = TestClient(app)

def as_user(k): current["u"] = USERS[k]

ok = fail = 0
def check(name, cond, extra=""):
    global ok, fail
    ok += cond; fail += (not cond)
    print(("PASS" if cond else "FAIL"), name, extra)

# Faculty founds a village, creates a course inside it
as_user("fac")
v = c.post("/api/villages", json={"name": "Oak Circle"}).json()
crs = c.post("/api/courses", json={"title": "Drumming", "village_id": v["id"]}).json()
check("create course with village_id", crs.get("village_id") == v["id"])
c.put(f"/api/courses/{crs['id']}", json={"status": "active"})
r = c.post(f"/api/courses/{crs['id']}/visibility", json={"visibility": "village"})
check("set village visibility", r.status_code == 200, r.text)

# Non-steward can't create village-scoped course
as_user("alice")
r = c.post("/api/courses", json={"title": "Sneak", "village_id": v["id"]})
check("non-steward create in village -> 403", r.status_code == 403)

# Visibility: non-member can't see/fetch/enroll
r = c.get("/api/courses")
check("non-member catalog hides village course", all(x["id"] != crs["id"] for x in r.json()))
check("non-member direct fetch -> 404", c.get(f"/api/courses/{crs['id']}").status_code == 404)
check("non-member enroll -> 403", c.post(f"/api/courses/{crs['id']}/enroll").status_code == 403)

# Invite code does not pierce village privacy
as_user("fac")
code = c.post(f"/api/courses/{crs['id']}/invite-code").json()["code"]
as_user("alice")
check("invite accept (non-member) -> 403", c.post(f"/api/courses/invites/{code}/accept").status_code == 403)

# Welcome alice into the village -> everything opens, no invite code needed
as_user("fac")
c.post(f"/api/villages/{v['id']}/members", json={"user_id": "alice", "village_role": "youth"})
as_user("alice")
check("member sees course in catalog", any(x["id"] == crs["id"] for x in c.get("/api/courses").json()))
check("member ?village_id= filter", any(x["id"] == crs["id"] for x in c.get(f"/api/courses?village_id={v['id']}").json()))
check("member direct fetch -> 200", c.get(f"/api/courses/{crs['id']}").status_code == 200)
check("member enroll, no code -> 200", c.post(f"/api/courses/{crs['id']}/enroll").status_code == 200)

# Live sessions
as_user("fac")
s = c.post("/api/live-sessions", json={"title": "Circle Time", "village_id": v["id"]}).json()
check("session carries village_id", s.get("village_id") == v["id"])
c.put(f"/api/live-sessions/{s['id']}/start")
as_user("bob")
check("non-member join -> 403", c.post(f"/api/live-sessions/{s['id']}/join").status_code == 403)
as_user("alice")
check("member join -> 200", c.post(f"/api/live-sessions/{s['id']}/join").status_code == 200)
check("village_id filter on sessions", any(x["id"] == s["id"] for x in c.get(f"/api/live-sessions?village_id={v['id']}").json()))

# Detach resets broken village visibility
as_user("fac")
c2 = c.post("/api/courses", json={"title": "Beads"}).json()
c.post(f"/api/villages/{v['id']}/courses", json={"course_id": c2["id"]})
c.post(f"/api/courses/{c2['id']}/visibility", json={"visibility": "village"})
c.delete(f"/api/villages/{v['id']}/courses/{c2['id']}")
got = c.get(f"/api/courses/{c2['id']}").json()
check("detach clears village + resets visibility", got["village_id"] is None and got["visibility"] == "unlisted")

# Commons untouched: regular course flow still works for non-members
as_user("fac")
c3 = c.post("/api/courses", json={"title": "Open Course", "visibility": "listed"}).json()
c.put(f"/api/courses/{c3['id']}", json={"status": "active"})
as_user("bob")
check("commons course visible+enrollable", c.post(f"/api/courses/{c3['id']}/enroll").status_code == 200)

print(f"\n{ok} passed, {fail} failed")
exit(1 if fail else 0)
