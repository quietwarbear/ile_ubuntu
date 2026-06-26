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
import routes.community_dashboard as community_dashboard, routes.family as family
import routes.learning_circles as learning_circles

app = FastAPI()
for m in (villages, courses, live_sessions, community_dashboard, family, learning_circles):
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

# Village home feed (Phase 2)
as_user("alice")
r = c.get(f"/api/villages/{v['id']}/home")
check("member home feed -> 200", r.status_code == 200)
h = r.json()
check("home has all sections", all(k in h for k in ("village", "sessions", "circle", "goals", "posts", "elder_prompt", "my_village_role")))
check("home sessions include village session", any(x["id"] == s["id"] for x in h["sessions"]))
check("home role is youth", h["my_village_role"] == "youth")
as_user("bob")
check("non-member home feed -> 403", c.get(f"/api/villages/{v['id']}/home").status_code == 403)

# Phase 3: measures go village-wide
as_user("fac")
r = c.get(f"/api/dashboard/village/{v['id']}")
check("village dashboard (faculty) -> 200", r.status_code == 200)
d = r.json()
check("village dashboard sections", all(k in d for k in ("village", "dimensions", "members", "attention", "village_mentors", "cohorts")))
check("village dashboard counts all members", d["village"]["member_count"] == 2)  # fac + alice
check("members carry village_role", all("village_role" in m for m in d["members"]))

# mentors surface for check-in routing
import database as _db
_db.users_col.insert_one({"id": "mona", "email": "m@x.co", "name": "Mona", "role": "student", "subscription_tier": "elder_circle"})
c.post(f"/api/villages/{v['id']}/members", json={"user_id": "mona", "village_role": "mentor"})
d = c.get(f"/api/dashboard/village/{v['id']}").json()
check("village mentors surfaced", any(m["id"] == "mona" for m in d["village_mentors"]))

as_user("bob")
check("non-steward village dashboard -> 403", c.get(f"/api/dashboard/village/{v['id']}").status_code == 403)

# family digest: youth section carries village + goal progress
as_user("fac")
c.post(f"/api/villages/{v['id']}/goals", json={"text": "Read together"})
from routes.family import _build_youth_summary, _digest_section_html
ys = _build_youth_summary("alice")
check("youth summary carries village", ys["village"] and ys["village"]["name"] == "Oak Circle")
check("youth summary goal counts", ys["village"]["goals_total"] == 1 and ys["village"]["goals_done"] == 0)
html = _digest_section_html(ys)
check("digest section names the village", "Oak Circle" in html and "0 of 1 goals" in html)
ys2 = _build_youth_summary("bob")
check("villageless youth -> no village block", ys2["village"] is None and "Oak Circle" not in _digest_section_html(ys2))

# Phase 4: backfill + village pulse events
as_user("fac")
import database as _db4
_db4.cohorts_col.insert_one({"id": "co1", "name": "Saturday Coders", "members": ["alice", "bob"], "created_at": __import__("datetime").datetime.now()})
nv = c.post("/api/villages/from-cohort", json={"cohort_id": "co1"})
check("found village from cohort -> 200", nv.status_code == 200)
nv = nv.json()
check("village takes cohort name", nv["name"] == "Saturday Coders")
check("cohort attached to new village", _db4.cohorts_col.find_one({"id": "co1"})["village_id"] == nv["id"])
check("membership stays explicit (founder only)", len(nv["members"]) == 1 and nv["members"][0]["user_id"] == "fac")
check("re-found same cohort -> 400", c.post("/api/villages/from-cohort", json={"cohort_id": "co1"}).status_code == 400)
check("found from missing cohort -> 404", c.post("/api/villages/from-cohort", json={"cohort_id": "nope"}).status_code == 404)
as_user("alice")
check("non-faculty backfill -> 403", c.post("/api/villages/from-cohort", json={"cohort_id": "co1"}).status_code == 403)

# events: goal_progress on toggle, session_held on village session end
as_user("fac")
g = c.post(f"/api/villages/{v['id']}/goals", json={"text": "Host a showcase"}).json()
c.put(f"/api/villages/{v['id']}/goals/{g['id']}/toggle")
ev = _db4.events_col.find_one({"type": "village.goal_progress", "entity_id": v["id"]}, sort=[("created_at", -1)])
check("goal_progress event emitted with counts", ev is not None and "done" in ev.get("meta", {}) and "total" in ev.get("meta", {}))
c.put(f"/api/live-sessions/{s['id']}/end")
ev = _db4.events_col.find_one({"type": "village.session_held", "entity_id": v["id"]})
check("session_held event emitted on village session end", ev is not None)

# Catalog privacy: another teacher's draft is invisible, even to admins
_db4.users_col.insert_one({"id": "shy", "email": "shy@x.co", "name": "Shy", "role": "faculty", "subscription_tier": "elder_circle"})
USERS["shy"] = _db4.users_col.find_one({"id": "shy"})
USERS["admin"] = dict(USERS["fac"], id="adm", role="admin", email="adm@x.co"); _db4.users_col.insert_one(dict(USERS["admin"]))
as_user("shy")
draft = c.post("/api/courses", json={"title": "Shy Draft"}).json()  # status: draft
as_user("admin")
check("admin catalog hides another teacher's draft", all(x["id"] != draft["id"] for x in c.get("/api/courses").json()))
check("admin can still open the draft by link", c.get(f"/api/courses/{draft['id']}").status_code == 200)
as_user("shy")
check("owner still sees own draft in catalog", any(x["id"] == draft["id"] for x in c.get("/api/courses").json()))

# Learning circles (reciprocal co-learner rename)
as_user("alice")
check("non-faculty can't form a circle", c.post("/api/learning-circles/form", json={"co_learner_a_id":"alice","co_learner_b_id":"bob"}).status_code == 403)
as_user("fac")
circ = c.post("/api/learning-circles/form", json={"co_learner_a_id":"alice","co_learner_b_id":"bob"})
check("faculty forms a circle -> 200", circ.status_code == 200, circ.text)
circ = circ.json()
check("circle carries both co-learners", circ["co_learner_a"]["id"]=="alice" and circ["co_learner_b"]["id"]=="bob")
check("duplicate circle (reverse order) -> 400", c.post("/api/learning-circles/form", json={"co_learner_a_id":"bob","co_learner_b_id":"alice"}).status_code == 400)
# reciprocity: BOTH co-learners can add goals
as_user("alice")
check("co-learner A adds goal", c.post(f"/api/learning-circles/{circ['id']}/goals", json={"text":"read together"}).status_code == 200)
check("alice sees the circle in mine", any(x["id"]==circ["id"] for x in c.get("/api/learning-circles").json()["mine"]))
as_user("bob")
check("co-learner B adds goal too (reciprocal)", c.post(f"/api/learning-circles/{circ['id']}/goals", json={"text":"build together"}).status_code == 200)
check("co-learner B writes journal", c.post(f"/api/learning-circles/{circ['id']}/notes", json={"text":"good week"}).status_code == 200)
# outsider can't peek
as_user("fac")
_db4.users_col.insert_one({"id":"zia","email":"z@x.co","name":"Zia","role":"student","subscription_tier":"elder_circle"})
USERS["zia"]=_db4.users_col.find_one({"id":"zia"})
as_user("zia")
check("outsider can't open the circle -> 403", c.get(f"/api/learning-circles/{circ['id']}").status_code == 403)
# are_co_learners powers messaging permission
from routes.learning_circles import are_co_learners
check("are_co_learners true for the pair", are_co_learners("alice","bob") and are_co_learners("bob","alice"))
check("are_co_learners false for outsider", not are_co_learners("alice","zia"))

# Course player: modules + lesson banner/module_id
as_user("fac")
pc = c.post("/api/courses", json={"title":"Player Course","visibility":"unlisted"}).json()
mod = c.post(f"/api/courses/{pc['id']}/modules", json={"title":"Section One"})
check("add module -> 200", mod.status_code == 200, mod.text)
mod = mod.json()
check("module has id+order", "id" in mod and mod["order"] == 0)
les = c.post(f"/api/courses/{pc['id']}/lessons", json={"title":"L1","module_id":mod["id"],"banner_url":"https://x/b.png"}).json()
check("lesson stores module_id", les.get("module_id") == mod["id"])
check("lesson stores banner_url", les.get("banner_url") == "https://x/b.png")
got = c.get(f"/api/courses/{pc['id']}").json()
check("course returns modules", any(m["id"]==mod["id"] for m in got.get("modules",[])))
# rename + delete module unsets lesson.module_id
c.put(f"/api/courses/{pc['id']}/modules/{mod['id']}", json={"title":"Renamed"})
got = c.get(f"/api/courses/{pc['id']}").json()
check("module renamed", any(m["title"]=="Renamed" for m in got["modules"]))
c.delete(f"/api/courses/{pc['id']}/modules/{mod['id']}")
got = c.get(f"/api/courses/{pc['id']}").json()
check("module deleted", all(m["id"]!=mod["id"] for m in got["modules"]))
lessons_after = c.get(f"/api/courses/{pc['id']}/lessons").json()
check("orphaned lesson module_id cleared", lessons_after[0].get("module_id") in (None, ""))
# non-owner can't add a module
as_user("alice")
check("non-owner add module -> 403/404", c.post(f"/api/courses/{pc['id']}/modules", json={"title":"x"}).status_code in (403,404))

print(f"\n{ok} passed, {fail} failed")
exit(1 if fail else 0)
