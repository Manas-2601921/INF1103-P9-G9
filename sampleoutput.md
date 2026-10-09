# Incident Triage Assistant

## Main Menu

```
Hello! Welcome to Incident Triage Assistant
What would you like to do today?
1. Submit a new Incident
2. View Incident Summary (What does this do?)
3. Search for a particular Incident
4. Exit
Enter your option number here:
```

---

## Option 1: Submit a New Incident

- Prompt the user for incident details
- Validate the inputs

---

## Option 2: View Incident Summary

> *(To be defined. Note: the menu includes a "What does this do?" help prompt that needs an explanation.)*

---

## Option 3: Search for a Particular Incident

```
What would you like to search by:
1. Title
2. Category
3. Date
Enter your option number here:
```

### After the user selects a search option

```
12 Search Results for '<user_search_query>':

#1 Falling of ladder
A worker was painting the building when he fell off the ladder
Incident Date: 16/09/2004 Location: Clarke Quay

#1 Falling of ladder
A worker was painting the building when he fell off the ladder
Incident Date: 16/09/2004 Location: Clarke Quay

#1 Falling of ladder
A worker was painting the building when he fell off the ladder
Incident Date: 16/09/2004 Location: Clarke Quay

Would you like to view more details of any particular incident? (yes/no):
```

### If the user selects "yes": display incident details

**Inputs**

| Field | Description |
|---|---|
| `incidentname` | Name/title of the incident |
| `description` | What happened |
| `location` | Where it happened |
| `reporter_role` | Role of the person reporting |
| `incident_datetime` | Date and time of the incident |
| `injury_reported` | Whether an injury was reported |

**Review**

| Field | Source | Notes |
|---|---|---|
| `final_queue` | Logic | Queue the incident is routed to |
| `severity_explanation` | AI | Explains why the severity level was assigned |
| `hazard_category` | AI | Classification of the type of hazard involved (e.g. working at height, electrical, chemical) *(needs a user-facing explanation)* |
| `incident_type` | AI | Classification of the incident (e.g. injury, near miss, property damage) |

**Repeating unsafe practices**

Some repeating unsafe practices that we observed were:

`repeat_pattern_indicators`

**Recommendation**

From all our analysis and observations... we recommend that:

`recommended_immediate_action`

---

## Option 4: Exit