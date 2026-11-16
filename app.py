"""Entry point for the Workplace Incident Triage dashboard."""

from dashboard import create_app

app = create_app()

if __name__ == "__main__":
    import os

    # FLASK_DEBUG overrides the config default so containers can run with
    # the debugger off while local development keeps it on.
    debug = os.getenv("FLASK_DEBUG", str(app.config.get("DEBUG", False))).lower() in (
        "1", "true", "yes",
    )
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=debug,
    )
