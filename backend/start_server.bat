@echo off
echo ========================================
echo Demarrage du serveur OVH Complaints Tracker
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
echo Serveur avec DuckDB
echo URL: http://127.0.0.1:8000
echo Documentation: http://127.0.0.1:8000/docs
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur
echo ========================================
echo.

%PYTHON_EXE% -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause

