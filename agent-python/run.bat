@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo .venv was not found. Create it first:
    echo py -3.12 -m venv .venv
    echo .venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)

".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000 %*