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
  +-- LLMClient  (abstract base class, the transport contract)
        |-- ZaiLLMClient           real Z.ai OpenAI-compatible endpoint
        |-- RetryableLLMClient     wraps ANY client, retries transient failures
        +-- TestLLMClient          scripted replies for offline tests
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