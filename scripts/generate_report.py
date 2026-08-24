"""Genera 'reporte de acuerdo.md' a partir del XML de resultados de pytest
(--junitxml). Pensado para correr en CI (GitHub Actions) despues de pytest,
usando variables de entorno que Actions ya expone (GITHUB_SHA, GITHUB_REF_NAME,
GITHUB_ACTOR, GITHUB_RUN_ID, GITHUB_RUN_ATTEMPT).

Uso: python scripts/generate_report.py <junit.xml> <salida.md>
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def _status_icon(testcase: ET.Element) -> tuple[str, str]:
    if testcase.find("failure") is not None:
        return "FAILED", "❌"
    if testcase.find("error") is not None:
        return "ERROR", "\U0001f4a5"
    if testcase.find("skipped") is not None:
        return "SKIPPED", "⏭️"
    return "PASSED", "✅"


def build_report(junit_path: str) -> str:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise SystemExit(f"No se encontro <testsuite> en {junit_path}")

    total = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0))
    errors = int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    passed = total - failures - errors - skipped
    duration = float(suite.get("time", 0.0))

    sha = os.environ.get("GITHUB_SHA", "local")[:7]
    branch = os.environ.get("GITHUB_REF_NAME", "local")
    actor = os.environ.get("GITHUB_ACTOR", os.environ.get("USER", "local"))
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    overall_icon = "✅" if failures == 0 and errors == 0 else "❌"

    lines: list[str] = []
    lines.append("# Reporte de acuerdo")
    lines.append("")
    lines.append(f"{overall_icon} **Resultado general:** "
                 f"{'todos los tests pasaron' if failures == 0 and errors == 0 else 'hay tests que fallaron'}")
    lines.append("")
    lines.append(f"- **Commit:** `{sha}`")
    lines.append(f"- **Rama:** `{branch}`")
    lines.append(f"- **Disparado por:** {actor}")
    lines.append(f"- **Fecha (UTC):** {now}")
    if run_id:
        lines.append(f"- **Run:** {run_id} (intento {run_attempt or 1})")
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    lines.append("| Total | Pasaron | Fallaron | Errores | Omitidos | Duracion |")
    lines.append("|---|---|---|---|---|---|")
    lines.append(f"| {total} | {passed} | {failures} | {errors} | {skipped} | {duration:.2f}s |")
    lines.append("")
    lines.append("## Detalle por test")
    lines.append("")
    lines.append("| Test | Resultado |")
    lines.append("|---|---|")

    testcases = suite.findall("testcase")
    for tc in sorted(testcases, key=lambda t: (t.get("classname", ""), t.get("name", ""))):
        classname = tc.get("classname", "")
        name = tc.get("name", "")
        status, icon = _status_icon(tc)
        lines.append(f"| `{classname}.{name}` | {icon} {status} |")

    if not testcases:
        lines.append("| _(sin tests recolectados)_ | - |")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    # La consola de Windows (cp1252) no puede imprimir los emoji del reporte;
    # forzar UTF-8 evita un UnicodeEncodeError al correr esto localmente.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 3:
        raise SystemExit("Uso: python scripts/generate_report.py <junit.xml> <salida.md>")

    junit_path, output_path = sys.argv[1], sys.argv[2]
    report = build_report(junit_path)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(report)

    print(report)


if __name__ == "__main__":
    main()
