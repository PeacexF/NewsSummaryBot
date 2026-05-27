FROM python:3.11-slim

# Dockerfile isn't ready yet, as there is no scheduler and all you need now to run the project is basically:
# `docker compose up -d`  ->  `python bot/main.py` And it's running.
# Originally planned to make a scheduler for the main.py to send them automatically, but there is no point considering that ai isn't working :/