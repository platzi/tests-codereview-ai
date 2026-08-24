"""Genera 'reporte de revision.md': el diff contra `develop` mas la rubrica
de reviewer.md convertida en checklist, para que una persona haga el review
(no llama a ningun LLM). Pensado para correr en CI (GitHub Actions).

Uso: python scripts/generate_review_checklist.py <rubric.md> <diff.txt> <salida.md>
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone

MAX_DIFF_CHARS = 60_000


def extract_categories(rubric_path: str) -> list[str]:
    with open(rubric_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    # Busca la seccion "## Rubrica" (o "## Rúbrica") y extrae los items
    # numerados en negrita: "1. **Correccion** - ..."
    match = re.search(r"##\s*R[uú]brica(.*?)(\n##\s|\Z)", text, re.DOTALL)
    section = match.group(1) if match else text

    categories = re.findall(r"^\d+\.\s+\*\*(.+?)\*\*", section, re.MULTILINE)
    return categories


def build_report(rubric_path: str, diff_path: str) -> str:
    categories = extract_categories(rubric_path)

    with open(diff_path, "r", encoding="utf-8", errors="replace") as fh:
        diff_text = fh.read()

    truncated = False
    if len(diff_text) > MAX_DIFF_CHARS:
        diff_text = diff_text[:MAX_DIFF_CHARS]
        truncated = True

    sha = os.environ.get("GITHUB_SHA", "local")[:7]
    branch = os.environ.get("GITHUB_REF_NAME", "local")
    actor = os.environ.get("GITHUB_ACTOR", os.environ.get("USER", "local"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = []
    lines.append("# Reporte de revision")
    lines.append("")
    lines.append("Checklist generado automaticamente a partir de "
                 f"`{os.path.basename(rubric_path)}` y el diff contra `develop`. "
                 "No usa ningun LLM: es para que una persona complete la revision "
                 "siguiendo la rubrica.")
    lines.append("")
    lines.append(f"- **Commit:** `{sha}`")
    lines.append(f"- **Rama:** `{branch}`")
    lines.append(f"- **Disparado por:** {actor}")
    lines.append(f"- **Fecha (UTC):** {now}")
    lines.append(f"- **Comparado contra:** `origin/develop`")
    lines.append("")
    lines.append("## Checklist de revision")
    lines.append("")
    if categories:
        for cat in categories:
            lines.append(f"- [ ] {cat}")
    else:
        lines.append(f"_No se pudieron extraer categorias de {rubric_path}; "
                     "revisar el archivo manualmente._")
    lines.append("")
    lines.append(f"Ver la rubrica completa (severidad, formato de salida esperado, "
                 f"reglas anti-alucinacion) en `{os.path.basename(rubric_path)}`.")
    lines.append("")
    lines.append("## Diff contra develop")
    lines.append("")
    if not diff_text.strip():
        lines.append("_Sin diferencias respecto a `develop`._")
    else:
        lines.append("```diff")
        lines.append(diff_text)
        if truncated:
            lines.append(f"\n... (diff truncado a {MAX_DIFF_CHARS} caracteres) ...")
        lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    # El diff puede traer acentos/enies; forzar UTF-8 en stdout evita un
    # UnicodeEncodeError al correr esto localmente en consola de Windows (cp1252).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 4:
        raise SystemExit(
            "Uso: python scripts/generate_review_checklist.py <rubric.md> <diff.txt> <salida.md>"
        )

    rubric_path, diff_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
    report = build_report(rubric_path, diff_path)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(report)

    print(report)


if __name__ == "__main__":
    main()
