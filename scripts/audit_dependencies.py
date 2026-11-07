from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PYPI_PACKAGE_URL = "https://pypi.org/pypi/{name}/json"


@dataclass(frozen=True)
class DependencyResult:
    raw: str
    name: str
    exists: bool
    status: str
    latest_version: str | None = None
    summary: str | None = None


def normalize_requirement(raw: str) -> str | None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return None

    line = line.split("#", 1)[0].strip()
    match = re.match(r"^([A-Za-z0-9_.-]+)", line)
    if match is None:
        return None
    return match.group(1).lower().replace("_", "-")


def query_pypi(name: str) -> tuple[bool, str, str | None, str | None]:
    request = Request(
        PYPI_PACKAGE_URL.format(name=name),
        headers={"User-Agent": "payments-svc-dependency-audit/1.0"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            return False, "not_found", None, None
        return False, f"http_error_{exc.code}", None, None
    except URLError:
        return False, "network_error", None, None
    except TimeoutError:
        return False, "timeout", None, None

    info = payload.get("info", {})
    return True, "found", info.get("version"), info.get("summary")


def audit_requirements(path: Path) -> list[DependencyResult]:
    results: list[DependencyResult] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        name = normalize_requirement(raw)
        if name is None:
            continue
        exists, status, version, summary = query_pypi(name)
        results.append(
            DependencyResult(
                raw=raw.strip(),
                name=name,
                exists=exists,
                status=status,
                latest_version=version,
                summary=summary,
            )
        )
    return results


def print_report(results: list[DependencyResult]) -> None:
    print("| dependency | normalized | status | latest |")
    print("| --- | --- | --- | --- |")
    for result in results:
        latest = result.latest_version or "-"
        print(
            f"| `{result.raw}` | `{result.name}` | `{result.status}` | `{latest}` |"
        )

    missing = [result for result in results if result.status == "not_found"]
    if missing:
        print()
        print("Potential hallucinated dependencies:")
        for result in missing:
            print(f"- {result.raw}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/audit_dependencies.py requirements.txt")
        return 2

    path = Path(argv[1])
    if not path.exists():
        print(f"requirements file not found: {path}")
        return 2

    results = audit_requirements(path)
    print_report(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))