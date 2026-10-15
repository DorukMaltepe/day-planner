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
assert c.get("/api/month/2026-10").get_json() == {"2026-10-15": {"eaten": 778, "done": 2, "net": -1422, "tasks": 0, "tasks_done": 0, "sets": 0, "workouts": 0}}

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
assert c.get("/api/month/2026-10").get_json()["2026-10-16"] == {
    "eaten": 0, "done": 0, "net": -1800, "tasks": 3, "tasks_done": 1, "sets": 0, "workouts": 0}
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
me = {"sex": "male", "age": 30, "height": 180, "weight": 80, "activity": "moderate", "goal": "lose"}
r = c.put("/api/profile", json=me).get_json()
# 10*80 + 6.25*180 - 5*30 + 5 = 1780; * 1.55 = 2759; * 0.8 = 2207.2 -> 2210
assert (r["bmr"], r["tdee"], r["goal_kcal"], r["at_minimum"]) == (1780, 2759, 2210, False), r
day = c.get("/api/day/2026-10-15").get_json()
assert day["base_burn"] == 1780 and day["goal_kcal"] == 2210
assert c.put("/api/profile", json=me | {"goal": "gain"}).get_json()["goal_kcal"] == 3030  # 2759 * 1.1
# 10*45 + 6.25*150 - 5*60 - 161 = 926.5; * 1.2 * 0.8 = 889 -> raised to the 1200 kcal minimum
small = {"sex": "female", "age": 60, "height": 150, "weight": 45, "activity": "sedentary", "goal": "lose"}
r = c.put("/api/profile", json=small).get_json()
assert (r["bmr"], r["goal_kcal"], r["at_minimum"]) == (926, 1200, True), r
assert c.put("/api/profile", json=me | {"age": 5}).status_code == 400
assert c.put("/api/profile", json=me | {"goal": "shred"}).status_code == 400
assert c.get("/api/profile").get_json()["sex"] == "female"  # rejected saves changed nothing

print("all tests passed")
