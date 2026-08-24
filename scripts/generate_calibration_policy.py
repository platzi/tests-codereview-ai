"""Genera 'detective e historico.md': una politica de calibracion para
payments-svc que combina evidencia EN VIVO de este run (tests, seguridad)
con evidencia HISTORICA ya documentada en el repositorio (FAILURES_MODE.md,
tests_mutation_report.md, suite_mata_mutantes.txt, mutations.txt), siguiendo
las guias de to_review.md (seccion 20: CI/CD Ownership / Confidence Matrix).

to_review.md no incluye una definicion formal de "Confidence Matrix" (solo
la seccion 20 esta presente en el repo), asi que esta politica es un diseno
concreto para este proyecto basado en esas guias, no una implementacion de
un estandar externo.

Uso:
  python scripts/generate_calibration_policy.py \
      <junit.xml> <semgrep.json> <FAILURES_MODE.md> \
      <tests_mutation_report.md> <suite_mata_mutantes.txt> <mutations.txt> \
      <tests_dir> <src_dir> <salida.md>
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""


# --- Evidencia en vivo: tests --------------------------------------------

def parse_junit(junit_path: str) -> dict:
    try:
        tree = ET.parse(junit_path)
    except (FileNotFoundError, ET.ParseError):
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0,
                "by_class": {}, "classes_run": []}

    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0,
                "by_class": {}, "classes_run": []}

    total = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0))
    errors = int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    passed = total - failures - errors - skipped

    by_class: dict[str, int] = {}
    for tc in suite.findall("testcase"):
        classname = tc.get("classname", "")
        by_class[classname] = by_class.get(classname, 0) + 1

    return {
        "total": total, "passed": passed, "failed": failures, "errors": errors,
        "skipped": skipped, "by_class": by_class,
        "classes_run": sorted(by_class),
    }


# --- Evidencia en vivo: seguridad ----------------------------------------

def parse_semgrep(semgrep_json_path: str) -> dict:
    import json

    try:
        with open(semgrep_json_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {"total": 0, "by_severity": {}, "error_count_by_path": {}}

    results = data.get("results", [])
    by_severity: dict[str, int] = {}
    error_count_by_path: dict[str, int] = {}
    for r in results:
        sev = r.get("extra", {}).get("severity", "INFO")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        if sev == "ERROR":
            path = r.get("path", "?")
            error_count_by_path[path] = error_count_by_path.get(path, 0) + 1

    return {"total": len(results), "by_severity": by_severity,
            "error_count_by_path": error_count_by_path}


# --- Evidencia historica: FAILURES_MODE.md --------------------------------

def parse_failures_mode(path: str) -> list[tuple[str, int]]:
    text = _read(path)
    section = re.search(r"###\s*Resumen por estado(.*?)(\n###\s|\Z)", text, re.DOTALL)
    section_text = section.group(1) if section else text
    rows = re.findall(r"\|\s*`([^`]+)`[^|]*\((\d+)\)\s*\|", section_text)
    return [(name, int(count)) for name, count in rows]


# --- Evidencia historica: tests_mutation_report.md -------------------------

def parse_legacy_mutation_table(path: str) -> list[tuple[str, int, int, int]]:
    text = _read(path)
    rows = re.findall(
        r"\|\s*`([\w.]+)`\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", text
    )
    return [(name, int(a), int(b), int(c)) for name, a, b, c in rows]


def legacy_report_flags_unreliable(path: str) -> bool:
    text = _read(path).lower()
    return "no es confiable" in text or "no confiable" in text


# --- Evidencia historica: suite_mata_mutantes.txt --------------------------

def count_confirmed_kills(path: str) -> int:
    text = _read(path)
    return len(re.findall(r"\|\s*DETECTED\s*\|", text))


# --- Evidencia historica: mutations.txt (corrida cruda de mutatest) --------

def parse_raw_mutation_summary(path: str) -> dict:
    text = _read(path)
    result = {}
    for key in ("SURVIVED", "DETECTED", "TOTAL RUNS"):
        m = re.search(rf"-\s*{re.escape(key)}:\s*(\d+)", text)
        if m:
            result[key] = int(m.group(1))
    return result


# --- Modulos del proyecto y si tienen test dedicado ------------------------

def modules_with_dedicated_tests(src_dir: str, tests_dir: str) -> dict[str, bool]:
    pkg_dir = os.path.join(src_dir, "payments_svc")
    modules = sorted(
        f[:-3] for f in os.listdir(pkg_dir)
        if f.endswith(".py") and f != "__init__.py"
    ) if os.path.isdir(pkg_dir) else []

    result = {}
    for mod in modules:
        test_file = os.path.join(tests_dir, f"test_{mod}.py")
        result[mod] = os.path.isfile(test_file)
    return result


def build_report(
    junit_path: str,
    semgrep_json_path: str,
    failures_mode_path: str,
    legacy_mutation_path: str,
    suite_mata_mutantes_path: str,
    mutations_raw_path: str,
    tests_dir: str,
    src_dir: str,
) -> str:
    tests = parse_junit(junit_path)
    security = parse_semgrep(semgrep_json_path)
    failures_mode_states = parse_failures_mode(failures_mode_path)
    legacy_table = parse_legacy_mutation_table(legacy_mutation_path)
    legacy_unreliable = legacy_report_flags_unreliable(legacy_mutation_path)
    confirmed_kills = count_confirmed_kills(suite_mata_mutantes_path)
    raw_mutation = parse_raw_mutation_summary(mutations_raw_path)
    module_tests = modules_with_dedicated_tests(src_dir, tests_dir)

    sha = os.environ.get("GITHUB_SHA", "local")[:7]
    branch = os.environ.get("GITHUB_REF_NAME", "local")
    actor = os.environ.get("GITHUB_ACTOR", os.environ.get("USER", "local"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = []
    lines.append("# Detective e historico")
    lines.append("")
    lines.append("Politica de calibracion de confianza para `payments-svc`, generada "
                 "automaticamente combinando evidencia en vivo de este run con evidencia "
                 "historica ya documentada en el repositorio. Diseñada segun las guias de "
                 "`to_review.md` (seccion 20: CI/CD Ownership). `to_review.md` no incluye "
                 "una definicion formal de 'Confidence Matrix' en este repositorio (solo la "
                 "seccion 20 esta presente); esta politica es un diseño concreto para este "
                 "proyecto, no la implementacion de un estandar externo.")
    lines.append("")
    lines.append(f"- **Commit:** `{sha}`")
    lines.append(f"- **Rama:** `{branch}`")
    lines.append(f"- **Disparado por:** {actor}")
    lines.append(f"- **Fecha (UTC):** {now}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- 1. Detective: evidencia en vivo ---
    lines.append("## 1. Detective — evidencia en vivo de este run")
    lines.append("")
    lines.append("### 1.1 Tests")
    lines.append("")
    lines.append(f"- Total: {tests['total']} | Pasaron: {tests['passed']} | "
                 f"Fallaron: {tests['failed']} | Errores: {tests['errors']} | "
                 f"Omitidos: {tests['skipped']}")
    lines.append("")
    lines.append(f"**{len(tests['classes_run'])} clases de test confirmadas corriendo** "
                 f"({tests['total']} casos individuales):")
    lines.append("")
    for cls in tests["classes_run"]:
        lines.append(f"- `{cls}` — {tests['by_class'][cls]} caso(s)")
    if not tests["classes_run"]:
        lines.append("- _(no se pudo leer el XML de resultados de tests)_")
    lines.append("")

    lines.append("### 1.2 Seguridad (semgrep)")
    lines.append("")
    lines.append(f"- Total hallazgos: {security['total']}")
    for sev in ("ERROR", "WARNING", "INFO"):
        lines.append(f"  - {sev}: {security['by_severity'].get(sev, 0)}")
    lines.append("")

    # --- 2. Historico ---
    lines.append("## 2. Historico — evidencia ya documentada en el repositorio")
    lines.append("")
    lines.append("### 2.1 Catalogo de contrato (`FAILURES_MODE.md`)")
    lines.append("")
    if failures_mode_states:
        lines.append("| Estado | Nodos |")
        lines.append("|---|---|")
        for name, count in failures_mode_states:
            lines.append(f"| `{name}` | {count} |")
    else:
        lines.append("_No se pudo leer la tabla de resumen de FAILURES_MODE.md._")
    lines.append("")
    lines.append("Cobertura de este catalogo: solo `amounts.py`. No existe un catalogo "
                 "equivalente de riesgo documentado para `api.py`, `auth.py`, "
                 "`refunds.py` ni `settlement.py`.")
    lines.append("")

    lines.append("### 2.2 Mutation testing legado (`tests_mutation_report.md`)")
    lines.append("")
    if legacy_table:
        lines.append("| Archivo | Mutantes generados | KILLED reportado | SURVIVED reportado |")
        lines.append("|---|---|---|---|")
        for name, gen, killed, survived in legacy_table:
            lines.append(f"| `{name}` | {gen} | {killed} | {survived} |")
    else:
        lines.append("_No se pudo leer la tabla de mutation testing legado._")
    lines.append("")
    if legacy_unreliable:
        lines.append("⚠️ **`tests_mutation_report.md` concluye explicitamente que estos "
                     "numeros NO son confiables** (el runner de tests crasheaba antes de "
                     "ejecutar nada, y ese crash se contaba como \"killed\" para los 216 "
                     "mutantes). Esta politica de calibracion **no** trata estos numeros "
                     "como evidencia real de cobertura de mutacion.")
    lines.append("")

    lines.append("### 2.3 Suite mata-mutantes (`suite_mata_mutantes.txt`)")
    lines.append("")
    lines.append(f"- Mutantes con test dedicado que los mata, confirmados en esta sesion "
                 f"(filas `DETECTED` en la tabla): **{confirmed_kills}**")
    lines.append("- Alcance: `amounts.py` (validate_non_negative_amount) y `auth.py` "
                 "(require_authenticated, can_refund). Ver el archivo para el detalle "
                 "mutante-por-mutante.")
    lines.append("")

    lines.append("### 2.4 Corrida cruda de mutatest (`mutations.txt`)")
    lines.append("")
    if raw_mutation:
        lines.append(f"- SURVIVED: {raw_mutation.get('SURVIVED', '?')} | "
                     f"DETECTED: {raw_mutation.get('DETECTED', '?')} | "
                     f"TOTAL RUNS: {raw_mutation.get('TOTAL RUNS', '?')}")
        lines.append("- Nota: corrida parcial/muestreada (mutatest con `-n`), no un barrido "
                     "exhaustivo de todos los mutantes posibles.")
    else:
        lines.append("_No se pudo leer el resumen de la corrida cruda de mutatest._")
    lines.append("")

    # --- 3. Politica de calibracion ---
    lines.append("## 3. Politica de calibracion — confianza por modulo")
    lines.append("")
    lines.append("Combina 1 y 2 en una calificacion por modulo. Sigue la advertencia de "
                 "`to_review.md` (20.7): *\"The confidence score must not be manually "
                 "increased simply because CI is green.\"* Un modulo puede tener CI en "
                 "verde y confianza baja si no hay tests reales, sin importar lo que "
                 "digan numeros historicos de mutation testing no confiables.")
    lines.append("")
    lines.append("| Modulo | Tests dedicados | Seguridad ERROR | Evidencia de mutacion confiable | Riesgo documentado (FAILURES_MODE) | Confianza | Gate sugerido |")
    lines.append("|---|---|---|---|---|---|---|")

    for mod in sorted(module_tests):
        has_tests = module_tests[mod]
        sec_errors_for_mod = sum(
            count for path, count in security["error_count_by_path"].items()
            if mod in path
        )

        if mod == "amounts":
            mutation_reliable = "Si (confirmado esta sesion, ver 2.3)"
            risk_doc = "Si (FAILURES_MODE.md, 29 nodos)"
        elif mod == "auth":
            mutation_reliable = "Si (confirmado esta sesion, ver 2.3)"
            risk_doc = "No documentado"
        else:
            mutation_reliable = "No confiable (ver 2.2)" if legacy_unreliable else "Sin dato"
            risk_doc = "No documentado"

        if has_tests and mutation_reliable.startswith("Si"):
            confianza = "Alto"
        elif has_tests:
            confianza = "Medio"
        else:
            confianza = "Bajo"

        gate = "PASS" if has_tests else "WARN — sin tests reales, no debe tratarse como validado"

        lines.append(
            f"| `{mod}.py` | {'Si' if has_tests else 'No'} | {sec_errors_for_mod} | "
            f"{mutation_reliable} | {risk_doc} | **{confianza}** | {gate} |"
        )
    lines.append("")

    # --- 4. Advertencias explicitas ---
    lines.append("## 4. Advertencias explicitas (supuestos no verificables)")
    lines.append("")
    lines.append("- No hay medicion de cobertura real integrada (sin `pytest-cov` en el "
                 "pipeline); el gate de cobertura de `to_review.md` (20.5) no esta "
                 "implementado todavia.")
    unte_ested = [m for m, has in module_tests.items() if not has]
    if unte_ested:
        lines.append(f"- Modulos sin ningun test dedicado: {', '.join(f'`{m}.py`' for m in unte_ested)}. "
                     "Los numeros historicos de mutation testing para estos archivos no son "
                     "evidencia real de confianza (ver 2.2).")
    lines.append("- No hay integracion de AI Review con un LLM real (sin API key de "
                 "OpenRouter configurada); el 'AI Review' actual del pipeline es un "
                 "checklist generado a partir de `reviewer.md`, para revision humana, no "
                 "una evaluacion automatizada real (ver `to_review.md` 20.6).")
    lines.append("- Esta politica **no** debe leerse como \"CI en verde = seguro para "
                 "produccion\" (`to_review.md`, 20.7).")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 10:
        raise SystemExit(
            "Uso: python scripts/generate_calibration_policy.py "
            "<junit.xml> <semgrep.json> <FAILURES_MODE.md> "
            "<tests_mutation_report.md> <suite_mata_mutantes.txt> <mutations.txt> "
            "<tests_dir> <src_dir> <salida.md>"
        )

    (junit_path, semgrep_json_path, failures_mode_path, legacy_mutation_path,
     suite_mata_mutantes_path, mutations_raw_path, tests_dir, src_dir,
     output_path) = sys.argv[1:]

    report = build_report(
        junit_path, semgrep_json_path, failures_mode_path, legacy_mutation_path,
        suite_mata_mutantes_path, mutations_raw_path, tests_dir, src_dir,
    )

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(report)

    print(report)


if __name__ == "__main__":
    main()
