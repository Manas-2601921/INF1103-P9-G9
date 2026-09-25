import data_manager as data
import json

incidents = data.load()

print(json.dumps(incidents, indent=4))