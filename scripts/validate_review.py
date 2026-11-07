"""Validate review JSON structure; this does not assess finding accuracy."""

import argparse
import json
from pathlib import Path
import re
import sys


CATEGORIES = {"correctness", "security", "performance", "tests", "style", "documentation"}
SEVERITIES = {"blocker", "advisory", "info"}


def validate_review(path):
    errors = []
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*\.json", path.name):
        errors.append("El nombre debe estar en kebab-case y terminar en .json")
    try:
        findings = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        return errors + [f"No se pudo leer un JSON válido: {exc}"]
    if not isinstance(findings, list):
        return errors + ["La raíz debe ser una lista de hallazgos"]
    for index, finding in enumerate(findings):
        prefix = f"Hallazgo {index + 1}"
        if not isinstance(finding, dict):
            errors.append(f"{prefix}: debe ser un objeto")
            continue
        for field in ("rule_id", "message", "suggested_fix"):
            value = finding.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: {field} debe ser texto no vacío")
        category = finding.get("category")
        if not isinstance(category, str) or category not in CATEGORIES:
            errors.append(f"{prefix}: category no permitida")
        severity = finding.get("severity")
        if not isinstance(severity, str) or severity not in SEVERITIES:
            errors.append(f"{prefix}: severity no permitida")
        location = finding.get("location")
        if not isinstance(location, dict):
            errors.append(f"{prefix}: location debe ser un objeto")
            continue
        file = location.get("file")
        if not isinstance(file, str) or not file.strip():
            errors.append(f"{prefix}: location.file debe ser texto no vacío")
        line = location.get("line")
        if type(line) is not int or line < 1:
            errors.append(f"{prefix}: location.line debe ser un entero positivo")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Archivo JSON o carpeta de reportes")
    args = parser.parse_args()
    if args.path.is_dir():
        paths = sorted(args.path.glob("*.json"))
        if not paths:
            print(f"ERROR: no hay archivos JSON en {args.path}", file=sys.stderr)
            return 1
    else:
        paths = [args.path]
    failed = False
    for path in paths:
        errors = validate_review(path)
        if errors:
            failed = True
            for error in errors:
                print(f"ERROR {path}: {error}", file=sys.stderr)
        else:
            print(f"OK {path}")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
