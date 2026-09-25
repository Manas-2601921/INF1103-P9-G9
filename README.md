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