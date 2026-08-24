"""Genera 'reporte de seguridad.md' a partir de la salida JSON de semgrep
(--json --output). Pensado para correr en CI (GitHub Actions) despues de
semgrep, usando las mismas variables de entorno que generate_report.py.

Uso: python scripts/generate_security_report.py <semgrep.json> <salida.md>

Codigo de salida: 1 si hay al menos un hallazgo de severidad ERROR
(para que el step de CI pueda fallar el job en base a esto), 0 en caso
contrario. WARNING/INFO no fallan el build, solo se reportan.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

SEVERITY_ICON = {"ERROR": "\U0001f6a8", "WARNING": "⚠️", "INFO": "ℹ️"}
SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def build_report(semgrep_json_path: str) -> tuple[str, int]:
    with open(semgrep_json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    results = data.get("results", [])
    errors_from_scan = data.get("errors", [])

    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for r in results:
        sev = r.get("extra", {}).get("severity", "INFO")
        counts[sev] = counts.get(sev, 0) + 1

    sha = os.environ.get("GITHUB_SHA", "local")[:7]
    branch = os.environ.get("GITHUB_REF_NAME", "local")
    actor = os.environ.get("GITHUB_ACTOR", os.environ.get("USER", "local"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    total = len(results)
    overall_icon = "✅" if counts["ERROR"] == 0 else "❌"
    result_text = (
        "sin hallazgos ERROR" if counts["ERROR"] == 0
        else f"{counts['ERROR']} hallazgo(s) ERROR"
    )

    lines: list[str] = []
    lines.append("# Reporte de seguridad")
    lines.append("")
    lines.append(f"{overall_icon} **Resultado:** {result_text}")
    lines.append("")
    lines.append(f"- **Commit:** `{sha}`")
    lines.append(f"- **Rama:** `{branch}`")
    lines.append(f"- **Disparado por:** {actor}")
    lines.append(f"- **Fecha (UTC):** {now}")
    lines.append(f"- **Herramienta:** semgrep (p/security-audit, p/python, p/owasp-top-ten)")
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    lines.append("| Total | Error | Warning | Info |")
    lines.append("|---|---|---|---|")
    lines.append(f"| {total} | {counts['ERROR']} | {counts['WARNING']} | {counts['INFO']} |")
    lines.append("")
    lines.append("## Detalle de hallazgos")
    lines.append("")

    if not results:
        lines.append("_Sin hallazgos._")
    else:
        lines.append("| Severidad | Regla | Archivo:linea | Mensaje |")
        lines.append("|---|---|---|---|")
        ordered = sorted(
            results,
            key=lambda r: SEVERITY_ORDER.get(r.get("extra", {}).get("severity", "INFO"), 3),
        )
        for r in ordered:
            sev = r.get("extra", {}).get("severity", "INFO")
            icon = SEVERITY_ICON.get(sev, "")
            rule = r.get("check_id", "?")
            path = r.get("path", "?")
            line_no = r.get("start", {}).get("line", "?")
            message = r.get("extra", {}).get("message", "").replace("\n", " ").replace("|", "\\|")
            if len(message) > 200:
                message = message[:200] + "..."
            lines.append(f"| {icon} {sev} | `{rule}` | `{path}:{line_no}` | {message} |")

    if errors_from_scan:
        lines.append("")
        lines.append("## Errores del propio scan (no son hallazgos de seguridad)")
        lines.append("")
        for e in errors_from_scan:
            lines.append(f"- {e.get('message', e)}")

    lines.append("")
    report = "\n".join(lines)
    exit_code = 1 if counts["ERROR"] > 0 else 0
    return report, exit_code


def main() -> None:
    # La consola de Windows (cp1252) no puede imprimir los emoji del reporte;
    # forzar UTF-8 evita un UnicodeEncodeError al correr esto localmente.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 3:
        raise SystemExit("Uso: python scripts/generate_security_report.py <semgrep.json> <salida.md>")

    semgrep_json_path, output_path = sys.argv[1], sys.argv[2]
    report, exit_code = build_report(semgrep_json_path)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(report)

    print(report)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
