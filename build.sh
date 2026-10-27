#!/usr/bin/env bash
# Render build step: install, collect static files, migrate (also loads the FAQ / error-code seed data).
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
