"""Read-only incident search with shareable GET filters."""
import csv
import io
from datetime import date, datetime, time, timedelta
from math import ceil

from flask import Response, current_app, render_template, request, url_for
from flask.views import MethodView

import managers
from dashboard.analytics.incident_datetime_parser import IncidentDatetimeParser
from data_manager import DataLoadError, DataManager

_SEVERITY_SORT_ORDER = {"high": 2, "medium": 1, "low": 0}
# Shared with the trends page so a "22-01-2026" row and a "2026-01-22T09:00:00"
# row sort the same way here as they do there.
_DATETIME_PARSER = IncidentDatetimeParser()


def _sort_key_record_id(incident):
    return DataManager._record_id_number(incident.record_id) or 0


def _sort_key_incident_name(incident):
    data = incident.input_section.manager_json if incident.input_section else {}
    return (data.get("incident_name") or "").strip().lower()


def _sort_key_incident_datetime(incident):
    """Sort by the parsed datetime, not the stored string.

    Legacy "DD-MM-YYYY HH:MM" rows and ISO rows must interleave by actual
    time, which raw string comparison cannot do (e.g. "31-12-2025" would
    sort before "2026-01-01" as text despite being later). Unparsed or
    missing values sort as the earliest possible date, mirroring how
    unassessed severity sorts below every known band. A timezone-aware
    value is normalised to naive by dropping its offset, since the rest of
    the app treats every stored incident_datetime as the reporter's local,
    offset-less time and never otherwise mixes aware and naive values.
    """
    data = incident.input_section.manager_json if incident.input_section else {}
    value = _DATETIME_PARSER.parse(data.get("incident_datetime"))
    if value is None:
        return datetime.min
    if value.utcoffset() is not None:
        value = value.replace(tzinfo=None)
    return value


def _sort_key_location(incident):
    data = incident.input_section.manager_json if incident.input_section else {}
    return (data.get("location") or "").strip().lower()


def _sort_key_hazard_category(incident):
    data = incident.ai_section.manager_json if incident.ai_section else {}
    return (data.get("hazard_category") or "").strip().lower()


def _sort_key_severity(incident):
    return _SEVERITY_SORT_ORDER.get(DataManager.severity_band(incident), -1)


def _sort_key_final_queue(incident):
    data = incident.logic_section.manager_json if incident.logic_section else {}
    return (data.get("final_queue") or "").strip().lower()


class SearchView(MethodView):
    PAGE_SIZE = 20
    PAGE_SIZES = (10, 20, 50, 100)
    SEVERITIES = {"low": "Low", "medium": "Medium", "high": "High", "unassessed": "Not assessed"}
    QUEUES = ("Immediate Action", "Priority Review", "Recurring Review", "Routine Log", "Manual Review")
    FIELDS = ("record_id", "incident_name", "name_match", "hazard_category", "location",
              "severity", "final_queue", "injury_reported", "date_mode", "date_from",
              "date_to", "specific_datetime", "sort", "dir")
    # Column key -> (header label, sort key function). Dict order sets header order.
    SORT_COLUMNS = {
        "record_id": ("ID", _sort_key_record_id),
        "incident_name": ("Incident", _sort_key_incident_name),
        "incident_datetime": ("Date and time", _sort_key_incident_datetime),
        "location": ("Location", _sort_key_location),
        "hazard_category": ("Hazard", _sort_key_hazard_category),
        "severity": ("Severity", _sort_key_severity),
        "final_queue": ("Queue", _sort_key_final_queue),
    }

    def get(self):
        form = {key: request.args.get(key, "").strip() for key in self.FIELDS}
        form["record_id"] = form["record_id"].upper()
        form["name_match"] = form["name_match"] or "contains"
        form["date_mode"] = form["date_mode"] or "any"
        form["sort"] = form["sort"] or "record_id"
        form["dir"] = form["dir"] or "asc"
        errors, filters, terms = {}, {}, []
        choices = {"name_match": ("contains", "exact"), "severity": tuple(self.SEVERITIES),
                   "final_queue": self.QUEUES, "injury_reported": ("yes", "no"),
                   "date_mode": ("any", "range", "exact"),
                   "sort": tuple(self.SORT_COLUMNS), "dir": ("asc", "desc")}
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

        # Removable filter chips: one per active filter (or group of related
        # fields, e.g. a title + its match mode, or the whole date filter),
        # built from the same conditions as `terms` so the two always agree.
        chips = []
        for key, label in (("record_id", "ID"), ("hazard_category", "Hazard"), ("location", "Location"),
                           ("severity", "Severity"), ("final_queue", "Queue")):
            if form[key]:
                chips.append({"text": f"{label}: {form[key]}", "keys": [key]})
        if form["incident_name"]:
            mode = "exact" if form["name_match"] == "exact" else "contains"
            chips.append({"text": f"Title ({mode}): {form['incident_name']}",
                          "keys": ["incident_name", "name_match"]})
        if form["injury_reported"] in ("yes", "no"):
            chips.append({"text": "Injury reported: " + form["injury_reported"].capitalize(),
                          "keys": ["injury_reported"]})
        date_terms = [term for term in terms if term.startswith(("From:", "Through:", "During:"))]
        if date_terms:
            chips.append({"text": "; ".join(date_terms),
                          "keys": ["date_mode", "date_from", "date_to", "specific_datetime"]})

        raw_page = request.args.get("page", "1")
        page = int(raw_page) if raw_page.isascii() and raw_page.isdigit() and len(raw_page) <= 9 else 0
        if page < 1:
            errors["page"] = "Page must be a positive whole number."
            page = 1
        raw_page_size = request.args.get("page_size", "")
        try:
            page_size = int(raw_page_size)
        except ValueError:
            page_size = self.PAGE_SIZE
        if page_size not in self.PAGE_SIZES:
            page_size = self.PAGE_SIZE
        incidents, categories, failed = [], [], False
        try:
            categories = managers.io_manager.get_all_incident_categories()
            if not errors:
                incidents = managers.io_manager.search_incidents(**filters)
        except DataLoadError:
            current_app.logger.exception("Failed to search incidents")
            managers.io_manager.notify("Incidents could not be loaded. Please try again later.")
            failed = True
        sort_key = form["sort"] if form["sort"] in self.SORT_COLUMNS else "record_id"
        incidents.sort(key=self.SORT_COLUMNS[sort_key][1], reverse=form["dir"] == "desc")
        if not errors and not failed and request.args.get("export") == "csv":
            return self._csv_response(incidents)
        total = len(incidents)
        pages = max(1, ceil(total / page_size))
        page = min(page, pages)
        first = (page - 1) * page_size
        query_args = {key: value for key, value in form.items() if value}
        size_args = {"page_size": page_size} if page_size != self.PAGE_SIZE else {}
        def page_url(number):
            return url_for("dashboard.search", **query_args, **size_args, page=number)
        def sort_url(column):
            args = dict(query_args)
            args["sort"] = column
            # Clicking a column defaults to descending first (e.g. highest
            # severity or newest date on top), then toggles to ascending on
            # the next click of that same column.
            args["dir"] = "asc" if (form["sort"] == column and form["dir"] == "desc") else "desc"
            return url_for("dashboard.search", **args, **size_args)
        def page_size_url(size):
            args = dict(query_args)
            if size != self.PAGE_SIZE:
                args["page_size"] = size
            return url_for("dashboard.search", **args)
        for chip in chips:
            chip["url"] = url_for("dashboard.search", **{
                key: value for key, value in query_args.items() if key not in chip["keys"]
            }, **size_args)
        sort_urls = {column: sort_url(column) for column in self.SORT_COLUMNS}
        page_size_urls = {size: page_size_url(size) for size in self.PAGE_SIZES}
        csv_url = url_for("dashboard.search", **query_args, export="csv") if not errors and not failed else None
        context = dict(
            form=form, errors=errors, failed=failed,
            incidents=incidents[first:first + page_size], total=total,
            query_text="; ".join(terms) or "All incidents", categories=categories,
            severities=self.SEVERITIES, queues=self.QUEUES,
            format_datetime=managers.io_manager.format_incident_datetime,
            severity_band=DataManager.severity_band, page=page, pages=pages,
            first=first + 1 if total else 0, last=min(first + page_size, total),
            previous_url=page_url(page - 1) if page > 1 else None,
            next_url=page_url(page + 1) if page < pages else None,
            csv_url=csv_url, chips=chips, sort_urls=sort_urls, current_sort=sort_key,
            current_dir=form["dir"],
            sort_columns=[(key, label) for key, (label, _) in self.SORT_COLUMNS.items()],
            page_size=page_size, page_sizes=self.PAGE_SIZES, page_size_urls=page_size_urls,
        )
        # A sort/chip/page-size/pagination click is fetched via JS (see
        # search.html) and only swaps the results fragment, so the page never
        # navigates or scrolls. These links are only ever built from already-
        # validated state, so a fragment request should never carry errors;
        # fall back to the full page on failure so nothing is silently lost.
        if not errors and not failed and request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render_template("_search_results.html", **context)
        return render_template("search.html", **context), 500 if failed else 400 if errors else 200

    def _csv_response(self, incidents: list) -> Response:
        """Return every matching incident (all pages) as a downloadable CSV.

        Columns mirror the results table so the export matches what the
        user sees on screen. Free-text fields are escaped against CSV
        formula injection (OWASP guidance): a leading =, +, -, @, tab or
        carriage return is neutralised with a leading apostrophe, since
        incident titles, locations and hazard categories are reporter-
        supplied text that spreadsheet software would otherwise evaluate.
        """
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Record ID", "Incident", "Date and time", "Location",
            "Hazard category", "Severity", "Review queue", "Injury reported",
        ])
        for incident in incidents:
            report = incident.input_section.to_dict() if incident.input_section else {}
            analysis = incident.ai_section.to_dict() if incident.ai_section else {}
            triage = incident.logic_section.to_dict() if incident.logic_section else {}
            band = DataManager.severity_band(incident)
            writer.writerow([
                incident.record_id or "",
                self._csv_safe(report.get("incident_name")),
                report.get("incident_datetime") or "",
                self._csv_safe(report.get("location")),
                self._csv_safe(analysis.get("hazard_category")),
                self.SEVERITIES.get(band, "Not assessed"),
                self._csv_safe(triage.get("final_queue")),
                "Yes" if report.get("injury_reported") else "No",
            ])
        filename = f"incident-search-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        return Response(
            buffer.getvalue(), mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @staticmethod
    def _csv_safe(value) -> str:
        """Neutralise a leading formula-injection character for CSV export."""
        text = "" if value is None else str(value)
        return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text
