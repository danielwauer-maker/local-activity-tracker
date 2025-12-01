@echo off
REM Pfad zu deinem Projekt
cd /d C:\dev\localtracker

REM Virtuelle Umgebung aktivieren
call venv\Scripts\activate.bat

REM Backend optional mitstarten:
start "backend" cmd /k uvicorn backend.main:app --reload