from datetime import datetime

from flask import current_app, redirect, render_template, request, url_for
from flask.views import MethodView

from data_manager import DataLoadError, DataSaveError
from dashboard.ai_section import AISection
from dashboard.incident import Incident
from dashboard.input_section import InputSection
from dashboard.logic_section import LogicSection
import managers


class AddIncidentView(MethodView):
    """Create and persist incident reports submitted through the dashboard."""

    reporter_roles = {
        "Employee", "Supervisor", "Manager", "Safety Officer",
        "Contractor", "Visitor", "Other",
    }

    def get(self):
        return self._render_form({})

    @staticmethod
    def _render_form(form_data, status=200, errors=None):
        return render_template(
            "add_incident.html",
            form_data=form_data,
            errors=errors or {},
        ), status

    def post(self):
        field_names = (
            "incident_name", "description", "incident_datetime", "location",
            "reporter_role", "injury_reported", "immediate_action",
        )
        form_data = {name: request.form.get(name, "").strip() for name in field_names}
        errors = {name: "This field is required." for name, value in form_data.items() if not value}

        if form_data["reporter_role"] not in self.reporter_roles:
            errors["reporter_role"] = "Select a valid reporter role."
        if form_data["injury_reported"] not in {"yes", "no"}:
            errors["injury_reported"] = "Select yes or no."

        try:
            record_input = {
                **form_data,
                "incident_datetime": datetime.fromisoformat(
                    form_data["incident_datetime"]
                ).isoformat(timespec="seconds"),
                "injury_reported": form_data["injury_reported"] == "yes",
            }
        except ValueError:
            errors["incident_datetime"] = "Enter a valid incident date and time."

        if errors:
            managers.io_manager.notify("Please correct the highlighted fields.")
            return self._render_form(form_data, 400, errors)

        try:
            history = [incident.to_dict() for incident in managers.data_manager.load()]
        except DataLoadError:
            current_app.logger.exception("Failed to load incident history")
            managers.io_manager.notify("Could not load incident history.")
            return self._render_form(form_data, 500)

        try:
            from main import analyse_incident

            ai_output = analyse_incident({"record_id": "", "input": record_input})
        except RuntimeError:
            current_app.logger.exception("Incident analysis is unavailable")
            managers.io_manager.notify("Incident analysis is unavailable.")
            return self._render_form(form_data, 503)

        logic_output = managers.logic_manager.determine_final_status(
            record_input, ai_output, history
        )
        incident = Incident(
            input_section=InputSection.from_dict(record_input),
            ai_section=AISection.from_dict(ai_output),
            logic_section=LogicSection.from_dict(logic_output),
        )

        try:
            managers.data_manager.save(incident)
        except DataSaveError:
            current_app.logger.exception("Failed to save submitted incident")
            managers.io_manager.notify("Could not save the incident.")
            return self._render_form(form_data, 500)

        if ai_output.get("ai_error"):
            managers.io_manager.notify(
                "Saved for manual review because AI analysis failed.",
                category="warning",
            )
        else:
            managers.io_manager.notify(
                "Incident report submitted successfully.",
                category="success",
            )
        return redirect(url_for("dashboard.incident_details", record_id=incident.record_id))