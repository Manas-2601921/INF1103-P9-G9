# Workplace Incident Triage Assistant

An AI-assisted, object-oriented web application (Flask + SQLite) that analyses unstructured workplace incident reports, classifies their severity and hazard type, prioritises follow-up actions using deterministic safety rules, and surfaces trend analytics on a live dashboard.

The project is designed for small and medium-sized organisations, with an initial focus on Singapore Workplace Safety and Health (WSH) reporting. It provides **triage support only** and does not replace a qualified workplace safety investigation.

---

## Key Capabilities

- **Structured incident processing:** Collects validated report fields and turns free-text descriptions into schema-validated AI assessments (severity score/band, confidence, hazard category, incident type, safety indicators, repeat-pattern indicators, recommended action, and supporting phrase).
- **Deterministic triage rules (`LogicManager`):** Applies safety escalation (high severity + fire/electrical hazard), injury/uncontrolled-hazard overrides, reporter–AI contradiction guards, 30-day recurrence checks, and near-duplicate detection.
- **SQLite / PostgreSQL persistence (`DataManager` & `Incident`):** Stores every processed incident across four normalised SQLAlchemy tables (`Incidents`, `io_manager`, `ai_manager`, `logic_manager`) with atomic inserts and history queries.
- **Analytics dashboard (`StatsService` & `HomeView`):** Computes severity, category, queue distributions, 14-day per-day incident counts, 30-day recurrence hotspots, and week-over-week rising hazard alerts rendered at `/`.

---

## Object-Oriented Architecture

The system preserves the four separated manager responsibilities alongside domain, analytics, configuration, and web layers:

- **`IOManager` (`IOManager.py`):** Input encapsulation/validation, search helpers, record formatting, and `IOManager.notify()` for Flask flash alerts.
- **`AIManager` (`ai_manager.py` + `ai_modules/`):** Composes `PromptBuilder` and `ResponseValidator`, and delegates transport to the `LLMClient` ABC (`ZaiLLMClient` for Z.ai GLM, `RetryableLLMClient` decorator for transient error retries, `TestLLMClient` for offline tests).
- **`LogicManager` (`logic_manager.py`):** Applies deterministic safety rules, severity/risk scoring, recurrence checks, duplicate detection, and queue routing (`Immediate Action`, `Priority Review`, `Recurring Review`, `Routine Log`, `Manual Review`).
- **`DataManager` (`data_manager.py`) & Domain Aggregate (`dashboard/`):** Persists `Incident` aggregates composed of `SectionObject` subclasses (`InputSection`, `AISection`, `LogicSection`) to SQLAlchemy ORM models (`dashboard/models.py`).
- **Analytics & Config Packages (`dashboard/analytics/`, `dashboard/config/`):** `StatsService` (composing `IncidentDatetimeParser` and returning `TrendPoint`, `Hotspot`, `RisingPattern` dataclasses), `DatabaseUrlResolver` / `Config` / `DevConfig` / `TestConfig`, Flask factory (`dashboard/__init__.py`), and `HomeView` (`dashboard/routes.py`).

```text
User / Browser  ──▶  Flask App (app.py / HomeView)  ──▶  StatsService (Analytics)
                            │
                            ▼
    IOManager  ──▶  AIManager (PromptBuilder + ResponseValidator + LLMClient)
                            │
                            ▼
                    LogicManager  ──▶  DataManager (Incident + SQLAlchemy Models)
```

---

## Environment Variables

Copy `.env.example` to `.env` before running with live AI features (`.env` is git-ignored; **never commit secrets**):

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ZAI_KEY` | For live AI triage | — | API key for the Z.ai OpenAI-compatible GLM endpoint (`ZaiLLMClient`) |
| `SECRET_KEY` | Recommended in prod | `dev-only-secret-key-change-me` | Flask session & CSRF protection secret |
| `DATABASE_URL` | Optional | `sqlite:///data/incidents.db` | SQLAlchemy database URI (`postgres://` normalised automatically to `postgresql://`) |
| `FLASK_DEBUG` | Optional | `True` (via `DevConfig`) | Set to `false` in containers/production |
| `HOST` / `PORT` | Optional | `0.0.0.0` / `5000` | Web server bind address and port |
| `WEBSITES_PORT` | Azure App Service | `5000` | Tells Azure App Service which port the container listens on |

---

## Local Setup & Running

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python -m flask --app app init-db
python app.py
```

Open `http://127.0.0.1:5000/` in your browser.

To populate sample data for exploring the analytics dashboard:

```bash
python -m scripts.seed_demo_data --force
```

---

## Automated Tests (Offline — No API Key Required)

All automated test suites run completely offline using scripted/mocked AI responses (`TestLLMClient`) and temporary SQLite databases (`TestConfig`):

```bash
python test_logic_manager.py
python test_ai_manager.py
python test_sections.py
python test_config.py
python -m unittest test_incident_sqlite test_data_manager
python -m unittest discover -s tests -v
python test_end_to_end.py
```

---

## Docker & CI

The `Dockerfile` in the repository root builds a self-contained `python:3.14-slim` image, initialises the SQLite database on startup, persists `/app/data` via a volume, exposes port `5000`, and starts the Flask web application (`app.py`).

### Build the image

```bash
docker build -t incident-triage:latest .
```

### Run the web application in Docker

```bash
docker run --rm -p 5000:5000 --env-file .env -v incident-data:/app/data incident-triage:latest
```

Then visit `http://127.0.0.1:5000/`.

### Run all automated test suites inside Docker

```bash
docker run --rm incident-triage:latest python test_logic_manager.py
docker run --rm incident-triage:latest python test_ai_manager.py
docker run --rm incident-triage:latest python test_sections.py
docker run --rm incident-triage:latest python test_config.py
docker run --rm incident-triage:latest python -m unittest test_incident_sqlite test_data_manager
docker run --rm incident-triage:latest python -m unittest discover -s tests
docker run --rm incident-triage:latest python test_end_to_end.py
```

GitHub Actions (`.github/workflows/ci.yml`) runs every test suite on the host, builds the Docker image, and re-runs every suite inside the built container on every push and pull request.

---

## Deployment (Azure App Service + PostgreSQL + Docker image)

The CD workflow (`.github/workflows/cd.yml`) deploys the **same Docker image the Dockerfile defines** to Azure App Service: it builds, pushes to GitHub Container Registry, and releases the image in one run so the deployment promotes the exact artifact built by CI.

Two database environments coexist via `DatabaseUrlResolver` (`dashboard/config/database_url_resolver.py`):

| Environment | Database | Trigger |
|---|---|---|
| Local, Docker, tests | SQLite (auto-created) | `DATABASE_URL` unset (default) |
| Azure deployment | PostgreSQL | `DATABASE_URL` injected by the cloud database |

The models are dialect-agnostic ORM, so no application code differs between the two.

Setup steps (detailed at the top of `.github/workflows/cd.yml`):

1. Create an Azure App Service (Linux) and an Azure Database for PostgreSQL Flexible Server.
2. Set `DATABASE_URL`, `ZAI_KEY`, `SECRET_KEY`, and `WEBSITES_PORT=5000` as App Service environment variables.
3. Store the App Service publish profile as the GitHub secret `AZURE_PUBLISH_PROFILE` and set the App Service name in `cd.yml`.
4. After the first CD run, set the pushed GHCR package to **Public** so App Service can pull it.
5. Enable App Service Authentication (Easy Auth) and allow-list the team's emails, then run the **CD** workflow (or uncomment its push trigger to deploy on every commit to `phase3/dev`).
6. In App Service, set the startup command to `startup.sh` (`init-db` + `FLASK_DEBUG=false` + `python app.py`).

Seed the deployed database with demo data:

```bash
az webapp ssh --name <app-service-name>
python scripts/seed_demo_data.py --force
```
