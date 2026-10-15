<div align="center">

# Day Planner

**A calendar of your days combined with a calorie, workout and body tracker.**

[![CI](https://github.com/DorukMaltepe/day-planner/actions/workflows/ci.yml/badge.svg)](https://github.com/DorukMaltepe/day-planner/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-3.1-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-database-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

Log what you ate, what you did and how you trained, then see each day's net calorie balance and your progress over time. It runs on your own machine or VM as one small Flask app with one SQLite file, and needs no account or cloud service.

```
net = eaten − base burn (BMR) − kcal burned by activities
```

## Features

| Area | What you get |
|------|--------------|
| **Calendar** | Month and day views with a daily plan of tasks and activities (gym, groceries, reading, job applications, …). An amber dot marks days whose program workout has no time yet; drag it onto an hour of the day's schedule. Export the day's timed items as an `.ics` file for iPhone or any other calendar. |
| **Food log** | Search about 22,500 foods with kcal, protein, carbs, fat and fiber per 100 g. Portion sizes are guessed from the food name. You can add your own foods. |
| **Energy balance** | Your BMR (Mifflin-St Jeor), maintenance calories (TDEE) and a daily goal for losing, recomposition, maintaining or gaining. |
| **Workouts** | Built-in programs (machine PPL 3×/week, classic PPL 6×/week, …). Swap an exercise for an equivalent one, and log sets (exercise, kg, reps) prefilled from your last session. |
| **Exercise progress** | For each session: sets, total reps, top weight, volume (kg × reps) and estimated 1-rep max (Epley), each with the change since the last session, so you can track progressive overload. |
| **Body measurements** | Track weight, waist, body fat and more, with the change since the previous entry. |

## Quick start

You need [Docker](https://docs.docker.com/get-docker/) with Compose.

```sh
git clone https://github.com/DorukMaltepe/day-planner.git
cd day-planner
docker compose up -d --build
```

Open <http://localhost:8000>. The data is stored in SQLite in the `planner-data` Docker volume, so it survives restarts and rebuilds.

## Development

```sh
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python app.py                     # http://localhost:8000, data in ./data/app.db
.venv/Scripts/python test_app.py                # run the tests
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `DB_PATH` | `./data/app.db` (`/data/app.db` in Docker) | Location of the SQLite database |

### Project structure

```
app.py              Flask app: JSON API, SQLite schema, calorie and portion logic
static/index.html   The whole single-page UI (HTML, CSS, JS)
static/programs.js  Workout programs and groups of interchangeable exercises
foods.csv           Food database, values per 100 g
fetch_foods.py      Pulls new products from Open Food Facts into foods.csv
test_app.py         API tests (plain asserts, no test framework)
Dockerfile          Production image: gunicorn with 1 worker and 4 threads
```

Gunicorn runs a single worker on purpose, because SQLite handles one writer best.

## Food database

On every start, `foods.csv` is loaded into the database. Rows whose name already exists are skipped. To add foods, use the **Add a food** form in the UI, or add rows to the CSV and restart.

Most entries are products sold at Edeka, REWE and Lidl, taken from [Open Food Facts](https://world.openfoodfacts.org). The values were entered by the community, so check the label if a number looks wrong. To pull new products:

```sh
python fetch_foods.py   # only adds rows, never changes existing ones
```

Then restart the app.

## Deploy to a VM

Copy the repo to the VM, run `docker compose up -d --build`, then move your database across:

```sh
# on your machine
docker compose cp app:/data/app.db ./app.db
# on the VM
docker compose cp ./app.db app:/data/app.db && docker compose restart
```

> [!WARNING]
> The app has no login. Do not expose port 8000 to the internet directly. Put it behind a VPN, an SSH tunnel or a reverse proxy with authentication.

## License

The code is released under the [MIT License](LICENSE).

The food data in `foods.csv` comes from [Open Food Facts](https://world.openfoodfacts.org) and is available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/).
