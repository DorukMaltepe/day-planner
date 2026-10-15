import csv
import os
import re
import smtplib
import sqlite3
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage

from flask import Flask, abort, g, jsonify, request

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(HERE, "data", "app.db"))
NUTRIENTS = ("kcal", "protein", "carbs", "fat", "fiber")  # per 100 g in the foods table
# activity multipliers turn BMR into maintenance calories (TDEE); goals adjust maintenance by a share
ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
GOALS = {"lose": -0.20, "recomp": -0.10, "maintain": 0.0, "gain": 0.10}
MIN_KCAL = {"female": 1200, "male": 1500}  # common safe minimum without medical supervision

# Typical single portion in grams, guessed from the food name (English and German).
# Each rule is (pattern, grams, (min_kcal, max_kcal)): the first match wins. The kcal range tells dry pasta
# (~350 kcal/100 g) from cooked dishes, and drinks from chocolate or spreads named "Vollmilch" or "Latte".
ANY, DRY, LIQUID = (0, 1e9), (300, 1e9), (0, 150)
PASTA = r"spaghetti|pasta|nudel|penne|fusilli|tagliatelle|linguine|farfalle|rigatoni|maccheroni|makkaroni|macaroni|gnocchi|ravioli|tortellini|tortelloni|maultasche|spätzle|lasagne|lasagna"
PORTIONS = [(re.compile(p), grams, *kcal) for p, grams, kcal in [
    (r"protein ?pulver|protein powder|whey", 30, ANY),
    (r"gewürz|pulver|powder|\bsalz\b|\bsalt\b|pfeffer\b|backpulver|hefe\b", 5, ANY),
    (r"espresso", 30, ANY),
    (r"bier\b|\bbeer\b|pils\b|pilsner|radler|weißbier|weizenbier|hefeweizen", 500, ANY),
    (r"\bwine\b|wein\b|\bsekt\b|prosecco|champagne", 150, ANY),
    (r"vodka|wodka|whisk|\brum\b|\bgin\b|schnaps|likör|liqueur|tequila", 40, ANY),
    (r"saft|juice|smoothie|shake|\bdrink|getränk|\bcola\b|limo\b|limonade|lemonade|schorle|fanta|sprite|\bsoda\b|eistee|ice ?tea|"
     r"wasser\b|^water|mineral water|kaffee|coffee|cappuccino|latte|tee\b|\btea\b|milch\b|\bmilk\b|kefir|ayran|kakao\b", 250, LIQUID),
    (r"^(?!.*(sauce|soße|salsa|paste))(.*butter chicken|.*murgh)", 350, ANY),
    (r"(?<!r)eis\b|eiscreme|ice cream|gelato|banana split|magnum", 100, ANY),  # before "cream"; (?<!r) skips Reis
    (r"nutella|nougat|schoko.?creme|haselnusscreme|aufstrich|erdnussbutter|peanut butter|nussmus|mandelmus|cashewmus|"
     r"honig|honey|marmelade|konfitüre|\bjam\b|sirup|syrup|ketchup|mayo|senf\b|mustard|remoulade|aioli|bbq|dressing|"
     r"soja ?sauce|curry ?(sauce|soße)|currysauce|soy sauce|sriracha|frischkäse|cream cheese|sahne\b|\bcream\b|schmand|crème fraîche|creme fraiche|zucker\b|\bsugar\b", 20, ANY),
    (r"butter\b(?! chicken)|margarine|ghee", 10, ANY),
    (r"pudding|milchreis|grießbrei|dessert|mousse|tiramisu|panna cotta", 150, ANY),
    (r"keks|cookie|biscuit|waffel|wafer|reiswaffel|rice cake|knäckebrot|zwieback", 25, ANY),
    (r"kuchen|cake|torte\b|muffin|brownie|strudel|donut|berliner|croissant", 80, ANY),
    (r"chips|crisps|flips|popcorn|cracker|salzstange|pretzel|nachos", 40, ANY),
    (r"schoko|chocolate|praline|riegel|\bbar\b|gummi|haribo|bonbon|candy|lakritz", 25, ANY),
    (r"nüsse|nuss\b|\bnuts?\b|almond|mandel|walnut|cashew|pistazie|pistachio|erdnüsse|peanuts|studentenfutter|trail mix", 30, ANY),
    (r"oats|hafer|müsli|muesli|granola|cornflakes|cereal|flakes|porridge|knusper", 50, ANY),
    # dishes before bread, dairy and cheese, so "Käsespätzle" or "Cheeseburger" count as a meal
    (r"pastasauce|nudelsauce|pasta sauce", 125, ANY),
    (r"pizza", 350, ANY),
    (r"curry|tikka|masala|korma|\bdal\b|chili con carne|gulasch|goulash|eintopf|stew|risotto|paella|auflauf|casserole|bowl|"
     r"bibimbap|ramen|\bpho\b|pad thai|fried rice|bratreis|bratnudeln|\bnasi\b|biryani|kebab|döner|dürüm", 350, ANY),
    (PASTA + r"|\breis\b|\brice\b|basmati|jasmin|quinoa|couscous|bulgur|linsen|lentils|kichererbsen|chickpeas|bohnen|beans", 80, DRY),
    (PASTA, 350, ANY),
    (r"so(ß|ss)e|sauce|sugo", 125, ANY),
    (r"pesto|hummus", 50, ANY),
    (r"suppe|soup", 300, ANY),
    (r"brötchen|semmel|\broll\b|\bbuns?\b|bagel|baguette|ciabatta", 60, ANY),
    (r"burger|wrap|burrito|sandwich|sushi", 250, ANY),
    (r"brot|bread|toast", 80, ANY),
    (r"skyr|quark|joghurt|jogurt|yogurt|yoghurt|cottage cheese|hüttenkäse|körniger", 150, ANY),
    (r"käse|cheese|cheddar|gouda|mozzarella|feta|parmesan|emmentaler|camembert|halloumi", 30, ANY),
    (r"pommes|fries", 150, ANY),
    (r"salat|salad", 200, ANY),
    (r"aufschnitt|salami|schinken|\bham\b|prosciutto|mortadella|lyoner|leberwurst|teewurst|mettwurst|bacon|speck", 30, ANY),
    (r"wurst|würstchen|wiener|frankfurter|sausage", 100, ANY),
    (r"chicken|hähnchen|huhn|hühner|pute|turkey|beef|rind|steak|pork|schwein|lamm|lamb|hack|mince|schnitzel|"
     r"fisch|fish|lachs|salmon|thunfisch|tuna|shrimp|garnele|tofu|tempeh|seitan|falafel", 150, ANY),
    (r"\boil\b|öl\b", 10, ANY),
    (r"\beggs?\b|\beier?\b", 60, ANY),
    (r"\breis\b|\brice\b|basmati|jasmin|quinoa|couscous|bulgur", 200, ANY),
    (r"linsen|lentils|kichererbsen|chickpeas|bohnen|beans", 150, ANY),
    (r"kartoffel|potato", 200, ANY),
    (r"apfel|apple|birne|\bpear|mango", 180, ANY),
    (r"orange", 150, ANY),
    (r"banane|banana", 120, ANY),
    (r"beere|berr|trauben|grapes|kirsche|cherr", 125, ANY),
    (r"avocado|kiwi", 100, ANY),
    (r"broccoli|brokkoli|spinat|spinach|karotte|möhre|carrot|tomate|tomato|gurke|cucumber|paprika|pepper|zwiebel|onion|"
     r"zucchini|blumenkohl|cauliflower|pilz|champignon|mushroom|gemüse|vegetable", 100, ANY),
]]


def portion(name, kcal):
    """Typical grams for one portion of this food: a placeholder the user can overwrite."""
    name = name.lower()
    for pattern, grams, lo, hi in PORTIONS:
        if lo <= kcal < hi and pattern.search(name):
            return grams
    # unknown food: energy-dense things (nuts, fats, snacks) are eaten in smaller amounts
    return 30 if kcal >= 500 else 50 if kcal >= 300 else 150 if kcal >= 150 else 200

SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  kcal REAL NOT NULL, protein REAL NOT NULL DEFAULT 0, carbs REAL NOT NULL DEFAULT 0,
  fat REAL NOT NULL DEFAULT 0, fiber REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS meals (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,
  food_id INTEGER NOT NULL REFERENCES foods(id),
  grams REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS meals_day ON meals(day);
CREATE TABLE IF NOT EXISTS activities (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,
  title TEXT NOT NULL,
  kcal REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS activities_day ON activities(day);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sets (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,
  exercise TEXT NOT NULL COLLATE NOCASE,
  weight REAL NOT NULL DEFAULT 0,
  reps INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sets_day ON sets(day);
CREATE INDEX IF NOT EXISTS sets_exercise ON sets(exercise);
CREATE TABLE IF NOT EXISTS measurements (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,
  kind TEXT NOT NULL COLLATE NOCASE,
  value REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS measurements_day ON measurements(day);
CREATE INDEX IF NOT EXISTS measurements_kind ON measurements(kind);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL,
  kind TEXT NOT NULL,  -- 'plan' (to-do, optional time), 'goal' or 'workout' (the program's session, timed)
  title TEXT NOT NULL,
  time TEXT,           -- HH:MM
  done INTEGER NOT NULL DEFAULT 0,
  type_id INTEGER REFERENCES event_types(id) ON DELETE SET NULL,
  link TEXT,           -- meeting link, for types with has_link
  location TEXT,       -- for types with has_location
  minutes INTEGER,     -- event length: from the end time, or a workout's estimate; without it an hour
  notes TEXT           -- details for the calendar export, e.g. a workout's exercises
);
CREATE INDEX IF NOT EXISTS tasks_day ON tasks(day);
CREATE TABLE IF NOT EXISTS event_types (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  color TEXT NOT NULL,  -- #rrggbb
  has_link INTEGER NOT NULL DEFAULT 0,
  has_location INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS program (
  id INTEGER PRIMARY KEY CHECK (id = 1),  -- one active program at a time
  name TEXT NOT NULL,                     -- program id from static/programs.js
  start TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profile (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  sex TEXT NOT NULL, age REAL NOT NULL, height REAL NOT NULL, weight REAL NOT NULL,
  activity TEXT NOT NULL, goal TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS swaps (
  slot TEXT PRIMARY KEY,   -- "program:workout:index" from static/programs.js
  exercise TEXT NOT NULL   -- what to do instead of the program's default exercise
);
"""

app = Flask(__name__, static_folder="static", static_url_path="")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.executescript(SCHEMA)
        # older databases lack these task columns
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        for col, decl in [("type_id", "INTEGER REFERENCES event_types(id) ON DELETE SET NULL"),
                          ("link", "TEXT"), ("location", "TEXT"), ("minutes", "INTEGER"), ("notes", "TEXT")]:
            if col not in cols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {decl}")
        # default types only into an empty table, so ones the user deleted stay deleted (unless all are)
        if not conn.execute("SELECT 1 FROM event_types").fetchone():
            conn.executemany("INSERT INTO event_types (name, color, has_link, has_location) VALUES (?, ?, ?, ?)", [
                ("Daily chore", "#3aa76d", 0, 0), ("Work", "#2f6fde", 1, 0),
                ("School", "#8b5cf6", 0, 1), ("Social", "#e0457b", 0, 1)])
        # OR IGNORE: re-running on every start adds new rows from foods.csv without touching existing ones
        with open(os.path.join(HERE, "foods.csv"), newline="", encoding="utf-8") as f:
            conn.executemany(
                "INSERT OR IGNORE INTO foods (name, kcal, protein, carbs, fat, fiber) "
                "VALUES (:name, :kcal, :protein, :carbs, :fat, :fiber)",
                csv.DictReader(f),
            )
    conn.close()


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(409)
@app.errorhandler(502)
@app.errorhandler(503)
def error(e):
    return jsonify(error=e.description), e.code


# --- input validation ---

def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "expected a JSON object")
    return data


def valid_day(value):
    try:
        if date.fromisoformat(value).isoformat() == value:
            return value
    except (TypeError, ValueError):
        pass
    abort(400, "day must be YYYY-MM-DD")


def num(data, key, default=None):
    try:
        v = float(data.get(key, default))
    except (TypeError, ValueError):
        abort(400, f"{key} must be a number")
    if not 0 <= v < 1e6:  # also rejects NaN and inf
        abort(400, f"{key} out of range")
    return v


def text(data, key):
    v = data.get(key)
    if not isinstance(v, str) or not v.strip() or len(v) > 200:
        abort(400, f"{key} must be a non-empty string (max 200 chars)")
    return v.strip()


def base_burn():
    row = db().execute("SELECT value FROM settings WHERE key = 'base_burn'").fetchone()
    return row[0] if row else 0


def targets(p):
    """BMR (Mifflin-St Jeor), maintenance and the daily calorie goal for a profile."""
    bmr = 10 * p["weight"] + 6.25 * p["height"] - 5 * p["age"] + (5 if p["sex"] == "male" else -161)
    tdee = bmr * ACTIVITY[p["activity"]]
    goal = round(tdee * (1 + GOALS[p["goal"]]), -1)
    return {"bmr": round(bmr), "tdee": round(tdee), "goal_kcal": max(goal, MIN_KCAL[p["sex"]]),
            "at_minimum": goal < MIN_KCAL[p["sex"]]}


def profile():
    row = db().execute("SELECT sex, age, height, weight, activity, goal FROM profile").fetchone()
    return dict(row) | targets(row) if row else None


# --- routes ---

@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/foods")
def list_foods():
    q = request.args.get("q", "")
    # prefix matches first, then foods.csv order: generic foods, then Edeka, REWE, Lidl products
    rows = db().execute(
        "SELECT * FROM foods WHERE name LIKE ? ORDER BY name NOT LIKE ?, id LIMIT 50",
        (f"%{q}%", f"{q}%"),
    )
    return jsonify([dict(r, portion=portion(r["name"], r["kcal"])) for r in rows])


@app.post("/api/foods")
def add_food():
    d = payload()
    values = [text(d, "name"), num(d, "kcal")] + [num(d, k, 0) for k in NUTRIENTS[1:]]
    try:
        with db() as conn:
            cur = conn.execute(f"INSERT INTO foods (name, {', '.join(NUTRIENTS)}) VALUES (?, ?, ?, ?, ?, ?)", values)
    except sqlite3.IntegrityError:
        abort(409, "a food with that name already exists")
    return jsonify(id=cur.lastrowid, portion=portion(values[0], values[1])), 201


@app.get("/api/day/<day>")
def get_day(day):
    valid_day(day)
    scaled = ", ".join(f"ROUND(f.{k} * m.grams / 100, 1) AS {k}" for k in NUTRIENTS)
    meals = [dict(r) for r in db().execute(
        f"SELECT m.id, m.grams, f.name, {scaled} FROM meals m JOIN foods f ON f.id = m.food_id "
        "WHERE m.day = ? ORDER BY m.id", (day,))]
    activities = [dict(r) for r in db().execute(
        "SELECT id, title, kcal FROM activities WHERE day = ? ORDER BY id", (day,))]
    sets = [dict(r) for r in db().execute(
        "SELECT id, exercise, weight, reps FROM sets WHERE day = ? ORDER BY id", (day,))]
    measurements = [dict(r) for r in db().execute(
        "SELECT id, kind, value FROM measurements WHERE day = ? ORDER BY id", (day,))]
    tasks = [dict(r) for r in db().execute(
        "SELECT t.id, t.kind, t.title, t.time, t.done, t.type_id, t.link, t.location, t.minutes, e.name AS type, e.color "
        "FROM tasks t LEFT JOIN event_types e ON e.id = t.type_id "
        "WHERE t.day = ? ORDER BY t.time IS NULL, t.time, t.id", (day,))]
    totals = {k: round(sum(m[k] for m in meals), 1) for k in NUTRIENTS}
    base = base_burn()
    burned = sum(a["kcal"] for a in activities)
    p = profile()
    return jsonify(meals=meals, activities=activities, sets=sets, measurements=measurements, tasks=tasks, totals=totals,
                   base_burn=base, activity_burn=burned, net=round(totals["kcal"] - base - burned),
                   goal_kcal=p and p["goal_kcal"])


@app.get("/api/month/<month>")
def get_month(month):
    valid_day(month + "-01")
    base = base_burn()
    rows = db().execute("""
        SELECT day, SUM(eaten) AS eaten, SUM(burned) AS burned, SUM(is_activity) AS done,
               SUM(is_task) AS tasks, SUM(task_done) AS tasks_done, SUM(is_set) AS sets, SUM(is_workout) AS workouts FROM (
          SELECT m.day, f.kcal * m.grams / 100 AS eaten, 0 AS burned, 0 AS is_activity, 0 AS is_task, 0 AS task_done,
                 0 AS is_set, 0 AS is_workout
            FROM meals m JOIN foods f ON f.id = m.food_id WHERE m.day LIKE ?
          UNION ALL
          SELECT day, 0, kcal, 1, 0, 0, 0, 0 FROM activities WHERE day LIKE ?
          UNION ALL
          SELECT day, 0, 0, 0, 1, done, 0, kind = 'workout' FROM tasks WHERE day LIKE ?
          UNION ALL
          SELECT day, 0, 0, 0, 0, 0, 1, 0 FROM sets WHERE day LIKE ?
        ) GROUP BY day""", (month + "-%",) * 4)
    colors = dict(db().execute("SELECT t.day, GROUP_CONCAT(DISTINCT e.color) FROM tasks t "
                               "JOIN event_types e ON e.id = t.type_id WHERE t.day LIKE ? GROUP BY t.day", (month + "-%",)))
    return jsonify({r["day"]: {"eaten": round(r["eaten"]), "done": r["done"],
                               "net": round(r["eaten"] - base - r["burned"]),
                               "tasks": r["tasks"], "tasks_done": r["tasks_done"], "sets": r["sets"],
                               "workouts": r["workouts"],
                               "colors": colors[r["day"]].split(",") if r["day"] in colors else []} for r in rows})


@app.post("/api/meals")
def add_meal():
    d = payload()
    grams = num(d, "grams")
    if grams == 0:
        abort(400, "grams must be greater than 0")
    try:
        with db() as conn:
            cur = conn.execute("INSERT INTO meals (day, food_id, grams) VALUES (?, ?, ?)",
                               (valid_day(d.get("day")), int(num(d, "food_id")), grams))
    except sqlite3.IntegrityError:
        abort(400, "unknown food_id")
    return jsonify(id=cur.lastrowid), 201


@app.post("/api/activities")
def add_activity():
    d = payload()
    with db() as conn:
        cur = conn.execute("INSERT INTO activities (day, title, kcal) VALUES (?, ?, ?)",
                           (valid_day(d.get("day")), text(d, "title"), num(d, "kcal", 0)))
    return jsonify(id=cur.lastrowid), 201


@app.post("/api/sets")
def add_set():
    d = payload()
    reps = int(num(d, "reps"))
    if reps == 0:
        abort(400, "reps must be at least 1")
    with db() as conn:
        cur = conn.execute("INSERT INTO sets (day, exercise, weight, reps) VALUES (?, ?, ?, ?)",
                           (valid_day(d.get("day")), text(d, "exercise"), num(d, "weight", 0), reps))
    return jsonify(id=cur.lastrowid), 201


@app.post("/api/measurements")
def add_measurement():
    d = payload()
    with db() as conn:
        cur = conn.execute("INSERT INTO measurements (day, kind, value) VALUES (?, ?, ?)",
                           (valid_day(d.get("day")), text(d, "kind"), num(d, "value")))
    return jsonify(id=cur.lastrowid), 201


@app.post("/api/tasks")
def add_task():
    d = payload()
    kind, time = d.get("kind"), d.get("time") or None
    if kind not in ("plan", "goal", "workout"):
        abort(400, "kind must be plan, goal or workout")
    if time is not None and not (isinstance(time, str) and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", time)):
        abort(400, "time must be HH:MM")
    link = d.get("link") or None
    # the link is rendered as an href, so only http(s) gets through (no javascript: URLs)
    if link is not None and not (isinstance(link, str) and len(link) <= 500 and re.fullmatch(r"https?://\S+", link)):
        abort(400, "link must be an http:// or https:// URL")
    location = text(d, "location") if d.get("location") else None
    type_id = int(num(d, "type_id")) if d.get("type_id") is not None else None
    minutes = d.get("minutes")
    if minutes is not None and not (isinstance(minutes, int) and not isinstance(minutes, bool) and 1 <= minutes <= 1440):
        abort(400, "minutes must be a whole number from 1 to 1440")
    notes = d.get("notes") or None
    if notes is not None and not (isinstance(notes, str) and len(notes) <= 4000):
        abort(400, "notes must be text (max 4000 chars)")
    try:
        with db() as conn:
            cur = conn.execute("INSERT INTO tasks (day, kind, title, time, type_id, link, location, minutes, notes) "
                               "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (valid_day(d.get("day")), kind, text(d, "title"), time, type_id, link, location, minutes, notes))
    except sqlite3.IntegrityError:
        abort(400, "unknown type_id")
    return jsonify(id=cur.lastrowid), 201


@app.get("/api/event_types")
def list_event_types():
    return jsonify([dict(r) for r in db().execute("SELECT * FROM event_types ORDER BY id")])


@app.post("/api/event_types")
def add_event_type():
    d = payload()
    color = d.get("color")
    if not (isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color)):  # it goes into a style attribute
        abort(400, "color must look like #1a2b3c")
    try:
        with db() as conn:
            cur = conn.execute("INSERT INTO event_types (name, color, has_link, has_location) VALUES (?, ?, ?, ?)",
                               (text(d, "name"), color, bool(d.get("has_link")), bool(d.get("has_location"))))
    except sqlite3.IntegrityError:
        abort(409, "an event type with that name already exists")
    return jsonify(id=cur.lastrowid), 201


@app.patch("/api/tasks/<int:task_id>")
def update_task(task_id):
    """Tick a task off ({done}) or move it to another start time ({time})."""
    d, fields = payload(), {}
    if "done" in d:
        if not isinstance(d["done"], bool):
            abort(400, "done must be true or false")
        fields["done"] = d["done"]
    if "time" in d:
        if not (isinstance(d["time"], str) and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", d["time"])):
            abort(400, "time must be HH:MM")
        fields["time"] = d["time"]
    if not fields:
        abort(400, "send done or time")
    with db() as conn:  # column names come from the fixed keys above, not from the request
        if not conn.execute(f"UPDATE tasks SET {', '.join(k + ' = ?' for k in fields)} WHERE id = ?",
                            (*fields.values(), task_id)).rowcount:
            abort(404, "no such task")
    return "", 204


def ics_text(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


@app.get("/api/calendar/<day>.ics")
def export_day(day):
    """The day's timed plan items and workout as an iCalendar file; iPhone Safari offers to add it to Calendar."""
    valid_day(day)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//day-planner//EN"]
    for t in db().execute("SELECT t.id, t.title, t.time, t.link, t.location, t.minutes, t.notes, e.name AS type "
                          "FROM tasks t LEFT JOIN event_types e ON e.id = t.type_id "
                          "WHERE t.day = ? AND t.time IS NOT NULL ORDER BY t.time", (day,)):
        start = datetime.fromisoformat(f"{day}T{t['time']}")
        end = start + timedelta(minutes=t["minutes"] or 60)
        # floating local times (no Z or TZID): the phone shows them in its own time zone
        lines += ["BEGIN:VEVENT", f"UID:task-{t['id']}@day-planner", f"DTSTAMP:{stamp}",
                  f"DTSTART:{start:%Y%m%dT%H%M%S}", f"DTEND:{end:%Y%m%dT%H%M%S}", f"SUMMARY:{ics_text(t['title'])}"]
        if t["location"]:
            lines.append(f"LOCATION:{ics_text(t['location'])}")
        if t["link"]:
            lines.append(f"URL:{t['link']}")
        # everything again in the notes too: Google Calendar ignores URL, and some apps hide LOCATION
        details = [f"Type: {t['type']}" if t["type"] else None, f"Location: {t['location']}" if t["location"] else None,
                   f"Meeting link: {t['link']}" if t["link"] else None, t["notes"]]
        if any(details):
            lines.append(f"DESCRIPTION:{ics_text(chr(10).join(x for x in details if x))}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    # shortcut: long lines aren't folded at 75 octets as RFC 5545 asks; Apple and Google Calendar read them anyway
    return app.response_class("\r\n".join(lines) + "\r\n", mimetype="text/calendar",
                              headers={"Content-Disposition": f'inline; filename="plan-{day}.ics"'})


@app.post("/api/calendar/<day>/email")
def email_day(day):
    """Mails the day's .ics to MAIL_TO; iPhone Mail offers Add All on the attachment."""
    host, user, password = (os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))
    if not (host and user and password):
        abort(503, "email isn't set up: set SMTP_HOST, SMTP_USER and SMTP_PASSWORD")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, os.environ.get("MAIL_TO", user), f"Day plan {day}"
    msg.set_content("Open the attachment and tap Add All to put the day in your calendar.")
    msg.add_attachment(export_day(day).get_data(), maintype="text", subtype="calendar", filename=f"plan-{day}.ics")
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587)), timeout=20) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        abort(502, f"couldn't send the email: {e}")
    return "", 204


@app.get("/api/program")
def get_program():
    row = db().execute("SELECT name, start FROM program").fetchone()
    return jsonify(program=row["name"] if row else None, start=row["start"] if row else None)


@app.put("/api/program")
def save_program():
    d = payload()
    with db() as conn:
        if d.get("program") is None:
            conn.execute("DELETE FROM program")
        else:
            conn.execute("INSERT INTO program (id, name, start) VALUES (1, ?, ?) "
                         "ON CONFLICT(id) DO UPDATE SET name = excluded.name, start = excluded.start",
                         (text(d, "program"), valid_day(d.get("start"))))
    return "", 204


@app.get("/api/profile")
def get_profile():
    return jsonify(profile() or {})


@app.put("/api/profile")
def save_profile():
    d = payload()
    p = {"sex": d.get("sex"), "activity": d.get("activity"), "goal": d.get("goal"),
         "age": num(d, "age"), "height": num(d, "height"), "weight": num(d, "weight")}
    if p["sex"] not in MIN_KCAL or p["activity"] not in ACTIVITY or p["goal"] not in GOALS:
        abort(400, "choose a sex, an activity level and a goal")
    for key, lo, hi in [("age", 14, 100), ("height", 100, 250), ("weight", 30, 300)]:
        if not lo <= p[key] <= hi:
            abort(400, f"{key} must be between {lo} and {hi}")
    t = targets(p)
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO profile (id, sex, age, height, weight, activity, goal) "
                     "VALUES (1, :sex, :age, :height, :weight, :activity, :goal)", p)
        # the energy balance subtracts base burn, so keep it in step with the estimated BMR
        conn.execute("INSERT INTO settings (key, value) VALUES ('base_burn', ?) "
                     "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (t["bmr"],))
    return jsonify(p | t)


@app.get("/api/swaps")
def get_swaps():
    return jsonify({r["slot"]: r["exercise"] for r in db().execute("SELECT slot, exercise FROM swaps")})


@app.put("/api/swaps")
def save_swap():
    d = payload()
    with db() as conn:
        if d.get("exercise") is None:  # back to the program's default
            conn.execute("DELETE FROM swaps WHERE slot = ?", (text(d, "slot"),))
        else:
            conn.execute("INSERT INTO swaps (slot, exercise) VALUES (?, ?) "
                         "ON CONFLICT(slot) DO UPDATE SET exercise = excluded.exercise",
                         (text(d, "slot"), text(d, "exercise")))
    return "", 204


@app.get("/api/last-sets")
def last_sets():
    """For each ?name=, the sets of the most recent session before ?before=."""
    before, out = valid_day(request.args.get("before")), {}
    for name in request.args.getlist("name")[:30]:
        last = db().execute("SELECT MAX(day) FROM sets WHERE exercise = ? AND day < ?", (name, before)).fetchone()[0]
        if last:
            out[name] = {"day": last, "sets": [dict(r) for r in db().execute(
                "SELECT weight, reps FROM sets WHERE exercise = ? AND day = ? ORDER BY id", (name, last))]}
    return jsonify(out)


@app.get("/api/names")
def names():
    return jsonify(
        exercises=[r[0] for r in db().execute("SELECT exercise FROM sets GROUP BY exercise ORDER BY exercise")],
        measurements=[r[0] for r in db().execute("SELECT kind FROM measurements GROUP BY kind ORDER BY kind")])


@app.get("/api/history/exercise")
def exercise_history():
    # e1rm = estimated one-rep max (Epley formula), the usual progressive-overload yardstick
    rows = db().execute("""
        SELECT day, COUNT(*) AS sets, SUM(reps) AS reps, MAX(weight) AS best,
               ROUND(SUM(weight * reps)) AS volume,
               ROUND(MAX(CASE WHEN reps = 1 THEN weight ELSE weight * (1 + reps / 30.0) END), 1) AS e1rm
        FROM sets WHERE exercise = ? GROUP BY day ORDER BY day DESC""", (request.args.get("name", ""),))
    return jsonify([dict(r) for r in rows])


@app.get("/api/history/measurement")
def measurement_history():
    rows = db().execute("SELECT day, value FROM measurements WHERE kind = ? ORDER BY day DESC, id DESC",
                        (request.args.get("name", ""),))
    return jsonify([dict(r) for r in rows])


@app.delete("/api/<any(meals, activities, sets, measurements, tasks, event_types):table>/<int:row_id>")
def delete_entry(table, row_id):
    with db() as conn:  # table name is safe: restricted by the URL converter
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
    return "", 204


@app.put("/api/settings")
def save_settings():
    with db() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('base_burn', ?) "
                     "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (num(payload(), "base_burn"),))
    return "", 204


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=8000)
