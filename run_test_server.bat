@echo off
echo Starting Incident Response Bot for Testing...
set USE_KAFKA_QUEUE=false
set WEBHOOK_SECRET=
venv\Scripts\python.exe main.py
pause
