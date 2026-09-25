from pathlib import Path
import json

incidents = Path("data/incidents.json")

def load():
    if incidents.exists():
        with open(incidents, "r") as f:
            return json.load(f)
    return {}

def save(dict):
    pass

def query():
    pass