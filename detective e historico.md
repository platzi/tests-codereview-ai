# Detective e historico

Politica de calibracion de confianza para `payments-svc`, generada automaticamente combinando evidencia en vivo de este run con evidencia historica ya documentada en el repositorio. Diseñada segun las guias de `to_review.md` (seccion 20: CI/CD Ownership). `to_review.md` no incluye una definicion formal de 'Confidence Matrix' en este repositorio (solo la seccion 20 esta presente); esta politica es un diseño concreto para este proyecto, no la implementacion de un estandar externo.

- **Commit:** `local`
- **Rama:** `local`
- **Disparado por:** local
- **Fecha (UTC):** 2026-08-24 06:07:57 UTC

---

## 1. Detective — evidencia en vivo de este run

### 1.1 Tests

- Total: 51 | Pasaron: 51 | Fallaron: 0 | Errores: 0 | Omitidos: 0

**14 clases de test confirmadas corriendo** (51 casos individuales):

- `tests.test_amounts.CurrencyConfigIsSingleSourceOfTruthTests` — 3 caso(s)
- `tests.test_amounts.ErrorPrecedenceIsUnifiedBetweenEntryPointsTests` — 2 caso(s)
- `tests.test_amounts.MaxAmountIsPerCurrencyTests` — 3 caso(s)
- `tests.test_amounts.NormalizeCurrencyEmptyAndMissingShareMessageTests` — 3 caso(s)
- `tests.test_amounts.NormalizeCurrencyRejectsNonStringTests` — 3 caso(s)
- `tests.test_amounts.ParseAmountRejectsFloatTests` — 3 caso(s)
- `tests.test_amounts.RoundMoneyForCurrencyRespectsExponentTests` — 4 caso(s)
- `tests.test_amounts.ValidateAmountGuardsNaNTests` — 3 caso(s)
- `tests.test_amounts.ValidateNonNegativeAmountGuardsNaNAndInfinityTests` — 8 caso(s)
- `tests.test_amounts.ZeroAmountIsInvalidTests` — 5 caso(s)
- `tests.test_auth.CanRefundCustomerRoleTests` — 3 caso(s)
- `tests.test_auth.CanRefundPrivilegedRolesTests` — 2 caso(s)
- `tests.test_auth.CanRefundRequiresAuthenticationTests` — 1 caso(s)
- `tests.test_auth.RequireAuthenticatedTests` — 2 caso(s)

### 1.2 Seguridad (semgrep)

- Total hallazgos: 0
  - ERROR: 0
  - WARNING: 0
  - INFO: 0

## 2. Historico — evidencia ya documentada en el repositorio

### 2.1 Catalogo de contrato (`FAILURES_MODE.md`)

| Estado | Nodos |
|---|---|
| `DEFINIDO-INCORRECTO` | 10 |
| `IMPLÍCITO` | 9 |
| `INDEFINIDO` | 9 |
| `DEFINIDO-OK` | 1 |

Cobertura de este catalogo: solo `amounts.py`. No existe un catalogo equivalente de riesgo documentado para `api.py`, `auth.py`, `refunds.py` ni `settlement.py`.

### 2.2 Mutation testing legado (`tests_mutation_report.md`)

| Archivo | Mutantes generados | KILLED reportado | SURVIVED reportado |
|---|---|---|---|
| `amounts.py` | 124 | 124 | 0 |
| `refunds.py` | 38 | 38 | 0 |
| `api.py` | 30 | 30 | 0 |
| `auth.py` | 24 | 24 | 0 |

⚠️ **`tests_mutation_report.md` concluye explicitamente que estos numeros NO son confiables** (el runner de tests crasheaba antes de ejecutar nada, y ese crash se contaba como "killed" para los 216 mutantes). Esta politica de calibracion **no** trata estos numeros como evidencia real de cobertura de mutacion.

### 2.3 Suite mata-mutantes (`suite_mata_mutantes.txt`)

- Mutantes con test dedicado que los mata, confirmados en esta sesion (filas `DETECTED` en la tabla): **10**
- Alcance: `amounts.py` (validate_non_negative_amount) y `auth.py` (require_authenticated, can_refund). Ver el archivo para el detalle mutante-por-mutante.

### 2.4 Corrida cruda de mutatest (`mutations.txt`)

- SURVIVED: 4 | DETECTED: 6 | TOTAL RUNS: 10
- Nota: corrida parcial/muestreada (mutatest con `-n`), no un barrido exhaustivo de todos los mutantes posibles.

## 3. Politica de calibracion — confianza por modulo

Combina 1 y 2 en una calificacion por modulo. Sigue la advertencia de `to_review.md` (20.7): *"The confidence score must not be manually increased simply because CI is green."* Un modulo puede tener CI en verde y confianza baja si no hay tests reales, sin importar lo que digan numeros historicos de mutation testing no confiables.

| Modulo | Tests dedicados | Seguridad ERROR | Evidencia de mutacion confiable | Riesgo documentado (FAILURES_MODE) | Confianza | Gate sugerido |
|---|---|---|---|---|---|---|
| `amounts.py` | Si | 0 | Si (confirmado esta sesion, ver 2.3) | Si (FAILURES_MODE.md, 29 nodos) | **Alto** | PASS |
| `api.py` | No | 0 | No confiable (ver 2.2) | No documentado | **Bajo** | WARN — sin tests reales, no debe tratarse como validado |
| `auth.py` | Si | 0 | Si (confirmado esta sesion, ver 2.3) | No documentado | **Alto** | PASS |
| `refunds.py` | No | 0 | No confiable (ver 2.2) | No documentado | **Bajo** | WARN — sin tests reales, no debe tratarse como validado |
| `settlement.py` | No | 0 | No confiable (ver 2.2) | No documentado | **Bajo** | WARN — sin tests reales, no debe tratarse como validado |

## 4. Advertencias explicitas (supuestos no verificables)

- No hay medicion de cobertura real integrada (sin `pytest-cov` en el pipeline); el gate de cobertura de `to_review.md` (20.5) no esta implementado todavia.
- Modulos sin ningun test dedicado: `api.py`, `refunds.py`, `settlement.py`. Los numeros historicos de mutation testing para estos archivos no son evidencia real de confianza (ver 2.2).
- No hay integracion de AI Review con un LLM real (sin API key de OpenRouter configurada); el 'AI Review' actual del pipeline es un checklist generado a partir de `reviewer.md`, para revision humana, no una evaluacion automatizada real (ver `to_review.md` 20.6).
- Esta politica **no** debe leerse como "CI en verde = seguro para produccion" (`to_review.md`, 20.7).
