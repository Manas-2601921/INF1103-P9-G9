from dashboard.shared_imports import *
from dashboard.analytics.stats_service import StatsService

class HomeView(MethodView):
    """Main dashboard page serving the incident trends analytics."""

    def get(self):
        import managers  

        payload = StatsService(managers.data_manager).dashboard_payload()
        if payload["rising"]:
            managers.io_manager.notify(
                f"Warning: {len(payload['rising'])} rising hazard pattern(s) "
                "detected this week (possible incoming incidents).",
                category="warning",
            )
        return render_template("index.html", stats=payload,
                               total=payload["total"])