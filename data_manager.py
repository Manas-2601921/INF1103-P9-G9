"""JSON persistence and queries for workplace incident records."""

from pathlib import Path
from datetime import datetime
import json
import os
import tempfile


class DataManager:
    """Manage one incident database independently of other manager instances.

    The file path belongs to the instance; records are read on each operation
    so a new instance can access records saved in an earlier run.
    """

    def __init__(self, incidents_file="data/incidents.json"):
        """Accept a string or Path, defaulting to the existing database path."""
        self._incidents_file = Path(incidents_file)

    @property
    def incidents_file(self):
        """Return the database path without exposing a writable attribute."""
        return self._incidents_file

    def load(self):
        """Read stored incident dictionaries without producing console output.

        Returns:
            list[dict]: Stored records. A missing file (including a missing
            parent directory) or a valid empty JSON array returns an empty list.

        Raises:
            InvalidIncidentDataError: The file is empty, contains invalid JSON
                or UTF-8, or is not a list containing only JSON objects.
            DataLoadError: The file cannot be accessed or read, for example
                because of permissions, an invalid path, or an I/O failure.

        Only the record container is validated here, not individual incident
        fields. Original read/parse exceptions are preserved as __cause__.
        Unexpected programming errors propagate rather than appearing to be
        an empty database. This method never creates or changes the file.
        """
        try:
            # Open directly: an exists() check can hide access errors and the
            # file could disappear between checking and opening it.
            with self._incidents_file.open("r", encoding="utf-8") as file:
                incidents_data = json.load(file)

        except FileNotFoundError:
            return []
        
        except UnicodeDecodeError as exc:
            raise InvalidIncidentDataError(
                f"Incident database '{self._incidents_file}' is not valid UTF-8."
            ) from exc
        
        except json.JSONDecodeError as exc:
            raise InvalidIncidentDataError(
                f"Incident database '{self._incidents_file}' contains invalid JSON "
                f"at line {exc.lineno}, column {exc.colno}: {exc.msg}."
            ) from exc
        
        except (OSError, ValueError) as exc:
            # OSError covers permission errors, directories used as files,
            # invalid path components, and device/read failures. ValueError
            # covers paths containing an embedded null character.
            raise DataLoadError(
                f"Cannot read incident database '{self._incidents_file}': {exc}"
            ) from exc

        if not isinstance(incidents_data, list):
            raise InvalidIncidentDataError(
                f"Incident database '{self._incidents_file}' must contain a JSON list."
            )
        
        for index, record in enumerate(incidents_data):
            if not isinstance(record, dict):
                raise InvalidIncidentDataError(
                    f"Incident database '{self._incidents_file}' contains a non-object "
                    f"record at index {index}."
                )
            
        return incidents_data

    def save(self, record):
        """Persist an incident and return its stored dictionary without printing.

        The input must contain dictionary-valued input, ai, and logic sections,
        and a non-empty string at ai.repeat_pattern_indicators.datetime.
        Domain validation remains the responsibility of the other managers.

        Raises:
            DataLoadError: Existing data cannot be loaded or its IDs are invalid.
            ValueError: The supplied record has an invalid structure or the
                updated records cannot be serialized as UTF-8 JSON.
            DataSaveError: Creating or replacing the database fails.

        Writes a temporary file beside the database, then replaces the database
        only after writing succeeds. Existing data is preserved on write failure.
        This JSON implementation assumes a single writer; it does not coordinate
        concurrent requests. The caller's record is not modified.
        """
        records = self.load()

        if not isinstance(record, dict) or any(
            not isinstance(record.get(section), dict)
            for section in ("input", "ai", "logic")
        ):
            raise ValueError("Incident must contain input, ai, and logic dictionaries.")
        
        indicators = record["ai"].get("repeat_pattern_indicators")
        created_at = indicators.get("datetime") if isinstance(indicators, dict) else None

        if not isinstance(created_at, str) or not created_at.strip():
            raise ValueError("Incident ai.repeat_pattern_indicators.datetime must be a non-empty string.")

        identifiers = set()

        for existing in records:
            identifier = existing.get("record_id")
            suffix = identifier[4:] if isinstance(identifier, str) and identifier.startswith("INC-") else ""
            if not suffix.isascii() or not suffix.isdigit() or int(suffix) < 1:
                raise InvalidIncidentDataError("Stored incident has an invalid record_id.")
            number = int(suffix)
            if number in identifiers:
                raise InvalidIncidentDataError("Stored incidents contain duplicate record IDs.")
            identifiers.add(number)

        next_id = max(identifiers, default=0) + 1

        stored_record = {
            "record_id": f"INC-{next_id:04d}",
            "input": record["input"],
            "ai": record["ai"],
            "logic": record["logic"],
            "metadata": {
                "created_at": created_at,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
            },
        }
        records.append(stored_record)
        try:
            content = (json.dumps(records, indent=4, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            raise ValueError("Incident records cannot be serialized as UTF-8 JSON.") from exc

        temporary_path = None
        try:
            self._incidents_file.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=self._incidents_file.parent,
                prefix=f".{self._incidents_file.name}.", suffix=".tmp", delete=False,
            ) as file:
                temporary_path = Path(file.name)
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self._incidents_file)

        except (OSError, ValueError) as exc:
            raise DataSaveError(
                f"Cannot save incident database '{self._incidents_file}': {exc}"
            ) from exc
        
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    # Cleanup must not hide the original storage failure.
                    pass
                
        return stored_record

    def query(self, filter_fn):
        """Return stored records accepted by a predicate, in storage order.

        Args:
            filter_fn (callable): Function taking a record dictionary and returning
                a truthy value when that record should be included.

        Returns:
            list: Matching records, or an empty list if none match or no records
                are loaded. Exceptions from the predicate propagate.
        """
        records = self.load()
        return [record for record in records if filter_fn(record)]

    # Query and summary helpers

    def query_stored_incident_summaries(self):  # This function is to load every stored incidents on startup
        """Build display summaries for all stored incidents.

        Returns:
            list[dict]: Summaries containing the record ID, incident date, location,
                description, hazard category, severity, final queue, and escalation
                status. Missing fields use display defaults; a missing escalation
                status is None. Returns an empty list if no records are loaded.
        """
        records = self.load()
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
            })

        return summaries

    def query_description(self, description):
        """Return incidents whose input description exactly matches the value.

        Args:
            description (str): Full description to match, including letter case.

        Returns:
            list: Matching incident records, or an empty list if none are found.
        """
        incidents = self.query(lambda record: record.get("input", {}).get("description") == description)
        return incidents

    def query_location(self, location):
        """Return incidents whose input location exactly matches the value.

        Args:
            location (str): Location to match, including letter case.

        Returns:
            list: Matching incident records, or an empty list if none are found.
        """
        incidents = self.query(lambda record: record.get("input", {}).get("location") == location)
        return incidents

    def query_reporter_role(self, reporter_role):
        """Return incidents whose input reporter role exactly matches the value.

        Args:
            reporter_role (str): Reporter role to match, including letter case.

        Returns:
            list: Matching incident records, or an empty list if none are found.
        """
        incidents = self.query(lambda record: record.get("input", {}).get("reporter_role") == reporter_role)
        return incidents

    def query_incident_datetime(self, incident_datetime):
        """Return incidents whose input datetime exactly matches the stored value.

        Args:
            incident_datetime (str): Datetime in the same format as the stored
                input datetime. No date parsing or normalization is performed.

        Returns:
            list: Matching incident records, or an empty list if none are found.
        """
        incidents = self.query(lambda record: record.get("input", {}).get("incident_datetime") == incident_datetime)
        return incidents

    def query_injury_reported(self, injury_reported):
        """Return incidents whose input injury status equals the supplied value.

        Args:
            injury_reported: Injury status in the same type and format as the
                stored ``input.injury_reported`` value.

        Returns:
            list: Matching incident records, or an empty list if none are found.
        """
        incidents = self.query(lambda record: record.get("input", {}).get("injury_reported") == injury_reported)
        return incidents

    @staticmethod
    def numeric_severity(record):
        """Return a record's numeric severity, or None when it has none.

        Current records keep the 0-1 score in severity_score alongside a banded
        severity ("high"/"medium"/"low"); older records store the number in
        severity directly.
        """
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
            list: Matching incident records. An unsupported operator prints an
                error message and returns an empty list.

        Raises:
            TypeError: An ordering comparison uses an incompatible threshold type.
        """
        # records without a usable numeric severity are skipped, not crashed on
        if comparison_operator == "==":
            incidents = self.query(lambda record: (s := self.numeric_severity(record)) is not None and s == severity)
        elif comparison_operator == ">":
            incidents = self.query(lambda record: (s := self.numeric_severity(record)) is not None and s > severity)
        elif comparison_operator == "<":
            incidents = self.query(lambda record: (s := self.numeric_severity(record)) is not None and s < severity)
        else:
            print("Invalid comparison operator. Use '==', '>', or '<'.")
            return [] # or raise an exception
        return incidents

    def query_hazard_category(self, hazard_category):
        """Return incidents whose AI hazard category exactly matches the value.

        Args:
            hazard_category (str): Hazard category to match, including letter case.

        Returns:
            list: Matching incident records, or an empty list if none are found.
        """
        incidents = self.query(lambda record: record.get("ai", {}).get("hazard_category") == hazard_category)
        return incidents


# Exceptions for data loading and validation
class DataLoadError(Exception):
    """Stored incidents could not be read; callers decide how to report this."""


class InvalidIncidentDataError(DataLoadError):
    """The database is not valid UTF-8 JSON containing a list of objects."""

class DataSaveError(Exception):
    """Incident records could not be written; callers decide how to report this."""
