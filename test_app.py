"""Run: python test_app.py"""
import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
from app import app, portion  # noqa: E402

c = app.test_client()

# seeded food DB is searchable
oats = c.get("/api/foods?q=oats").get_json()[0]
assert oats["name"] == "Oats (dry)" and oats["kcal"] == 389 and oats["portion"] == 50

# typical portion guessed from the name; kcal tells dry pasta from a cooked dish
assert portion("Butter chicken", 150) == 350 and portion("Pesto spaghetti", 180) == 350
assert portion("Nutella", 539) == 20 and portion("Spaghetti (Gut & Günstig)", 356) == 80
assert portion("Vollmilch Schokolade", 530) == 25 and portion("Basmati Reis", 130) == 200

# log a meal, an activity and a base burn, then check the balance
assert c.put("/api/settings", json={"base_burn": 1800}).status_code == 204
assert c.post("/api/meals", json={"day": "2026-10-15", "food_id": oats["id"], "grams": 200}).status_code == 201
assert c.post("/api/activities", json={"day": "2026-10-15", "title": "Gym", "kcal": 400}).status_code == 201
assert c.post("/api/activities", json={"day": "2026-10-15", "title": "Applied for jobs"}).status_code == 201

day = c.get("/api/day/2026-10-15").get_json()
assert day["totals"]["kcal"] == 778 and day["totals"]["protein"] == 33.8
assert day["net"] == 778 - 1800 - 400
assert c.get("/api/month/2026-10").get_json() == {"2026-10-15": {"eaten": 778, "done": 2, "net": -1422, "tasks": 0, "tasks_done": 0, "sets": 0, "workouts": 0, "colors": []}}

# custom food + duplicate rejected
r = c.post("/api/foods", json={"name": "Mom's lasagna", "kcal": 160, "protein": 9})
assert r.status_code == 201 and r.get_json()["portion"] == 350
assert c.post("/api/foods", json={"name": "mom's LASAGNA", "kcal": 1}).status_code == 409

# bad input is rejected
assert c.post("/api/meals", json={"day": "20261015", "food_id": oats["id"], "grams": 1}).status_code == 400
assert c.post("/api/meals", json={"day": "2026-10-15", "food_id": 99999, "grams": 1}).status_code == 400
assert c.post("/api/meals", json={"day": "2026-10-15", "food_id": oats["id"], "grams": "NaN"}).status_code == 400
assert c.post("/api/activities", json={"day": "2026-10-15", "title": " "}).status_code == 400
assert c.post("/api/activities", json=[1]).status_code == 400

# delete
meal_id = day["meals"][0]["id"]
assert c.delete(f"/api/meals/{meal_id}").status_code == 204
assert c.get("/api/day/2026-10-15").get_json()["meals"] == []

# workout sets: history per exercise, case-insensitive name
for day, w, r, name in [("2026-10-13", 60, 8, "Bench press"), ("2026-10-13", 60, 8, "Bench press"),
                        ("2026-10-15", 62.5, 6, "bench PRESS"), ("2026-10-15", 100, 1, "Bench press")]:
    assert c.post("/api/sets", json={"day": day, "exercise": name, "weight": w, "reps": r}).status_code == 201
assert c.post("/api/sets", json={"day": "2026-10-15", "exercise": "Pull-up", "reps": 10}).status_code == 201
assert c.post("/api/sets", json={"day": "2026-10-15", "exercise": "Squat", "weight": 80, "reps": 0}).status_code == 400
hist = c.get("/api/history/exercise?name=bench press").get_json()
assert hist == [
    {"day": "2026-10-15", "sets": 2, "reps": 7, "best": 100, "volume": 475, "e1rm": 100},
    {"day": "2026-10-13", "sets": 2, "reps": 16, "best": 60, "volume": 960, "e1rm": 76},
], hist
assert len(c.get("/api/day/2026-10-15").get_json()["sets"]) == 3

# body measurements
assert c.post("/api/measurements", json={"day": "2026-10-13", "kind": "Weight (kg)", "value": 81.2}).status_code == 201
assert c.post("/api/measurements", json={"day": "2026-10-15", "kind": "weight (kg)", "value": 80.6}).status_code == 201
assert c.post("/api/measurements", json={"day": "2026-10-15", "kind": "Waist (cm)"}).status_code == 400
assert [r["value"] for r in c.get("/api/history/measurement?name=Weight (kg)").get_json()] == [80.6, 81.2]
assert c.get("/api/names").get_json() == {"exercises": ["Bench press", "Pull-up"], "measurements": ["Weight (kg)"]}
m_id = c.get("/api/day/2026-10-15").get_json()["measurements"][0]["id"]
assert c.delete(f"/api/measurements/{m_id}").status_code == 204

# daily plan and goals: plan items sort by time, untimed last
for body in [{"kind": "plan", "title": "Groceries"}, {"kind": "plan", "title": "Dentist", "time": "09:30"},
             {"kind": "goal", "title": "Drink 2 L of water"}]:
    assert c.post("/api/tasks", json={"day": "2026-10-16", **body}).status_code == 201
assert c.post("/api/tasks", json={"day": "2026-10-16", "kind": "plan", "title": "x", "time": "25:00"}).status_code == 400
assert c.post("/api/tasks", json={"day": "2026-10-16", "kind": "todo", "title": "x"}).status_code == 400
tasks = c.get("/api/day/2026-10-16").get_json()["tasks"]
assert [x["title"] for x in tasks] == ["Dentist", "Groceries", "Drink 2 L of water"], tasks
assert c.patch(f"/api/tasks/{tasks[0]['id']}", json={"done": True}).status_code == 204
assert c.patch(f"/api/tasks/{tasks[0]['id']}", json={"done": "yes"}).status_code == 400
assert c.patch("/api/tasks/99999", json={"done": True}).status_code == 404
# moving a task changes only its start time
assert c.patch(f"/api/tasks/{tasks[0]['id']}", json={"time": "10:15"}).status_code == 204
moved = c.get("/api/day/2026-10-16").get_json()["tasks"][0]
assert (moved["title"], moved["time"], moved["done"]) == ("Dentist", "10:15", 1), moved
assert c.patch(f"/api/tasks/{tasks[0]['id']}", json={"time": "9:15"}).status_code == 400
assert c.patch(f"/api/tasks/{tasks[0]['id']}", json={}).status_code == 400
assert c.get("/api/month/2026-10").get_json()["2026-10-16"] == {
    "eaten": 0, "done": 0, "net": -1800, "tasks": 3, "tasks_done": 1, "sets": 0, "workouts": 0, "colors": []}
assert c.delete(f"/api/tasks/{tasks[1]['id']}").status_code == 204

# a scheduled workout is a timed task; the day's timed items export as an iCalendar file
assert c.post("/api/tasks", json={"day": "2026-10-16", "kind": "workout", "title": "Push, workout", "time": "23:30"}).status_code == 201
assert c.get("/api/month/2026-10").get_json()["2026-10-16"]["workouts"] == 1
ics = c.get("/api/calendar/2026-10-16.ics")
assert ics.mimetype == "text/calendar"
body = ics.get_data(as_text=True)
assert body.count("BEGIN:VEVENT") == 2 and "Drink" not in body, body  # Dentist and the workout; the goal has no time
assert "DTSTART:20261016T233000\r\nDTEND:20261017T003000\r\nSUMMARY:Push\\, workout\r\nEND:VEVENT" in body, body
assert c.get("/api/calendar/16.10.2026.ics").status_code == 400
# emailing the export: refused until SMTP is set up, then sent as a text/calendar attachment
assert c.post("/api/calendar/2026-10-16/email").status_code == 503
sent = []
class FakeSMTP:
    def __init__(self, host, port, timeout): sent.append((host, port))
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def starttls(self): pass
    def login(self, user, password): sent.append((user, password))
    def send_message(self, msg): sent.append(msg)
app_module = __import__("app")
real_smtp, app_module.smtplib.SMTP = app_module.smtplib.SMTP, FakeSMTP
os.environ.update(SMTP_HOST="smtp.example.com", SMTP_USER="me@example.com", SMTP_PASSWORD="pw", MAIL_TO="phone@example.com")
assert c.post("/api/calendar/2026-10-16/email").status_code == 204
assert c.post("/api/calendar/16.10.2026/email").status_code == 400
app_module.smtplib.SMTP = real_smtp
for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_TO"):
    del os.environ[k]
assert sent[:2] == [("smtp.example.com", 587), ("me@example.com", "pw")], sent
msg = sent[2]
att = next(msg.iter_attachments())
assert msg["To"] == "phone@example.com" and att.get_content_type() == "text/calendar" and att.get_filename() == "plan-2026-10-16.ics"
assert att.get_content().count("BEGIN:VEVENT") == 2
# a workout's estimated length sets its end time; other events last an hour
assert c.post("/api/tasks", json={"day": "2026-10-18", "kind": "workout", "title": "Legs workout", "time": "18:00", "minutes": 75}).status_code == 201
assert c.get("/api/day/2026-10-18").get_json()["tasks"][0]["minutes"] == 75
assert "DTSTART:20261018T180000\r\nDTEND:20261018T191500" in c.get("/api/calendar/2026-10-18.ics").get_data(as_text=True)
# a planned event with an end time past midnight ends the next day
assert c.post("/api/tasks", json={"day": "2026-10-18", "kind": "plan", "title": "Party", "time": "22:00", "minutes": 180}).status_code == 201
assert "DTSTART:20261018T220000\r\nDTEND:20261019T010000" in c.get("/api/calendar/2026-10-18.ics").get_data(as_text=True)
for bad in (0, 1441, 1.5, "60", True):
    assert c.post("/api/tasks", json={"day": "2026-10-18", "kind": "workout", "title": "x", "time": "18:00", "minutes": bad}).status_code == 400, bad

# event types: seeded defaults, user-defined ones, and their optional link and location
types = {t["name"]: t for t in c.get("/api/event_types").get_json()}
assert list(types) == ["Daily chore", "Work", "School", "Social"] and types["Work"]["has_link"] and types["School"]["has_location"]
assert c.post("/api/event_types", json={"name": "Gym class", "color": "#ff8800", "has_location": True}).status_code == 201
assert c.post("/api/event_types", json={"name": "gym CLASS", "color": "#ff8800"}).status_code == 409
assert c.post("/api/event_types", json={"name": "Bad", "color": "red;}"}).status_code == 400
work = types["Work"]["id"]
assert c.post("/api/tasks", json={"day": "2026-10-17", "kind": "plan", "title": "Standup", "time": "09:00",
                                  "type_id": work, "link": "https://meet.example.com/abc"}).status_code == 201
assert c.post("/api/tasks", json={"day": "2026-10-17", "kind": "plan", "title": "Lecture", "time": "11:00",
                                  "type_id": types["School"]["id"], "location": "Room 2.14"}).status_code == 201
assert c.post("/api/tasks", json={"day": "2026-10-17", "kind": "plan", "title": "x", "link": "javascript:alert(1)"}).status_code == 400
assert c.post("/api/tasks", json={"day": "2026-10-17", "kind": "plan", "title": "x", "type_id": 99999}).status_code == 400
t = c.get("/api/day/2026-10-17").get_json()["tasks"]
assert (t[0]["type"], t[0]["color"], t[0]["link"], t[1]["location"]) == ("Work", "#2f6fde", "https://meet.example.com/abc", "Room 2.14"), t
assert sorted(c.get("/api/month/2026-10").get_json()["2026-10-17"]["colors"]) == ["#2f6fde", "#8b5cf6"]
body = c.get("/api/calendar/2026-10-17.ics").get_data(as_text=True)
assert "URL:https://meet.example.com/abc" in body and "LOCATION:Room 2.14" in body, body
assert r"DESCRIPTION:Type: Work\nMeeting link: https://meet.example.com/abc" + "\r\n" in body, body
assert r"DESCRIPTION:Type: School\nLocation: Room 2.14" + "\r\n" in body, body
# a workout's exercise list goes into its event notes
assert c.post("/api/tasks", json={"day": "2026-10-19", "kind": "workout", "title": "Push workout", "time": "07:00",
                                  "notes": "Chest, about 60 minutes.\n\nBench press: 3 × 8-10 at 60 kg"}).status_code == 201
body = c.get("/api/calendar/2026-10-19.ics").get_data(as_text=True)
assert r"DESCRIPTION:Chest\, about 60 minutes.\n\nBench press: 3 × 8-10 at 60 kg" + "\r\n" in body, body
assert c.post("/api/tasks", json={"day": "2026-10-19", "kind": "plan", "title": "x", "notes": 5}).status_code == 400
assert c.delete(f"/api/event_types/{work}").status_code == 204  # its tasks stay, without a type
t = c.get("/api/day/2026-10-17").get_json()["tasks"]
assert t[0]["type_id"] is None and t[0]["link"] == "https://meet.example.com/abc"

# workout program: one active at a time, null clears it
assert c.get("/api/program").get_json() == {"program": None, "start": None}
assert c.put("/api/program", json={"program": "machine-3", "start": "2026-10-12"}).status_code == 204
assert c.put("/api/program", json={"program": "classic-6", "start": "2026-10-13"}).status_code == 204
assert c.get("/api/program").get_json() == {"program": "classic-6", "start": "2026-10-13"}
assert c.put("/api/program", json={"program": "classic-6", "start": "13.10.2026"}).status_code == 400
assert c.put("/api/program", json={"program": None}).status_code == 204
assert c.get("/api/program").get_json()["program"] is None

# last session before a day, per exercise, case-insensitive; unknown names are left out
last = c.get("/api/last-sets?before=2026-10-15&name=bench press&name=Squat").get_json()
assert last == {"bench press": {"day": "2026-10-13", "sets": [{"weight": 60, "reps": 8}, {"weight": 60, "reps": 8}]}}, last
assert c.get("/api/last-sets?before=2026-10-16&name=Bench press").get_json()["Bench press"]["day"] == "2026-10-15"
assert c.get("/api/month/2026-10").get_json()["2026-10-13"]["sets"] == 2

# exercise swaps per program slot; null goes back to the default
assert c.get("/api/swaps").get_json() == {}
assert c.put("/api/swaps", json={"slot": "classic-6:pushA:0", "exercise": "Chest press"}).status_code == 204
assert c.put("/api/swaps", json={"slot": "classic-6:pushA:0", "exercise": "Dumbbell bench press"}).status_code == 204
assert c.get("/api/swaps").get_json() == {"classic-6:pushA:0": "Dumbbell bench press"}
assert c.put("/api/swaps", json={"slot": "classic-6:pushA:0", "exercise": " "}).status_code == 400
assert c.put("/api/swaps", json={"slot": "classic-6:pushA:0", "exercise": None}).status_code == 204
assert c.get("/api/swaps").get_json() == {}

# profile -> BMR (Mifflin-St Jeor) and calorie goal; saving it also sets base burn
assert c.get("/api/profile").get_json() == {}
me = {"sex": "male", "age": 30, "height": 180, "weight": 80, "activity": "on_feet", "goal": "lose"}
r = c.put("/api/profile", json=me).get_json()
# 10*80 + 6.25*180 - 5*30 + 5 = 1780; * 1.5 = 2670; * 0.8 = 2136 -> 2140
assert (r["bmr"], r["tdee"], r["goal_kcal"], r["at_minimum"]) == (1780, 2670, 2140, False), r
day = c.get("/api/day/2026-10-15").get_json()
assert day["base_burn"] == 1780 and day["goal_kcal"] == 2140
assert c.put("/api/profile", json=me | {"goal": "gain"}).get_json()["goal_kcal"] == 2940  # 2670 * 1.1
assert c.put("/api/profile", json=me | {"activity": "moderate"}).status_code == 400  # old levels are gone
# a profile saved with an old level that counted training moves to the new levels on start
app_module = __import__("app")
for old, new in [("moderate", "sedentary"), ("very_active", "physical")]:
    with app_module.sqlite3.connect(os.environ["DB_PATH"]) as conn:
        conn.execute("UPDATE profile SET activity = ?", (old,))
    app_module.init_db()
    assert c.get("/api/profile").get_json()["activity"] == new
# 10*45 + 6.25*150 - 5*60 - 161 = 926.5; * 1.2 * 0.8 = 889 -> raised to the 1200 kcal minimum
small = {"sex": "female", "age": 60, "height": 150, "weight": 45, "activity": "sedentary", "goal": "lose"}
r = c.put("/api/profile", json=small).get_json()
assert (r["bmr"], r["goal_kcal"], r["at_minimum"]) == (926, 1200, True), r
assert c.put("/api/profile", json=me | {"age": 5}).status_code == 400
assert c.put("/api/profile", json=me | {"goal": "shred"}).status_code == 400
assert c.get("/api/profile").get_json()["sex"] == "female"  # rejected saves changed nothing

# activities without kcal are estimated from time and distance: (MET - 1) x 45 kg (the profile above) x hours
def activity(**body):
    r = c.post("/api/activities", json={"day": "2026-10-21", **body})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["kcal"]
assert activity(title="Walking", minutes=45, km=3.5) == 82  # 4.67 km/h -> MET 3.42
assert activity(title="Morning run", km=5) == 203           # usual 10 km/h, so 30 min at MET 10.03
assert activity(title="Schwimmen", minutes=40) == 150       # MET 6
assert activity(title="Swimming", km=1) == 0                # no speed table for swimming: the time is needed
assert activity(title="Walking", minutes=60, kcal=200) == 200  # an entered value wins
assert c.post("/api/activities", json={"day": "2026-10-21", "title": "Walking", "minutes": 2000}).status_code == 400
# a gym session is estimated from its sets: time by rep range, plus the lifted work
assert c.post("/api/sets", json={"day": "2026-10-21", "exercise": "Deadlift", "weight": 100, "reps": 5}).status_code == 201
assert c.post("/api/sets", json={"day": "2026-10-21", "exercise": "Pull-up", "reps": 12}).status_code == 201
day = c.get("/api/day/2026-10-21").get_json()
assert (day["activity_burn"], day["gym_burn"]) == (635, 15), day  # 9.85 + 4.69 kcal for the two sets
assert day["activities"][0]["minutes"] == 45 and day["activities"][0]["km"] == 3.5
assert day["net"] == -926 - 635 - 15
assert c.get("/api/month/2026-10").get_json()["2026-10-21"]["net"] == -1576

print("all tests passed")
