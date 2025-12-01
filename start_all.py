# start_all.py
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable  # nutzt das Python aus der aktiven venv

processes = []

def start(name, args):
    print(f"Starte {name}: {' '.join(args)}")
    p = subprocess.Popen(args, cwd=BASE_DIR)
    processes.append((name, p))

def main():
    # Backend
    start("backend", [PYTHON, "-m", "uvicorn", "backend.main:app", "--reload"])

    # Collectors
    start("screenshot", [PYTHON, "collectors/screenshot_collector.py"])
    start("window",     [PYTHON, "collectors/window_collector.py"])
    start("input",      [PYTHON, "collectors/input_collector.py"])
    start("document",   [PYTHON, "collectors/document_collector.py"])

    print("Alle Prozesse gestartet. Strg+C zum Beenden dieses Starters (Child-Prozesse laufen weiter).")
    try:
        for name, p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("Beende Prozesse...")
        for name, p in processes:
            p.terminate()

if __name__ == "__main__":
    main()
