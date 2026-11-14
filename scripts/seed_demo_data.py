"""Seed the database with demo incidents so the trends page has patterns to show.

Creates roughly 43 incidents spread over the last 30 days with three
deliberate narratives:

- a recurring cluster (Warehouse × mechanical forklift incidents) with
  several reports in the last 7 days, so a hotspot AND a rising pattern appear
- an older, stable cluster (Workshop × ergonomic) that is a hotspot but NOT rising
- scattered single incidents across locations and categories

The AI sections are crafted, but every logic section is computed by the real
``LogicManager`` against the incidents stored so far — seeded queues follow the
same business rules as live triage.

Run with:

    .venv/Scripts/python scripts/seed_demo_data.py [--days 30] [--force]

Point it at a scratch database with the DATABASE_URL environment variable,
e.g. (bash): DATABASE_URL=sqlite:///$(pwd)/data/demo.db python scripts/seed_demo_data.py
"""

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow "python scripts/seed_demo_data.py" from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard import create_app
from dashboard.ai_section import AISection
from dashboard.extensions import db
from dashboard.incident import Incident
from dashboard.input_section import InputSection
from dashboard.logic_section import LogicSection
from data_manager import DataManager
from logic_manager import LogicManager


class DemoSeeder:
    """Populate the database with deterministic demo incidents."""

    LOCATIONS = ["Warehouse", "Workshop", "Office", "Construction Site", "Laboratory"]
    CATEGORY_DETAIL = {
        "mechanical": ("Forklift reversing incident",
                       "A forklift reversing in the loading bay nearly struck a worker."),
        "electrical": ("Damaged power cable",
                       "A frayed power cable was found energised across a walkway."),
        "chemical": ("Chemical splash risk",
                      "An unlabelled solvent container was left open beside a work bench."),
        "ergonomic": ("Manual handling strain",
                      "A worker reported lower-back pain after lifting stock repeatedly."),
        "slip/trip/fall": ("Wet floor slip hazard",
                           "A puddle from a roof leak made the corridor floor slippery."),
        "fire": ("Blocked fire exit",
                 "Stored pallets were found blocking a marked fire exit route."),
        "biological": ("Mould growth reported",
                       "Visible mould was found spreading on a storeroom wall."),
        "psychosocial": ("Verbal abuse report",
                         "A customer shouted at and threatened staff at the counter."),
    }

    def __init__(self, days: int = 30, force: bool = False, seed_value: int = 20261118):
        self._days = days
        self._force = force
        self._rng = random.Random(seed_value)
        self._app = create_app()
        self._data_manager = DataManager(self._app)
        self._logic = LogicManager()
        self._added = 0

    def _band(self, score: float) -> str:
        """Band a raw 0-1 severity score with the pipeline thresholds."""
        if score > 0.7:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"

    def _make_incident(self, location: str, category: str, occurred: datetime,
                       score: float, injury: bool = False, danger: bool = False) -> tuple[dict, dict]:
        """Build the input and AI dictionaries for one seeded incident."""
        name, description = self.CATEGORY_DETAIL[category]
        input_data = {
            "incident_name": name,
            "description": description,
            "location": location,
            "reporter_role": self._rng.choice(["Employee", "Supervisor", "Safety Officer"]),
            "incident_datetime": occurred.isoformat(timespec="seconds"),
            "injury_reported": injury,
            "immediate_action": self._rng.choice([
                "Area cordoned off", "Supervisor notified", "Work paused",
                "Equipment isolated", "Cleanup started",
            ]),
        }
        ai_output = {
            "severity": self._band(score),
            "severity_score": score,
            "confidence": round(self._rng.uniform(0.78, 0.95), 2),
            "severity_explanation": f"{category} hazard at {location} with score {score:.2f}.",
            "hazard_category": category,
            "incident_type": self._rng.choice(["near-miss", "unsafe condition", "injury"]),
            "indicators": {
                "injury": injury,
                "immediate_danger": danger,
                "exposure": self._rng.random() < 0.3,
                "equipment_involvement": category == "mechanical",
                "work_stoppage": self._rng.random() < 0.35,
                "uncontrolled_hazard": self._rng.random() < 0.25,
            },
            "repeat_pattern_indicators": {
                "hazard_category": category,
                "location": location,
                "datetime": occurred.strftime("%d-%m-%Y %H:%M"),
                "activity": name.lower(),
            },
            "recommended_immediate_action": input_data["immediate_action"],
            "supporting_phrase": description[:60],
        }
        return input_data, ai_output

    def _store(self, location: str, category: str, occurred: datetime,
               score: float, injury: bool = False, danger: bool = False) -> None:
        """Craft one incident, route it through the real logic manager, and save it."""
        input_data, ai_output = self._make_incident(
            location, category, occurred, score, injury, danger
        )
        record = {"record_id": "", "input": input_data}
        history = [item.to_dict() for item in self._data_manager.load()]
        logic_result = self._logic.determine_final_status(record, ai_output, history)
        incident = Incident(
            InputSection.from_dict(input_data),
            AISection.from_dict(ai_output),
            LogicSection.from_dict(logic_result),
        )
        self._data_manager.save(incident)
        self._added += 1

    def run(self) -> int:
        """Seed the configured database and return the process exit code."""
        with self._app.app_context():
            db.create_all()
            existing = self._data_manager.load()
            if existing and not self._force:
                print(f"The database already holds {len(existing)} incidents; "
                      "use --force to add demo data on top.")
                return 0

            now = datetime.now()

            # 1. recurring Warehouse × mechanical cluster: 3 in the last 7 days,
            #    2 more in weeks 2-4 -> a hotspot that is also RISING
            for offset in (0, 2, 5, 12, 24):
                score = self._rng.uniform(0.45, 0.92)
                occurred = now - timedelta(days=offset, hours=self._rng.randint(0, 7))
                self._store("Warehouse", "mechanical", occurred, score)

            # 2. older Workshop × ergonomic cluster: repeated but NOT rising
            for offset in (11, 14, 18):
                occurred = now - timedelta(days=offset, hours=self._rng.randint(0, 7))
                self._store("Workshop", "ergonomic", occurred, self._rng.uniform(0.25, 0.5))

            # 3. scattered background incidents across locations and categories
            for _ in range(35):
                location = self._rng.choice(self.LOCATIONS)
                category = self._rng.choice(list(self.CATEGORY_DETAIL))
                offset = self._rng.randint(0, self._days - 1)
                occurred = now - timedelta(days=offset, minutes=self._rng.randint(0, 600))
                score = round(self._rng.uniform(0.05, 0.95), 2)
                self._store(
                    location,
                    category,
                    occurred,
                    score,
                    injury=self._rng.random() < 0.12,
                    danger=self._rng.random() < 0.15,
                )

            print(f"Seeded {self._added} demo incidents over the last {self._days} days.")

            # quick verification summary
            counts = {}
            for item in self._data_manager.load():
                pair = (item.input_section.manager_json.get("location"),
                        item.ai_section.manager_json.get("hazard_category"))
                counts[pair] = counts.get(pair, 0) + 1
            for (location, category), count in sorted(counts.items(), key=lambda kv: -kv[1])[:6]:
                print(f"  {location} × {category}: {count}")
            print("Start the dashboard with:  python app.py  then open http://127.0.0.1:5000/")
            return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30,
                        help="how many days back to scatter background incidents (default 30)")
    parser.add_argument("--force", action="store_true",
                        help="seed even when the database already contains incidents")
    args = parser.parse_args()
    raise SystemExit(DemoSeeder(days=args.days, force=args.force).run())
