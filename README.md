# Workplace Incident Triage Assistant

An AI-assisted terminal application that analyses unstructured workplace incident reports, classifies their severity and hazard type, and prioritises them for appropriate follow-up.

The project is designed for small and medium-sized organisations, with an initial focus on Singapore Workplace Safety and Health (WSH) reporting.

---

## Overview

Workplace incident reports are often submitted as unstructured free-text descriptions. Important hazards, repeated near-misses, or serious incidents may therefore be difficult to identify consistently.

This application provides an initial incident-triage process by:

- Extracting important information from incident descriptions
- Classifying incident severity
- Identifying hazard categories
- Detecting recurring incidents
- Applying business rules for escalation
- Storing processed incident records for future analysis

The system provides **triage support only** and does not replace a qualified workplace safety investigation.

---

## Application Flow

```text
User
  |
  v
I/O Manager
  |
  v
AI Manager
  |
  v
Logic Manager
  |
  v
Data Manager
  |
  v
Stored Incident Record / Result

---

## AI Manager Architecture (object-oriented)

The AI manager (`ai_manager.py`) is a class, `AIManager`, that orchestrates
one incident analysis: validate the shared record, build the prompt, query
the LLM, validate the reply and reprompt on schema violations.

Its collaborators live in `ai_modules/`:

```text
AIManager  (composes PromptBuilder + ResponseValidator, uses one LLMClient)
  |
  +-- PromptBuilder                ai_modules/prompt_builder.py
  |     builds analysis / retry chat prompts (owns the schema contract text)
  |
  +-- ResponseValidator            ai_modules/response_validator.py
  |     validates every raw reply against the reply schema
  |
  +-- LLMClient                     ai_modules/llm_client.py
        abstract base class, the transport contract
        |-- ZaiLLMClient           ai_modules/zai_llm_client.py
        |     real Z.ai OpenAI-compatible endpoint
        |-- RetryableLLMClient     ai_modules/retryable_llm_client.py
        |     wraps ANY client, retries transient failures
        +-- TestLLMClient          ai_modules/test_llm_client.py
              scripted replies for offline tests
```

Design notes:

- `LLMClient` is an abstract base class (interface): `AIManager` and the
  retry wrapper only call its `complete` method, so the real API and the
  offline test client are interchangeable (polymorphism / LSP).
- The prompt builder and response validator are created inside `AIManager`
  (composition); the LLM client is supplied from outside (aggregation), so
  tests inject a `TestLLMClient` and future backends can be added without
  modifying the manager (OCP).
- `RetryableLLMClient` is itself an `LLMClient`, so retry behaviour is added
  to any backend by wrapping it (inheritance + decorator pattern).
- Configuration (attempt limits, backoff) is passed via the `AIManager`
  constructor; internals use `_`-prefixed private attributes and methods
  (encapsulation).

The test suite (`test_ai_manager.py`) runs fully offline by injecting the
test client; `--live` switches to the real API.

---

## Deployment (Azure App Service + PostgreSQL)

Locally and in Docker the app runs on SQLite with no configuration. A
deployed environment switches to PostgreSQL automatically via the
`DATABASE_URL` environment variable (see `dashboard/config.py`); the
models are dialect-agnostic, so no application code differs between the
two.

| Environment variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (set by the cloud database; unset locally) |
| `ZAI_KEY` | Z.ai API key used by the AI manager |
| `SECRET_KEY` | Flask session/CSRF secret |

Setup steps (detailed at the top of `.github/workflows/cd.yml`):

1. Create an Azure App Service (Linux, Python) and an Azure Database for
   PostgreSQL Flexible Server.
2. Set `DATABASE_URL`, `ZAI_KEY` and `SECRET_KEY` as App Service
   environment variables.
3. Set the startup command to `startup.sh` — it runs
   `flask --app app init-db` (creates any missing tables) and starts the
   web dashboard.
4. Enable App Service Authentication (Easy Auth) and allow-list the
   team's emails, keeping the public URL private to the team.
5. Store the App Service publish profile as the GitHub secret
   `AZURE_PUBLISH_PROFILE`, then run the **CD** workflow (Actions tab) —
   or uncomment its push trigger to deploy on every commit to
   `phase3/dev`.

Seed the deployed database with demo data:

```bash
az webapp ssh --name <app-service-name>
python scripts/seed_demo_data.py --force
```