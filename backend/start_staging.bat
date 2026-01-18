@echo off
echo ========================================
echo Demarrage du serveur STAGING OVH Complaints Tracker
echo ========================================
echo.

REM Trouver et utiliser le Python de l'environnement virtuel
set PYTHON_EXE=
if exist "..\.venv\Scripts\python.exe" (
    set PYTHON_EXE=..\.venv\Scripts\python.exe
    echo Environnement virtuel trouve: ..\.venv
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
    echo Environnement virtuel trouve: .venv
) else (
    echo ATTENTION: Environnement virtuel non trouve!
    echo Utilisation du Python systeme...
    set PYTHON_EXE=python
)

echo.
echo Configuration STAGING:
echo   - Environnement: staging
echo   - Base de donnees: DuckDB (data_staging.duckdb)
echo   - Port: 8001
echo   - URL: http://127.0.0.1:8001
echo   - Documentation: http://127.0.0.1:8001/docs
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur
echo ========================================
echo.

REM Configurer les variables d'environnement pour staging
set ENVIRONMENT=staging
set USE_DUCKDB=true
set APP_PORT=8001

%PYTHON_EXE% -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

pause

