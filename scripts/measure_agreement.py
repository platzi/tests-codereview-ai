import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_labels(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    labels = data.get("labels")
    if not isinstance(labels, list) or not labels:
        raise ValueError(f"{path.name}: 'labels' debe ser una lista no vacia.")

    result = {}
    for label in labels:
        if not isinstance(label, dict):
            raise ValueError(f"{path.name}: etiqueta invalida.")

        case_id = label.get("case_id")
        category = label.get("category")
        present = label.get("present")

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"{path.name}: case_id invalido.")
        if category not in (
            "correctness", "security", "performance",
            "tests", "style", "documentation",
        ):
            raise ValueError(f"{path.name}: categoria invalida.")
        if type(present) is not bool:
            raise ValueError(f"{path.name}: present debe ser true o false.")

        key = (case_id, category)
        if key in result:
            raise ValueError(f"{path.name}: etiqueta duplicada: {key}")
        result[key] = present

    return result

def main():
    try:
        human = load_labels(ROOT / "samples/agreement/human-labels.json")
        ai = load_labels(ROOT / "samples/agreement/ai-labels.json")

        if human.keys() != ai.keys():
            raise ValueError(
                "Los archivos deben contener los mismos case_id y category. "
                "Una etiqueta ausente no equivale a present=false."
            )
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Comparacion de presencia de hallazgos (no de severidad)")
    print()
    print(f"{'Categoria':<18} {'Casos':>5} {'Acuerdo':>10} {'Kappa':>10}")

    for category in sorted({key[1] for key in human}):
        keys = [key for key in human if key[1] == category]
        n = len(keys)
        matches = sum(human[key] == ai[key] for key in keys)
        observed = matches / n

        human_positive = sum(human[key] for key in keys) / n
        ai_positive = sum(ai[key] for key in keys) / n
        expected = (
            human_positive * ai_positive
            + (1 - human_positive) * (1 - ai_positive)
        )

        if abs(1 - expected) < 1e-12:
            kappa_text = "N/D"
        else:
            kappa = (observed - expected) / (1 - expected)
            kappa_text = f"{kappa:.3f}"

        print(
            f"{category:<18} {n:>5} "
            f"{observed:>9.1%} {kappa_text:>10}"
        )

    print()
    print("N/D: kappa indefinido porque el acuerdo esperado es 1.")
    print("Con un solo caso por categoria no se puede calibrar una politica.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
