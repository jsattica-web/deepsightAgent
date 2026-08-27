$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host ".venv was not found. Create it first:"
    Write-Host "py -3.12 -m venv .venv"
    Write-Host ".venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

& $Python -m uvicorn app.main:app --reload --port 8000 @args