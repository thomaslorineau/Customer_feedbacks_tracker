@echo off
cd /d "C:\Users\tlorinea\Documents\Documents\Documents\Projets\VibeCoding\ovh-complaints-tracker"

echo Installing dependencies...
call .venv\Scripts\pip install feedparser apscheduler

echo.
echo Starting backend...
cd backend
call ..\.venv\Scripts\python -m uvicorn app.main:app --reload

