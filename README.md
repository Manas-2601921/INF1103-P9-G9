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

The system preserves the four separated manager responsibilities alongside shared AI orchestration, domain, analytics, configuration, recovery, and web layers (legacy terminal entrypoints retired):

- **`IOManager` (`IOManager.py`):** Input encapsulation/validation, search helpers (`search_incidents()`, `get_all_incident_categories()`, `format_incident_datetime()`), and `IOManager.notify()` for Flask flash alerts.
- **`IncidentAnalyzer` (`incident_analyzer.py`):** Wraps `managers.ai_manager` for web triage, converts numeric scores to bands (`to_severity_band()`), surfaces `RuntimeError` if AI deps are unavailable, and returns an `ai_error` Manual Review stub on failure.
- **`AIManager` (`ai_manager.py` + `ai_modules/`):** Composes `PromptBuilder` and `ResponseValidator`, and delegates transport to the `LLMClient` ABC (`ZaiLLMClient` for Z.ai GLM, `RetryableLLMClient` decorator for transient error retries, `TestLLMClient` for offline tests).
- **`LogicManager` (`logic_manager.py`):** Applies deterministic safety rules, severity/risk scoring, recurrence checks, duplicate detection, and queue routing (`Immediate Action`, `Priority Review`, `Recurring Review`, `Routine Log`, `Manual Review`).
- **`DataManager` (`data_manager.py`) & Domain Aggregate (`dashboard/`):** Persists `Incident` aggregates composed of `SectionObject` subclasses (`InputSection`, `AISection`, `LogicSection`) to SQLAlchemy ORM models (`dashboard/models.py`), invoking `recover_corrupt_sqlite()` (`dashboard/database_recovery.py`) on confirmed local SQLite corruption.
- **Web Views, Analytics & Config (`dashboard/`):** Five Flask `MethodView` routes (`HomeView` `/`, `AddIncidentView` `/incidents/add`, `SearchView` `/search` with OWASP-safe CSV export, `IncidentsView` `/incidents`, `IncidentDetailsView` `/incidents/<record_id>`), `StatsService` (`dashboard/analytics/`), `DatabaseUrlResolver` / `Config` / `DevConfig` / `TestConfig`, and `create_app()` with Werkzeug `ProxyFix`.

```text
User / Browser  ──▶  Flask App (app.py + MethodViews: /, /incidents/add, /search, /incidents)
                            │
                            ├──▶  StatsService (Analytics Dashboard)
                            ▼
    IOManager  ──▶  IncidentAnalyzer / AIManager (PromptBuilder + ResponseValidator + LLMClient)
                            │
                            ▼
                    LogicManager  ──▶  DataManager (Incident + ORM Models + SQLite Recovery)
```

---

## Web application views

- **`/` (`HomeView`):** Incident trends analytics dashboard (metric cards, Chart.js visualisations, 30-day recurrence hotspots, rising pattern warnings).
- **`/incidents/add` (`AddIncidentView`):** Validated report submission (`GET`/`POST` with PRG redirect to details); runs live AI analysis via `IncidentAnalyzer` + `LogicManager` triage rules and falls back to `Manual Review` on AI failure.
- **`/search` (`SearchView`):** Multi-filter search (`record_id`, contains/exact `incident_name`, `hazard_category`, `location`, `severity`, `final_queue`, `injury_reported`, date range or specific minute), AJAX sorting across 7 columns, removable filter chips, pagination (`10`/`20`/`50`/`100`), and formula-safe CSV export (`export=csv`).
- **`/incidents` (`IncidentsView`) & `/incidents/<record_id>` (`IncidentDetailsView`):** Browse all incidents and view structured Inputs / Review / Repeating unsafe practices / Recommendation reports (preserving filtered `?search=` return links and redirecting unknown IDs safely).

## Incident query contract

`DataManager.load()`, `query()`, the named incident query helpers, and
`IOManager.find_by_*()` return `Incident` objects (`list[Incident]`).
`get_by_record_id()` returns one `Incident` or `None`. Convert with
`incident.to_dict()` at boundaries that require dictionaries, such as the
existing triage rules, console formatting, or the details template.
Summary dictionaries and category strings remain presentation projections.

`query(*criteria)` accepts SQLAlchemy expressions combined with AND, not
Python callbacks. ID and named equality/title/category queries filter in SQL;
category options use a distinct SQL projection. Relationships are loaded
before the session closes so returned objects remain usable.

Combined search narrows text and boolean filters in SQL first.
Date-range/parsed-datetime searches and numeric legacy-severity filtering
still run in Python on those candidates: existing text dates have multiple formats and legacy
severity JSON mixes numbers, numeric strings, and bands. Moving those filters
fully into SQL requires normalising their stored representations first.

---

## Search and query pages (Pair B)

Open `/search` or choose **Search incidents** in the navigation. Title searches
use literal, case-insensitive partial matching by default; choose **Exact title**
for the CLI-style full-name match. Combine record ID, hazard, location, severity,
review queue, injury status, and date filters; every selected filter must match.
An empty search browses all incidents. URLs preserve filters for bookmarking.

Date ranges include the entire end date and allow either bound to be omitted.
**Specific date and minute** matches any second within the selected minute.
Dates use reported local time; timezone-aware and naive timestamps are not mixed.
Results show a count and query summary, with 20 records per page and a link to
incident details. The detail page follows Inputs / Review / Repeating unsafe
practices / Recommendation and preserves the return link to filtered results.

`DataManager.query_record_id`, `query_incident_name`, and `query_datetime_range`
return `Incident` lists. `IOManager` delegates existing CLI date searches to the
same database-layer parser and exposes `search_incidents` for the web view.
Confirmed local SQLite corruption is preserved and reset as described below.
Other database read failures display an error without resetting the database.

---

## Corrupt SQLite database recovery

On a confirmed SQLite `SQLITE_CORRUPT` or `SQLITE_NOTADB` error during incident
reads, category reads, or `init-db`, the app:

1. Closes its failed read session and pooled database connections.
2. Copies the damaged file beside the original as
   `incidents.corrupt-<UTC timestamp>-<unique suffix>.db`.
3. Builds all four tables in a separate temporary database, then replaces the
   damaged database only after the backup and new schema succeed.
4. Returns an empty result and logs a warning. Web requests also show a warning
   explaining where the previous database was preserved.

This preserves the damaged file; it does **not** restore the old incidents.
New incidents can be saved to the replacement database. A failed backup or
replacement leaves the original database in place and reports an error.

Recovery is attempted once per app instance. If another corruption or recovery
failure occurs, stop the app and inspect the files before restarting. Missing
schema, invalid incident section graphs, locked/read-only databases, disk-full
errors, and write failures never trigger automatic reset. PostgreSQL, in-memory
SQLite, and SQLite URI databases are excluded.

This is intended for the single-process local coursework app. Automatic reset
is refused if SQLite journal/WAL sidecars were present before the failing read
or remain during recovery. Stop every process using that database and inspect
it manually in that case. Scheduled backups, concurrent-process recovery, and
record salvage are outside this feature's scope.

Recovery tests use disposable temporary databases, not `data/incidents.db`.

---

## Environment Variables

Copy `.env.example` to `.env` before running with live AI features (`.env` is git-ignored; **never commit secrets**):

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ZAI_KEY` | For live AI triage | — | API key for the Z.ai OpenAI-compatible GLM endpoint (`ZaiLLMClient`) |
| `SECRET_KEY` | Recommended in prod | `dev-only-secret-key-change-me` | Flask session & CSRF protection secret |
| `DATABASE_URL` | Optional | `sqlite:///data/incidents.db` | SQLAlchemy database URI (`postgres://` normalised automatically to `postgresql://`) |
| `SQLALCHEMY_ECHO` | Optional | `false` | Print SQL statements and bound parameters to the console |
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

To inspect the SQL sent to the database, enable the built-in SQLAlchemy engine
logger before starting the app (PowerShell):

```powershell
$env:SQLALCHEMY_ECHO = "true"
.\.venv\Scripts\python.exe app.py
```

For Windows CMD:

```cmd
set SQLALCHEMY_ECHO=true
.venv\Scripts\python.exe app.py
```

Requests now print SQL, bound parameters, and transaction messages in the server
console. Parameters can contain incident text. To turn logging off, stop the
server, set `$env:SQLALCHEMY_ECHO = "false"`, and restart it. Python-side legacy
date/severity filters do not generate extra SQL log entries.

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

The CD workflow (`.github/workflows/cd.yml`) is gated behind CI (`.github/workflows/ci.yml` via `workflow_call`, `needs: ci`), builds the `Dockerfile` image, pushes it to **Azure Container Registry** (`inf1103.azurecr.io/incident-triage`), and deploys automatically on pushes to `main` (or manually via `workflow_dispatch`) to Azure App Service (`inf1103`).

Two database environments coexist via `DatabaseUrlResolver` (`dashboard/config/database_url_resolver.py`):

| Environment | Database | Trigger |
|---|---|---|
| Local, Docker, tests | SQLite (auto-created) | `DATABASE_URL` unset (default) |
| Azure deployment | PostgreSQL | `DATABASE_URL` injected by the cloud database |

The models are dialect-agnostic ORM (`psycopg[binary]` + `psycopg2-binary`), and `create_app()` automatically enables Werkzeug `ProxyFix` + secure session cookie flags when `WEBSITE_SITE_NAME` or `ENABLE_PROXY_FIX=true` is present.

Setup summary (also documented at the top of `.github/workflows/cd.yml`):

1. Azure App Service (Linux container `inf1103`, `WEBSITES_PORT=5000`), Azure Container Registry (`inf1103.azurecr.io`), and Azure Database for PostgreSQL Flexible Server (`inf1103-pg-eastasia`).
2. App Service environment variables: `DATABASE_URL`, `ZAI_KEY`, `SECRET_KEY`, and `WEBSITES_PORT=5000`.
3. GitHub repository secrets: `AZURE_PUBLISH_PROFILE`, `ACR_USERNAME`, and `ACR_PASSWORD`.
4. App Service Authentication (Easy Auth) with Google OAuth allow-listing authorised test users (`HTTP 302`/`401` at the edge; checked by the post-deploy smoke test).

Seed the deployed PostgreSQL database from a workstation or container whose IP is permitted in PostgreSQL networking:

```powershell
$env:DATABASE_URL = "<DATABASE_URL from Azure App Service Environment Variables>"
python scripts/seed_demo_data.py --force
Remove-Item Env:DATABASE_URL
```
