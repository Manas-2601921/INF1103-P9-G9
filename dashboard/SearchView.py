"""Read-only incident search with shareable GET filters."""
from datetime import date, datetime, time, timedelta
from math import ceil

from flask import current_app, render_template, request, url_for
from flask.views import MethodView

import managers
from data_manager import DataLoadError, DataManager


class SearchView(MethodView):
    PAGE_SIZE = 20
    SEVERITIES = {"low": "Low", "medium": "Medium", "high": "High", "unassessed": "Not assessed"}
    QUEUES = ("Immediate Action", "Priority Review", "Recurring Review", "Routine Log", "Manual Review")
    FIELDS = ("record_id", "incident_name", "name_match", "hazard_category", "location",
              "severity", "final_queue", "injury_reported", "date_mode", "date_from",
              "date_to", "specific_datetime")

    def get(self):
        form = {key: request.args.get(key, "").strip() for key in self.FIELDS}
        form["record_id"] = form["record_id"].upper()
        form["name_match"] = form["name_match"] or "contains"
        form["date_mode"] = form["date_mode"] or "any"
        errors, filters, terms = {}, {}, []
        choices = {"name_match": ("contains", "exact"), "severity": tuple(self.SEVERITIES),
                   "final_queue": self.QUEUES, "injury_reported": ("yes", "no"),
                   "date_mode": ("any", "range", "exact")}
        for key, allowed in choices.items():
            if form[key] and form[key] not in allowed:
                errors[key] = "Select a valid option."
        if form["record_id"] and DataManager._record_id_number(form["record_id"]) is None:
            errors["record_id"] = "Enter a record ID such as INC-0001."
        for key, label in (("record_id", "ID"), ("incident_name", "Title"),
                           ("hazard_category", "Hazard"), ("location", "Location"),
                           ("severity", "Severity"), ("final_queue", "Queue")):
            if form[key]:
                filters[key] = form[key]
                terms.append(f"{label}: {form[key]}")
        filters["exact_name"] = form["name_match"] == "exact"
        if form["incident_name"]:
            terms.append("Exact title" if filters["exact_name"] else "Title contains text")
        if form["injury_reported"] in ("yes", "no"):
            filters["injury_reported"] = form["injury_reported"] == "yes"
            terms.append("Injury reported: " + form["injury_reported"])
        if form["date_mode"] == "range":
            if not form["date_from"] and not form["date_to"]:
                errors["date_from"] = "Choose a start date, an end date, or both."
            for key, bound in (("date_from", "start_datetime"), ("date_to", "end_datetime")):
                if form[key]:
                    try:
                        value = date.fromisoformat(form[key])
                        filters[bound] = datetime.combine(value, time.min if key == "date_from" else time.max)
                        terms.append(("From: " if key == "date_from" else "Through: ") + value.strftime("%d %b %Y"))
                    except ValueError:
                        errors[key] = "Enter a valid date."
            if "start_datetime" in filters and "end_datetime" in filters and filters["start_datetime"] > filters["end_datetime"]:
                errors["date_to"] = "End date cannot be earlier than start date."
        elif form["date_mode"] == "exact":
            try:
                if "T" not in form["specific_datetime"]:
                    raise ValueError
                value = datetime.fromisoformat(form["specific_datetime"])
                if value.utcoffset() is not None:
                    raise ValueError
                value = value.replace(second=0, microsecond=0)
                filters["start_datetime"] = value
                filters["end_datetime"] = value + timedelta(seconds=59, microseconds=999999)
                terms.append("During: " + value.strftime("%d %b %Y, %H:%M"))
            except (ValueError, OverflowError):
                errors["specific_datetime"] = "Choose a valid date and time."
        raw_page = request.args.get("page", "1")
        page = int(raw_page) if raw_page.isascii() and raw_page.isdigit() and len(raw_page) <= 9 else 0
        if page < 1:
            errors["page"] = "Page must be a positive whole number."
            page = 1
        incidents, categories, failed = [], [], False
        try:
            categories = managers.io_manager.get_all_incident_categories()
            if not errors:
                incidents = managers.io_manager.search_incidents(**filters)
        except DataLoadError:
            current_app.logger.exception("Failed to search incidents")
            managers.io_manager.notify("Incidents could not be loaded. Please try again later.")
            failed = True
        total = len(incidents)
        pages = max(1, ceil(total / self.PAGE_SIZE))
        page = min(page, pages)
        first = (page - 1) * self.PAGE_SIZE
        query_args = {key: value for key, value in form.items() if value}
        def page_url(number):
            return url_for("dashboard.search", **query_args, page=number)
        return render_template(
            "search.html", form=form, errors=errors, failed=failed,
            incidents=incidents[first:first + self.PAGE_SIZE], total=total,
            query_text="; ".join(terms) or "All incidents", categories=categories,
            severities=self.SEVERITIES, queues=self.QUEUES,
            format_datetime=managers.io_manager.format_incident_datetime,
            severity_band=DataManager.severity_band, page=page, pages=pages,
            first=first + 1 if total else 0, last=min(first + self.PAGE_SIZE, total),
            previous_url=page_url(page - 1) if page > 1 else None,
            next_url=page_url(page + 1) if page < pages else None,
        ), 500 if failed else 400 if errors else 200
