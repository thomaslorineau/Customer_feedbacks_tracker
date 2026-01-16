@echo off
REM Script de démarrage du serveur staging avec DuckDB
REM Usage: scripts\start_staging_duckdb.bat

set ENVIRONMENT=staging
set USE_DUCKDB=true
set APP_PORT=8001

echo 🚀 Démarrage du serveur staging avec DuckDB...
echo    Environnement: staging
echo    Base de données: DuckDB
echo    Port: 8001
echo    URL: http://127.0.0.1:8001
echo.

cd /d %~dp0\..
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload



