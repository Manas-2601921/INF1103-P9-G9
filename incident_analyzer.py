"""Shared AI analysis for CLI and dashboard incident reports."""

class IncidentAnalyzer:
    """Run AI analysis and prepare its result for the logic manager."""

    def __init__(self):
        try:
            from ai_manager import AIManager

            self.ai_manager = AIManager()
            self.ai_import_error = None
        except ImportError as exc:
            self.ai_manager = None
            self.ai_import_error = str(exc)

    @staticmethod
    def to_severity_band(ai_output: dict) -> dict:
        """Convert numeric severity to a band while retaining the original score."""
        severity = ai_output.get("severity")
        if isinstance(severity, (int, float)) and not isinstance(severity, bool):
            ai_output["severity_score"] = severity
            if severity > 0.7:
                ai_output["severity"] = "high"
            elif severity >= 0.4:
                ai_output["severity"] = "medium"
            else:
                ai_output["severity"] = "low"
        return ai_output

    def analyse_incident(self, record: dict) -> dict:
        """Analyse a record or return the existing manual-review fallback."""
        if self.ai_manager is None:
            raise RuntimeError(
                f"the AI dependencies are unavailable ({self.ai_import_error}); "
                "run 'pip install -r requirements.txt' first"
            )

        ok, ai_output = self.ai_manager.analyze(record)
        if ok:
            return self.to_severity_band(ai_output)

        print("\n[Warning] The AI analysis failed and this incident will be "
              "queued for manual review.")
        print(f"[Reason]  {ai_output}")
        return {
            "repeat_pattern_indicators": {
                "datetime": record["input"]["incident_datetime"]
            },
            "ai_error": ai_output,
        }


incident_analyzer = IncidentAnalyzer()
