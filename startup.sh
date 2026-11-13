#!/bin/sh
# Azure App Service Linux startup command. Point the App Service
# "Startup command" setting at this file: it creates any missing database
# tables (existing data is preserved) and then starts the web dashboard.
set -e
python -m flask --app app init-db
exec python app.py
