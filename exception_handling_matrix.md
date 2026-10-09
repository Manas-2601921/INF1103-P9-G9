# Exception Handling Matrix — AI Manager

Scope: the full `ai_manager` call flow and every exception that can be raised,
where it is caught, and what the caller receives.

## 1. Call flow

```text
ai_manager(record_json)
 ├─ validate_record_json        (input-side, raises TypeError / KeyError)
 ├─ validate_incident_json      (input-side, raises TypeError / KeyError)
 ├─ build_user_prompt           (no exceptions expected)
 ├─ build_analysis_messages     (no exceptions expected)
 └─ loop, max 3 validation attempts:
     ├─ retry_api_call          (wraps zai_connector, 3 API attempts;
     │                           raises non-retryable errors immediately)
     │   └─ zai_connector       (raises ValueError on missing key or
     │                           malformed response, APIError family otherwise)
     ├─ validate_ai_output      (never raises; returns errors as a list)
     │   └─ parse_reply         (raises ValueError, caught internally)
     └─ build_retry_messages    (no exceptions expected; input already validated)
```

## 2. Matrix

| # | Stage / function | Exception | Trigger / cause | Caught by | Handling action | Caller-visible result |
|---|------------------|-----------|-----------------|-----------|-----------------|-----------------------|
| 1 | `validate_record_json` | `TypeError` | `record_json` is not a dict (e.g. str, list, None passed in) | `ai_manager` — `except (TypeError, KeyError)` | Error converted to message | `(None, "Invalid record or incident json input: …")` |
| 2 | `validate_record_json` | `KeyError` | `input` section missing from the record | `ai_manager` — `except (TypeError, KeyError)` | Error converted to message | `(None, "Invalid record or incident json input: …")` |
| 3 | `validate_incident_json` | `TypeError` | `input` section is not a dict | `ai_manager` — `except (TypeError, KeyError)` | Error converted to message | `(None, "Invalid record or incident json input: …")` |
| 4 | `validate_incident_json` | `KeyError` | One or more required incident fields missing (message names every missing key) | `ai_manager` — `except (TypeError, KeyError)` | Error converted to message | `(None, "Invalid record or incident json input: …")` |
| 5 | `zai_connector` (openai client) | Retryable `APIError` family — `APIConnectionError`, `APITimeoutError`, `RateLimitError`, `InternalServerError` | Network failure, timeout, 429 or 5xx from the Z.ai endpoint — may succeed on retry | `retry_api_call` — `except (APIError, ValueError)` | Sleep 1 s, then 6 s, retry; after 3 attempts re-raised as `ValueError` | see row 8 |
| 6 | `zai_connector` (openai client) | Non-retryable `APIError` family — `AuthenticationError`, `PermissionDeniedError`, `BadRequestError`, `NotFoundError`, `UnprocessableEntityError` | 401/403/400/404/422 — invalid key or malformed request; retrying can never succeed | `retry_api_call` — `except NON_RETRYABLE_ERRORS` (matched before the generic clause) | Raised immediately as `ValueError`, no attempt consumed | see row 8 |
| 7 | `zai_connector` | `ValueError` | `ZAI_KEY` missing/empty, or API responded but `choices` is empty or message content is `None` | Missing key: re-checked by `retry_api_call` before the loop, so no attempt is consumed; malformed response: retried via `except (APIError, ValueError)` | Fail fast (missing key) or retry-then-raise (malformed response) | see row 8 |
| 8 | `retry_api_call` | `ValueError` (raised, not caught internally) | Non-retryable error, missing key, or any row 5/7 error persisting across all 3 API attempts | `ai_manager` — `except ValueError` | Error converted to message | `(None, "Malformed API response was returned: …")` |
| 9 | `parse_reply` | `ValueError` | Reply is empty or is not text (e.g. `None`) | `validate_ai_output` — internal `try/except ValueError` | Returns `({}, [message])`; counts as a failed validation attempt | Reprompt; see row 13 |
| 10 | `parse_reply` | `json.JSONDecodeError` (subclass of `ValueError`) | Reply is not valid JSON, including after markdown-fence stripping | `validate_ai_output` — internal `try/except ValueError` | Same as row 9 | Reprompt; see row 13 |
| 11 | `parse_reply` | `ValueError` | Reply is valid JSON but not an object (e.g. a list) | `validate_ai_output` — internal `try/except ValueError` | Same as row 9 | Reprompt; see row 13 |
| 12 | `check_fields` / `check_scores` / `check_enums` | none — violations are collected, not raised | Missing fields, wrong types, scores outside 0.0–1.0, invalid enum values, boolean where number expected | n/a | Violations appended to `errors` list; list feeds `build_retry_messages` | Reprompt with the violations; after 3 failed attempts: `(None, "AI output failed schema validation after 3 attempts: […]")` |
| 13 | `build_retry_messages` | none expected | Field access on `incident_json` | n/a | Cannot occur — `incident_json` already validated by rows 1–4 | — |

## 3. Caller-visible outcomes of `ai_manager`

| Scenario | Return value |
|----------|--------------|
| Reply passes schema validation (any attempt) | `(True, parsed_analysis_dict)` |
| Record / incident JSON structurally invalid | `(None, "Invalid record or incident json input: …")` |
| API key missing | `(None, "Malformed API response was returned: ZAI_KEY is not set …")` — fails on the spot, no attempts consumed |
| Non-retryable API error (401/403/400/404/422) | `(None, "Malformed API response was returned: API call failed with a non-retryable error: …")` — raised after 1 attempt |
| Transient API error or malformed response after 3 API retries | `(None, "Malformed API response was returned: API call failed after 3 attempts: …")` |
| Reply breaks the schema on all 3 validation attempts | `(None, "AI output failed schema validation after 3 attempts: […]")` |

## 4. Resolved gaps and remaining notes

1. ~~**`OpenAIError` is uncaught.**~~ **Resolved:** `zai_connector` now raises
   `ValueError` when `ZAI_KEY` is missing, and `retry_api_call` re-checks the key
   before the loop so a missing key consumes zero attempts. The crash path is closed.
2. ~~**Non-retryable errors are retried.**~~ **Resolved:** `retry_api_call` now has a
   dedicated `except NON_RETRYABLE_ERRORS` clause (matched before the generic
   `(APIError, ValueError)` clause) that raises immediately for 401/403/400/404/422.
   Only transient errors — connection failures, timeouts, 429, 5xx — consume retries.
3. **Worst-case latency before a failure return.** A persistently *transient* failing
   endpoint still costs 3 API attempts with 1 s + 6 s backoff per validation attempt;
   across 3 validation attempts that is roughly 21 s of pure backoff plus 9 API calls
   before the caller sees `(None, …)`. Non-retryable failures now return after a
   single call.
4. **Cosmetic:** `ai_manager` wraps every API-layer failure — including
   non-retryable auth errors — as `"Malformed API response was returned: …"`. The
   nested message clarifies the real cause, but the outer wording could be more
   accurate (e.g. "API call failed").
