# Workplace Incident Triage Assistant

**Topic Approval and Project Scope Validation — Team Project Proposal**

## Scope

A procedural, AI-assisted terminal application for small and medium-sized companies that analyses unstructured workplace incident reports and prioritises them for appropriate follow-up. It supports near-misses, safety hazards and workplace complaints, with an initial focus on Singapore Workplace Safety and Health (WSH) reporting needs.

## 1. Problem Statement and Target Users

Small and medium-sized companies may receive many unstructured incident reports but lack the time or specialist resources to assess them consistently. Important hazards can be buried in free-text descriptions, while repeated near-misses may not be recognised as a pattern. Delayed escalation of a serious incident can increase the likelihood of injury, property damage or regulatory consequences. The application will standardise the first stage of incident triage by extracting key information, assigning an initial severity, detecting hazard categories and identifying recurring patterns.

Target users are workplace safety officers, operations managers, supervisors, HR personnel and designated incident reporters in small and medium-sized organisations. The system provides triage support rather than a legal determination or replacement for a qualified safety investigation. Its local relevance is strong because workplace safety and health compliance is a regulated responsibility in Singapore.

## 2. User Inputs

- Free-text incident description, including what happened, the hazard observed, people or equipment involved, and any immediate action taken.
- Incident location, such as a workshop, office, warehouse, laboratory or construction area.
- Reporter role, such as employee, supervisor, visitor, contractor or safety officer.
- Optional date and time, department, affected activity, injury status and immediate containment action.
- Optional confirmation of whether the incident is related to an existing or previous report.

The I/O Manager will collect the information through validated terminal prompts. It will reject blank descriptions, invalid dates, unsupported menu selections and missing locations or reporter roles, then re-prompt the user.

## 3. Use of AI

Every incident record passes through the AI Manager because the central challenge is interpreting unstructured descriptions rather than matching fixed fields. The AI will analyse the incident text and return a validated JSON response containing:

- **Severity:** low, medium or high, with a short evidence-based explanation.
- **Hazard category:** electrical, fire, chemical, ergonomic, slip/trip/fall, mechanical, biological, psychosocial or other.
- **Incident type:** near-miss, injury, unsafe condition, property damage or complaint.
- **Extracted indicators:** injury, immediate danger, exposure, equipment involvement and work stoppage.
- **Repeat-pattern indicators:** hazard keywords, location, activity or description features that may be comparable with earlier incidents.
- **Recommended immediate action** and the exact supporting phrase from the report.

The AI Manager will build the prompt, call the AI API, parse the response and validate its schema, allowed categories and required fields. It will retry malformed output and record API failures without crashing. The AI suggests an initial classification; the Logic Manager makes the final queue and escalation decision.

## 4. Business Rules

- High severity plus a fire or electrical hazard: automatically assign the incident to the **Immediate Action** queue and require supervisor or safety-officer escalation.
- Low severity plus a similar incident at the same location within the previous 30 days: flag it as **Recurring — Root-Cause Review**.
- Any incident indicating injury, imminent danger or an uncontrolled hazard cannot be assigned to a routine queue, even if the AI suggests low severity.
- An incident with missing, contradictory or low-confidence AI output is assigned to **Manual Review** rather than being silently accepted.
- A report is considered similar to a previous report when the hazard category and location match and the AI identifies a shared hazard keyword or activity pattern.
- The Logic Manager retains the AI explanation and evidence phrase but applies the final status: **Immediate Action, Priority Review, Routine Log, Recurring Review or Manual Review**.
- Duplicate submissions are identified using incident date, location, category and text similarity. Possible duplicates are flagged for confirmation rather than discarded automatically.

These rules make the Logic Manager essential: it combines AI-extracted fields with incident history, time windows, location and escalation policy to decide what operational action is required.

## 5. Data Manager and Architecture

The Data Manager stores all processed incidents in JSON or CSV, including the original description, date, location, reporter role, AI output, final queue, escalation status and timestamps. It loads the incident log on startup, creates the file if absent, and backs up and safely resets a missing or corrupt file without crashing. It provides queries such as:

- All high-severity incidents this month by location
- Recurring hazards in the last 30 days
- All incidents in the Immediate Action queue

The four procedural modules are:

- **I/O Manager:** terminal input, validation and display.
- **AI Manager:** prompt construction, API interaction, structured classification and error handling.
- **Logic Manager:** escalation, recurrence, duplicate and queue rules.
- **Data Manager:** persistence, filtering and incident history.

The project will use functions only, Docker, tests, clear interfaces and granular Git commits.

## 6. GitHub Repository

https://github.com/Manas-2601921/Group9Repo.git
