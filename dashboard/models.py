"""Four-table storage for incidents and their one-to-one sections."""

from dashboard.extensions import db


class IncidentModel(db.Model):
    __tablename__ = "Incidents"
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.Text)
    processed_at = db.Column(db.Text)

    input_section = db.relationship(
        "IOManagerModel", back_populates="incident", uselist=False,
        cascade="all, delete-orphan", single_parent=True,
    )
    ai_section = db.relationship(
        "AIManagerModel", back_populates="incident", uselist=False,
        cascade="all, delete-orphan", single_parent=True,
    )
    logic_section = db.relationship(
        "LogicManagerModel", back_populates="incident", uselist=False,
        cascade="all, delete-orphan", single_parent=True,
    )


class IOManagerModel(db.Model):
    __tablename__ = "io_manager"

    incident_id = db.Column(db.Integer, db.ForeignKey("Incidents.id", ondelete="CASCADE"), primary_key=True)
    incident_name = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    location = db.Column(db.Text, nullable=False, default="")
    reporter_role = db.Column(db.Text, nullable=False, default="")
    incident_datetime = db.Column(db.Text, nullable=False, default="")
    injury_reported = db.Column(db.Boolean, nullable=False, default=False)
    immediate_action = db.Column(db.Text, nullable=False, default="")
    incident = db.relationship("IncidentModel", back_populates="input_section")


class AIManagerModel(db.Model):
    __tablename__ = "ai_manager"

    incident_id = db.Column(db.Integer, db.ForeignKey("Incidents.id", ondelete="CASCADE"), primary_key=True)
    # JSON preserves both legacy numeric severity and current string bands.
    severity = db.Column(db.JSON(none_as_null=True))
    confidence = db.Column(db.Float)
    severity_explanation = db.Column(db.Text)
    hazard_category = db.Column(db.Text)
    incident_type = db.Column(db.Text)
    indicators = db.Column(db.JSON, nullable=False, default=dict)
    repeat_pattern_indicators = db.Column(db.JSON, nullable=False, default=dict)
    recommended_immediate_action = db.Column(db.Text)
    supporting_phrase = db.Column(db.Text)
    severity_score = db.Column(db.Float)
    ai_error = db.Column(db.Text)
    incident = db.relationship("IncidentModel", back_populates="ai_section")


class LogicManagerModel(db.Model):
    __tablename__ = "logic_manager"

    incident_id = db.Column(db.Integer, db.ForeignKey("Incidents.id", ondelete="CASCADE"), primary_key=True)
    final_queue = db.Column(db.Text)
    escalation_required = db.Column(db.Boolean)
    recurring = db.Column(db.Boolean)
    duplicate_possible = db.Column(db.Boolean)
    risk_score = db.Column(db.Integer)
    rule_applied = db.Column(db.Text)
    ai_explanation = db.Column(db.Text)
    supporting_phrase = db.Column(db.Text)
    incident = db.relationship("IncidentModel", back_populates="logic_section")
