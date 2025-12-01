@echo off
REM Pfad zu deinem Projekt
cd /d C:\dev\localtracker

REM Virtuelle Umgebung aktivieren
call venv\Scripts\activate.bat

REM Backend optional mitstarten:
start "backend" cmd /k uvicorn backend.main:app --reload

REM Screenshot-Collector
start "screenshot" cmd /k python collectors\screenshot_collector.py

REM Window-Collector
start "window" cmd /k python collectors\window_collector.py

REM Input-Collector (Maus & Tastatur)
start "input" cmd /k python collectors\input_collector.py

REM Document-Collector (Dateiänderungen)
start "document" cmd /k python collectors\document_collector.py
