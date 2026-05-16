# Habit Tracker

A small, dependency-light habit tracker available as both a **web app** and a **command-line interface**, built around a clean layered architecture so the same business rules power both transports.

Track daily habits, mark them complete, and watch your streaks grow.

---

## Features

- **Add, remove, and track habits** with day-by-day completion history
- **Live streak counter** — consecutive completed days, calculated on the fly
- **Web UI** — minimal, responsive single-page interface
- **CLI** — for quick terminal interactions
- **Atomic, thread-safe persistence** to a local JSON file
- **Security defaults** — CSRF protection, strict CSP, sensible response headers, server-side input validation

## Quick start

### Requirements
- Python 3.10+
- [Poetry](https://python-poetry.org/) (or any tool that can read `pyproject.toml`)

### Install

```bash
poetry install
```

Or with `pip`:

```bash
pip install flask flask-wtf gunicorn
```

### Run the web app

Development:

```bash
python app.py
```

Production:

```bash
gunicorn --bind=0.0.0.0:5000 --reuse-port app:app
```

Then open <http://localhost:5000>.

### Run the CLI

```bash
python main.py
```

### Configuration

| Variable | Purpose |
|---|---|
| `FLASK_SECRET_KEY` | Optional. Set in production so sessions and CSRF tokens survive restarts. A random ephemeral key is used if absent. |

---

## Architecture

The project is organised in clear layers. Each module has a single responsibility, which keeps the codebase small, testable, and easy to evolve.

```
.
├── app.py                      # App factory + WSGI entry point for Gunicorn
├── main.py                     # CLI transport (reuses the same service layer)
├── templates/
│   └── index.html              # Minimal single-page web UI
└── habit_tracker/
    ├── domain.py               # Pure Habit entity (no I/O, no framework)
    ├── repository.py           # HabitRepository ABC + JsonHabitRepository
    ├── service.py              # HabitService — business rules and orchestration
    ├── validators.py           # Input cleaning (shared by web + CLI)
    ├── routes.py               # Flask Blueprint with dependency injection
    └── security.py             # CSRF setup + response security headers
```

### Why this shape?

- **Domain → Repository → Service → Routes** is just enough structure for an app of this size. Each boundary earns its place: the repository abstracts storage so a future SQL backend slots in without touching anything else; the service centralises rules so the web app and CLI can't drift apart.
- **No DI container, no DTO classes, no event sourcing** — those would be over-engineering at this scale. Constructor injection and `dict` responses are sufficient.
- **Atomic file writes** (write to temp + `os.replace`) protect the data file from a half-written state if the process is killed mid-write.
- **Repository-level `update(name, mutator)`** performs read-modify-write under a single lock, preventing lost updates under concurrent toggles.

## REST API

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the web UI |
| `GET` | `/api/habits` | Lists all habits with today's completion + streak |
| `POST` | `/api/habits` | Creates a habit. Body: `{"name": "..."}` |
| `DELETE` | `/api/habits/<name>` | Removes a habit |
| `POST` | `/api/habits/<name>/toggle` | Toggles today's completion |

All state-changing requests require a CSRF token (`X-CSRFToken` header).

### HTTP status codes

| Code | Meaning |
|---|---|
| `200 / 201` | Success |
| `400` | Malformed JSON body |
| `404` | Habit not found |
| `409` | Habit already exists |
| `422` | Validation error (empty / too long / invalid characters) |

## Security

- CSRF protection on every write endpoint (via `flask-wtf`)
- Strict Content-Security-Policy and standard hardening headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`)
- Server-side input validation (length cap, allow-listed characters)
- Atomic, type-checked JSON loading — tampered or corrupt files are tolerated, never trusted
- All user-supplied text is HTML-escaped in the UI

## Data persistence

Habits are stored in a local `habits.json` file alongside the application. The file is created automatically on first write and is excluded from version control.

> If you plan to deploy on a stateless platform (Cloud Run, Cloud Functions, autoscaled containers, etc.), the local-file repository is not appropriate — the filesystem is ephemeral and isn't shared between instances. Implement an additional `HabitRepository` backed by a real database; the rest of the codebase doesn't need to change.

## License

[MIT](./LICENSE) © 2026 leejaew
