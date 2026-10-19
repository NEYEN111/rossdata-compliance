@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero instala el entorno siguiendo README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run.py
pause
