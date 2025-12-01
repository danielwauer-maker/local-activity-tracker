import compileall
import sys
from pathlib import Path
import importlib.util
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Zeitstempel für die Logdatei
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file_path = LOG_DIR / f"check_{timestamp}.log"

# Logfile öffnen
log_file = open(log_file_path, "w", encoding="utf-8")

def log(msg: str):
    print(msg)
    log_file.write(msg + "\n")


def compile_all():
    log("== Syntax-Check via compileall ==")
    ok = compileall.compile_dir(str(PROJECT_ROOT), quiet=1)
    if ok:
        log("✔ Alle .py-Dateien sind syntaktisch OK.")
    else:
        log("✘ Syntaxfehler vorhanden.")
    return ok


def import_all():
    log("\n== Import-Check für alle .py-Dateien ==")
    errors = []

    for py_file in PROJECT_ROOT.rglob("*.py"):
        if py_file.name in {"check_project.py"}:
            continue

        rel = py_file.relative_to(PROJECT_ROOT)
        module_name = ".".join(rel.with_suffix("").parts)

        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            log(f"✔ import {module_name}")
        except Exception as e:
            log(f"✘ Fehler beim Import von {module_name}: {e}")
            errors.append((module_name, e))

    if not errors:
        log("\n✔ Alle Module ließen sich importieren.")
    else:
        log("\n✘ Einige Module konnten nicht importiert werden:")
        for name, err in errors:
            log(f"  - {name}: {err}")

    return not errors


if __name__ == "__main__":
    log(f"=== Projekt-Check gestartet: {timestamp} ===\n")
    ok_syntax = compile_all()
    ok_imports = import_all()
    log("\n=== Check abgeschlossen ===")

    log_file.close()

    if not (ok_syntax and ok_imports):
        log(f"\nErgebnis: Probleme gefunden → Log siehe: {log_file_path}")
        sys.exit(1)

    log(f"\nErgebnis: Alles OK → Log siehe: {log_file_path}")
