@echo off
chcp 65001 >nul
title JARVIS - KI-Assistent
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    echo Hinweis: Keine .venv gefunden - nutze System-Python.
    python main.py
)
pause
