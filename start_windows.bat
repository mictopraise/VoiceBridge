@echo off
title VoiceBridge NG
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo VoiceBridge NG requires Python 3.12.
  echo Install it from https://www.python.org/downloads/
  echo Keep your existing Python 3.14 installation.
  pause
  exit /b 1
)
if not exist .venv (
  py -3.12 -m venv .venv
  call .venv\Scripts\activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)
echo Checking VoiceBridge requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo VoiceBridge could not install its required packages.
  echo Check your internet connection, then run this file again.
  pause
  exit /b 1
)
start "" http://127.0.0.1:5050
python app.py
pause
