<div align="center">

# Day Planner

**A self-hosted planner that combines your calendar with calorie, workout and body tracking.**

[![CI](https://github.com/DorukMaltepe/day-planner/actions/workflows/ci.yml/badge.svg)](https://github.com/DorukMaltepe/day-planner/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-3.1-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-database-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Features](#features) · [Quick start](#quick-start) · [Email to calendar](#email-to-calendar) · [Configuration](#configuration) · [Development](#development)

</div>

Plan your day, log what you ate and how you trained, and see each day's net calorie balance and your progress over time. Day Planner is a single Flask app backed by one SQLite file. It runs on your own machine or VM and needs no account or third-party service.

```
net = eaten − base burn (BMR) − kcal burned by activities and gym sessions
```

## Features

### Planning

| | |
|---|---|
| **Month and day views** | A daily plan of tasks and activities (gym, groceries, reading, job applications, …) that you tick off as you go. Colored dots on the month view show which kinds of events each day holds. |
| **Event types** | Daily chore, Work, School and Social come built in, and you can add your own with any color. A type can ask for a meeting link (shown as a **Join** button) or a location. |
| **Day schedule** | Timed items appear on an hourly schedule. Give an item an end time, or let it default to one hour, and drag items to another hour to reschedule them. |
| **Email to calendar** | One click emails the day's timed items to you as an `.ics` file. On iPhone, open the attachment in Mail and tap **Add All**. Locations, meeting links and workout details carry over into the event notes. [Setup](#email-to-calendar) |

### Health and training

| | |
|---|---|
| **Food log** | Search about 22,500 foods with kcal, protein, carbs, fat and fiber per 100 g. Portion sizes are guessed from the food name, and you can add your own foods. |
| **Energy balance** | Your BMR (Mifflin-St Jeor), maintenance calories (TDEE) from your daily life without training, and a daily goal for losing, recomposition, maintaining or gaining. Exercise is taken off what you ate, and the bars show in color how much each food total, activity and gym session contributed. |
| **Workout programs** | Built-in programs (machine PPL 3×/week, classic PPL 6×/week, …). Swap an exercise for an equivalent one. An amber dot marks days whose workout has no time yet: drag it onto the schedule, and it lasts as long as its sets and rests take. |
| **Activities** | Log a walk, run, ride, swim and so on with its time and/or distance; the calories are estimated from your weight with MET values from the Compendium of Physical Activities (by speed for walking, running and cycling), or type them in yourself. |
| **Set logging** | Log sets (exercise, kg, reps), prefilled from your last session. Tap a scheduled workout to see each exercise's sets × reps and the weight you used last time. The day's sets count as a gym session: its calories are estimated from the set count (with rest by rep range) and the weight you lifted. |
| **Exercise progress** | For each session: sets, total reps, top weight, volume (kg × reps) and estimated 1-rep max (Epley), each with the change since the last session, so you can track progressive overload. |
| **Body measurements** | Track weight, waist, body fat and more, with the change since the previous entry. |

## Quick start

You need [Docker](https://docs.docker.com/get-docker/) with Compose 2.24 or newer.

```sh
git clone https://github.com/DorukMaltepe/day-planner.git
cd day-planner
docker compose up -d --build
```

Open <http://localhost:8000>. Your data is stored in the `planner-data` Docker volume, so it survives restarts and rebuilds.

## Email to calendar

The **Email to calendar** button sends the day's plan through your own email account over SMTP. Nothing else needs to be installed; you only need an **app password**, which is a separate password your provider creates just for this app. Never use your normal account password here.

1. Create an app password:

   | Provider | Where | Requirement |
   |----------|-------|-------------|
   | Gmail | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) | 2-Step Verification turned on. Remove the spaces from the 16-letter password. |
   | iCloud | [account.apple.com](https://account.apple.com) → Sign-In and Security → App-Specific Passwords | Two-factor authentication turned on |

2. Create a `.env` file next to `docker-compose.yml`:

   ```ini
   # iCloud: smtp.mail.me.com
   SMTP_HOST=smtp.gmail.com
   SMTP_USER=you@gmail.com
   SMTP_PASSWORD=yourapppassword
   # optional, defaults to SMTP_USER
   MAIL_TO=you@icloud.com
   ```

3. Run `docker compose up -d` to apply it.

To add the events on an iPhone, open the email in the **Mail** app, because the Gmail app can't add `.ics` files to Apple Calendar.

> [!NOTE]
> `.env` is listed in both `.gitignore` and `.dockerignore`, so the password is never committed or built into the image. If it does leak, revoke the app password and create a new one. Your main account password is not affected.

## Configuration

All settings are environment variables.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DB_PATH` | `./data/app.db` (`/data/app.db` in Docker) | Location of the SQLite database |
| `SMTP_HOST` | none | Mail server for the calendar email, e.g. `smtp.gmail.com` |
| `SMTP_PORT` | `587` | Mail server port; the connection is upgraded with STARTTLS |
| `SMTP_USER`, `SMTP_PASSWORD` | none | Login for the mail server; the email is sent from `SMTP_USER` |
| `MAIL_TO` | `SMTP_USER` | Address the calendar email goes to |

If the SMTP settings are not set, everything else works as normal, and the email button shows a message that email isn't set up yet.

## Development

```sh
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python app.py                     # http://localhost:8000, data in ./data/app.db
.venv/Scripts/python test_app.py                # run the tests
```

`python app.py` does not read `.env`. To test email locally, set the variables in your shell first, for example `$env:SMTP_HOST="smtp.gmail.com"` in PowerShell.

### Project structure

```
app.py              Flask app: JSON API, SQLite schema, calorie, portion and calendar logic
static/index.html   The whole single-page UI (HTML, CSS, JS)
static/programs.js  Workout programs and groups of interchangeable exercises
foods.csv           Food database, values per 100 g
fetch_foods.py      Pulls new products from Open Food Facts into foods.csv
test_app.py         API tests (plain asserts, no test framework; email uses a fake SMTP server)
Dockerfile          Production image: gunicorn with 1 worker and 4 threads
docker-compose.yml  One service, a data volume and the optional .env file
```

Gunicorn runs a single worker on purpose, because SQLite handles one writer best. Older databases are upgraded automatically on start.

## Food database

On every start, `foods.csv` is loaded into the database. Rows whose name already exists are skipped. To add foods, use the **Add a food** form in the UI, or add rows to the CSV and restart.

Most entries are products sold at Edeka, REWE and Lidl, taken from [Open Food Facts](https://world.openfoodfacts.org). The values were entered by the community, so check the label if a number looks wrong. To pull new products:

```sh
python fetch_foods.py   # only adds rows, never changes existing ones
```

Then restart the app.

## Deploy to a VM

Copy the repo to the VM, create your `.env` there if you want email, run `docker compose up -d --build`, then move your database across:

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
