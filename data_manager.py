"""JSON persistence and queries for workplace incident records."""

from pathlib import Path
from datetime import datetime
import json


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
        """Load incident records from the JSON database.

        Returns:
            list: Stored records, or an empty list if the file is missing, cannot
            be read, contains invalid JSON, or has a non-list top-level value.
            A diagnostic message is printed when records cannot be loaded.
        """
        if self._incidents_file.exists():
            try:
                with open(self._incidents_file, "r", encoding="utf-8") as f:
                    incidents_data = json.load(f)
                    if isinstance(incidents_data, list):
                        return incidents_data
                    else:
                        print("\n" + "-"*60 + "\n")
                        print("[Error]   : Fail to load data.")
                        print("[Reason]  : JSON returns a top-level type that is not a list. Please contact the support team.")
                        print("[Warning] : New incidents will be saved to the new database file if you wish to continue.\n            Manual combination of the old and new database files may be required.")
                        print("\n" + "-"*60 + "\n")
                        return []

            except json.JSONDecodeError:    # if file exists but empty, this error is also raised
                print("\n" + "-"*60 + "\n")
                print("[Error]   : Fail to load data.")
                print("[Reason]  : Invalid JSON format in the database file. Please contact the support team.")
                print("[Warning] : New incidents will be saved to the new database file if you wish to continue.\n            Manual combination of the old and new database files may be required.")
                print("\n" + "-"*60 + "\n")
                return []

            except Exception as e:
                print("\n" + "-"*60 + "\n")
                print("[Error]   : Fail to load data.")
                print("[Reason]  : An unexpected error occurred while reading the database file. Please contact the support team.")
                print(f"[Details] : {str(e)}")
                print("[Warning] : New incidents will be saved to the new database file if you wish to continue.\n            Manual combination of the old and new database files may be required.")
                print("\n" + "-"*60 + "\n")
                return []

        else:
            print("\n" + "-"*60 + "\n")
            print("Database file not found. The application must be running for the first time.\nA new database file will be created upon adding the first incident.")
            print("\nIf you are sure that you have recently saved data, please contact the Support Team.")
            print("\n" + "-"*60 + "\n")
        return []

    def save(self, record):
        """Assign an incident ID and rewrite the updated record list as JSON.

        Args:
            record (dict): Incident containing ``input``, ``ai``, and ``logic``.
                The ``ai.repeat_pattern_indicators.datetime`` value supplies
                the creation timestamp; the processing timestamp is set now.

        Returns:
            None.

        Notes:
            The ID increments the last stored record's ID, starting at INC-0001.
            Creates the parent directory if needed and prints a success message.
            The entire updated list replaces the file, preserving a single JSON array.
        """
        records = self.load()
        next_id = int(records[-1]["record_id"].split("-")[1]) + 1 if records else 1 # update last ID to next ID otherwise start with 0001
        stored_record = {
            "record_id": f"INC-{next_id:04d}",
            "input": record["input"],
            "ai": record["ai"],
            "logic": record["logic"],
            "metadata": {
                "created_at": record["ai"]["repeat_pattern_indicators"]["datetime"],
                "processed_at": datetime.now().isoformat(timespec="seconds"),
            },
        }
        records.append(stored_record)
        content = json.dumps(records, indent=4, ensure_ascii=False)

        # Create the folder "data" if it doesn't exist
        self._incidents_file.parent.mkdir(parents=True, exist_ok=True)

        # Rewrite the whole file: appending would concatenate a second JSON
        # array after the first and corrupt the database
        with open(self._incidents_file, "w", encoding="utf-8") as f:
            f.write(content)
            f.write("\n")
            print(f"Saved record to {self._incidents_file}")

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
