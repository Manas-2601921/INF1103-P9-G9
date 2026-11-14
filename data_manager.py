"""SQLAlchemy persistence and incident queries returning domain objects."""

from contextlib import contextmanager
from datetime import datetime
import re

from flask import current_app, has_app_context
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from dashboard.extensions import db
from dashboard.incident import Incident
from dashboard.models import IncidentModel, IOManagerModel, AIManagerModel


class DataManager:
    """Persist completed incidents; use a configured Flask app or the active app.

    Without either, a default app is created lazily for terminal use. Initialize
    its database with `python -m flask --app app init-db` before using storage.
    Each operation owns a separate session, never committing unrelated changes.
    """

    def __init__(self, app=None):
        self._app = app

    @contextmanager
    def _session(self):
        app = self._app
        if app is None and has_app_context():
            app = current_app._get_current_object()
        if app is None:
            from dashboard import create_app
            app = self._app = create_app()
        with app.app_context():
            with Session(db.engine) as session:
                yield session

    def load(self) -> list[Incident]:
        """Return fully reconstructed incidents ordered by database ID.

        Objects and sections remain usable after the session closes. Missing or
        unreadable tables raise DataLoadError; damaged section graphs raise
        InvalidIncidentDataError. No tables or files are reset automatically.
        """
        return self.query()

    def save(self, incident: Incident) -> Incident:
        """Insert a completed Incident atomically and return the same instance.

        All three sections must be attached. This inserts new records only;
        previously saved incidents are rejected. ID and metadata are updated on
        the caller only after commit succeeds. Field/domain validation belongs
        to the layer that constructs each section.
        """
        if not isinstance(incident, Incident):
            raise TypeError("save() requires an Incident instance.")
        
        incident.validate_complete()

        if incident.record_id is not None:
            raise ValueError("save() inserts new incidents; this incident already has a record_id.")
        
        metadata = incident.metadata
        now = datetime.now().isoformat(timespec="seconds")
        metadata.setdefault("created_at", incident.input_section.to_dict().get("incident_datetime") or now)
        metadata.setdefault("processed_at", now)
        model = incident.convert_to_db_model()
        model.created_at = metadata["created_at"]
        model.processed_at = metadata["processed_at"]

        try:
            # Exiting session.begin() commits automatically, or rolls back if an error occurs
            with self._session() as session:
                with session.begin():
                    session.add(model)
                    session.flush()
                    record_id = f"INC-{model.id:04d}"
                # session.begin rolls back on failure; no partial section rows survive.
        except SQLAlchemyError as exc:
            raise DataSaveError("Cannot save incident to SQLite.") from exc
        
        incident.record_id = record_id
        incident.metadata = metadata
        return incident

    def query(self, *criteria) -> list[Incident]:
        """Filter in SQL using SQLAlchemy expressions; return detached Incidents.

        With no criteria this loads all incidents. Multiple criteria are ANDed.
        Python callbacks are deliberately unsupported: SQLAlchemy cannot turn
        an arbitrary Python lambda into SQL. Prefer the named query helpers
        so callers do not need to import persistence models.
        """
        if any(callable(criterion) for criterion in criteria):
            raise TypeError("query() requires SQL expressions, not Python callbacks.")
        statement = select(IncidentModel).where(*criteria).options(
            selectinload(IncidentModel.input_section),
            selectinload(IncidentModel.ai_section),
            selectinload(IncidentModel.logic_section),
        ).order_by(IncidentModel.id)
        try:
            with self._session() as session:
                models = session.scalars(statement).all()
                try:
                    return [Incident.from_db_model(model) for model in models]
                except (ValueError, TypeError) as exc:
                    raise InvalidIncidentDataError("Stored incident sections are invalid.") from exc
        except SQLAlchemyError as exc:
            raise DataLoadError("Cannot query incidents; check database initialization.") from exc

    def get_by_record_id(self, record_id: str) -> Incident | None:
        """Find a single incident by its public INC- identifier using its SQL key."""
        if not isinstance(record_id, str) or re.fullmatch(r"INC-[0-9]+", record_id) is None:
            return None
        incident_id = int(record_id[4:])
        if not 0 < incident_id <= 9223372036854775807:
            return None
        matches = self.query(IncidentModel.id == incident_id)
        return matches[0] if matches else None

    def query_title(self, title: str) -> list[Incident]:
        """Match an entire title case-insensitively, ignoring surrounding spaces."""
        return self.query(IncidentModel.input_section.has(
            func.lower(func.trim(IOManagerModel.incident_name)) == title.strip().lower()
        ))

    def query_category(self, category: str) -> list[Incident]:
        """Match an entire hazard category case-insensitively."""
        return self.query(IncidentModel.ai_section.has(
            func.lower(func.trim(AIManagerModel.hazard_category)) == category.strip().lower()
        ))

    def get_all_incident_categories(self) -> list[str]:
        """Select distinct nonblank categories without loading incident objects."""
        category = func.trim(AIManagerModel.hazard_category)
        statement = select(category).join(
            IncidentModel, IncidentModel.id == AIManagerModel.incident_id
        ).where(category != "").distinct().order_by(category)
        try:
            with self._session() as session:
                return list(session.scalars(statement))
        except SQLAlchemyError as exc:
            raise DataLoadError("Cannot load incident categories.") from exc

    # Query and summary helpers

    def query_stored_incident_summaries(self):  # This function is to load every stored incidents on startup
        """Build display summaries for all stored incidents.

        Returns:
            list[dict]: Summaries containing the record ID, incident date, location,
                description, hazard category, severity, final queue, escalation
                status, and risk score. Missing fields use display defaults; a
                missing escalation status or risk score is None. Returns an empty
                list if no records are loaded.
                description, hazard category, severity, final queue, and escalation
                status. Missing fields use display defaults; a missing escalation
                status is None. Returns an empty list if no records are loaded.
        """
        records = [incident.to_dict() for incident in self.load()]
        summaries = []

        for record in records:
            user_input = record.get("input") or {}
            ai_response = record.get("ai") or {}
            logic = record.get("logic") or {}
            summaries.append({
                "record_id": record.get("record_id", "Unknown"),

                "incident_date": user_input.get("incident_datetime", "Unknown"),
                "location": user_input.get("location", "Unknown"),
                "description": user_input.get("description", "No description provided."),

                "hazard_category": ai_response.get("hazard_category", "Not assessed"),
                "severity": ai_response.get("severity", "Not assessed"),

                "final_queue": logic.get("final_queue", "Unassigned"),
                "escalation_required": logic.get("escalation_required"),
                "risk_score": logic.get("risk_score"),
            })

        return summaries

    def query_description(self, description):
        """Return incidents whose input description exactly matches the value.

        Args:
            description (str): Full description to match, including letter case.

        Returns:
            list[Incident]: Matching incidents, or an empty list if none are found.
        """
        incidents = self.query(IncidentModel.input_section.has(IOManagerModel.description == description))
        return incidents

    def query_location(self, location):
        """Return incidents whose input location exactly matches the value.

        Args:
            location (str): Location to match, including letter case.

        Returns:
            list[Incident]: Matching incidents, or an empty list if none are found.
        """
        incidents = self.query(IncidentModel.input_section.has(IOManagerModel.location == location))
        return incidents

    def query_reporter_role(self, reporter_role):
        """Return incidents whose input reporter role exactly matches the value.

        Args:
            reporter_role (str): Reporter role to match, including letter case.

        Returns:
            list[Incident]: Matching incidents, or an empty list if none are found.
        """
        incidents = self.query(IncidentModel.input_section.has(IOManagerModel.reporter_role == reporter_role))
        return incidents

    def query_incident_datetime(self, incident_datetime):
        """Return incidents whose input datetime exactly matches the stored value.

        Args:
            incident_datetime (str): Datetime in the same format as the stored
                input datetime. No date parsing or normalization is performed.

        Returns:
            list[Incident]: Matching incidents, or an empty list if none are found.
        """
        incidents = self.query(IncidentModel.input_section.has(IOManagerModel.incident_datetime == incident_datetime))
        return incidents

    def query_injury_reported(self, injury_reported):
        """Return incidents whose input injury status equals the supplied value.

        Args:
            injury_reported: Injury status in the same type and format as the
                stored ``input.injury_reported`` value.

        Returns:
            list[Incident]: Matching incidents, or an empty list if none are found.
        """
        incidents = self.query(IncidentModel.input_section.has(IOManagerModel.injury_reported == injury_reported))
        return incidents

    @staticmethod
    def numeric_severity(record):
        """Return a record's numeric severity, or None when it has none.

        Current records keep the 0-1 score in severity_score alongside a banded
        severity ("high"/"medium"/"low"); older records store the number in
        severity directly.
        """
        if isinstance(record, Incident):
            ai = record.ai_section.to_dict() if record.ai_section else {}
        else:
            ai = record.get("ai", {})
        for key in ("severity_score", "severity"):
            value = ai.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    continue
        return None

    def query_severity(self, severity, comparison_operator):
        """Filter incidents by comparing their numeric AI severity to a threshold.

        Args:
            severity (int or float): Numeric value to compare stored severities to.
            comparison_operator (str): One of ``==``, ``>``, or ``<``.

        Returns:
            list[Incident]: Matching incidents. An unsupported operator prints an
                error message and returns an empty list.

        Raises:
            TypeError: An ordering comparison uses an incompatible threshold type.
        """
        # Legacy severity is JSON containing numbers, numeric strings, or bands.
        # Keep this compatibility filter in Python until that field is normalised.
        # Every result is still an Incident, consistent with other retrieval APIs.
        if comparison_operator == "==":
            incidents = [incident for incident in self.load()
                         if (s := self.numeric_severity(incident)) is not None and s == severity]
        elif comparison_operator == ">":
            incidents = [incident for incident in self.load()
                         if (s := self.numeric_severity(incident)) is not None and s > severity]
        elif comparison_operator == "<":
            incidents = [incident for incident in self.load()
                         if (s := self.numeric_severity(incident)) is not None and s < severity]
        else:
            print("Invalid comparison operator. Use '==', '>', or '<'.")
            return [] # or raise an exception
        return incidents

    def query_hazard_category(self, hazard_category):
        """Return incidents whose AI hazard category exactly matches the value.

        Args:
            hazard_category (str): Hazard category to match, including letter case.

        Returns:
            list[Incident]: Matching incidents, or an empty list if none are found.
        """
        incidents = self.query(IncidentModel.ai_section.has(AIManagerModel.hazard_category == hazard_category))
        return incidents


class DataLoadError(Exception):
    """Stored incidents could not be read."""


class InvalidIncidentDataError(DataLoadError):
    """Stored incident rows could not be reconstructed."""


class DataSaveError(Exception):
    """An incident transaction could not be committed."""
