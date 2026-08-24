# Reporte de tests reales vs. mutaciones (`tests_results.txt`)

Este documento es solo de lectura/analisis. No modifica codigo fuente ni
tests existentes. Objetivo: mostrar los tests reales que corren hoy y
diagnosticar los resultados de `tests_results.txt`, incluyendo por que el
0% de mutantes sobrevivientes que reporta ese archivo **no es confiable**.

---

## 1. Tests reales que existen y corren hoy

Unico archivo de tests en el repo: `tests/test_amounts.py` (unittest,
sobre `src/payments_svc/amounts.py`). No existe `test_api.py`,
`test_auth.py` ni `test_refunds.py`.

Comando verificado en esta sesion:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Resultado real (confirmado ahora mismo): **`Ran 30 tests ... FAILED (failures=1)`**
— 29 pasan, 1 falla a proposito (`CanaryDeliberateFailureTests`, un test
canario que siempre debe fallar, usado para validar que el runner reporta
fallos).

| Clase de test | # tests | Nodo de FAILURES_MODE.md | Resultado |
|---|---|---|---|
| `ZeroAmountIsInvalidTests` | 5 | FR-03 / CN-01 | OK |
| `ValidateAmountGuardsNaNTests` | 3 | EQ-01 | OK |
| `ParseAmountRejectsFloatTests` | 3 | EQ-02 | OK |
| `NormalizeCurrencyRejectsNonStringTests` | 3 | EQ-05 | OK |
| `CurrencyConfigIsSingleSourceOfTruthTests` | 3 | EQ-08 | OK |
| `MaxAmountIsPerCurrencyTests` | 3 | CN-03 | OK |
| `RoundMoneyForCurrencyRespectsExponentTests` | 4 | CN-04 | OK |
| `ErrorPrecedenceIsUnifiedBetweenEntryPointsTests` | 2 | CN-06 | OK |
| `NormalizeCurrencyEmptyAndMissingShareMessageTests` | 3 | NV-03 | OK |
| `CanaryDeliberateFailureTests` | 1 | (ninguno, es un canario) | **FALLA a proposito** |

---

## 2. Que contiene `tests_results.txt`

El archivo esta en **UTF-16 LE**, no UTF-8 (por eso se ve como texto con
espacios entre letras al abrirlo con herramientas que asumen UTF-8). Al
decodificarlo correctamente aparecen 216 registros de mutmut, con este
resumen final incluido en el propio archivo:

```
total jobs: 216
complete: 216 (100.00%)
surviving mutants: 0 (0.00%)
```

Es decir: **el archivo dice que no sobrevivio ningun mutante**, en los 4
archivos de `src/payments_svc/`:

| Archivo mutado | # mutantes generados | Reportados KILLED | Reportados SURVIVED |
|---|---|---|---|
| `amounts.py` | 124 | 124 | 0 |
| `refunds.py` | 38 | 38 | 0 |
| `api.py` | 30 | 30 | 0 |
| `auth.py` | 24 | 24 | 0 |
| **Total** | **216** | **216** | **0** |

**No hay ninguna fila que decir "sobreviviente" porque el archivo no
registra ninguna.** Por eso no se puede entregar la tabla de mutantes
sobrevivientes que pediste con datos reales: el archivo, tal como esta,
no contiene ese caso.

---

## 3. Por que ese "0% de sobrevivientes" es sospechoso (evidencia)

Un 100% de mutantes "matados" en `auth.py` y `api.py` es matematicamente
imposible con la cobertura de tests que existe hoy: **no hay ningun test
que importe o ejecute `auth.py` (`require_authenticated`, `can_refund`) ni
que llame a los endpoints de `api.py`**. Solo `test_amounts.py` existe, y
solo cubre `amounts.py`.

Reproduje, en esta sesion, el comando que mutmut usaria por defecto
(`python -m pytest`, corrido desde la raiz del repo, sin argumentos) y
encontre esto:

```
$ python -m pytest -q
...
ERROR tests_results.txt - UnicodeDecodeError: 'utf-8' codec can't decode byte...
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.19s
exit code: 2
```

**pytest se interrumpe antes de correr ningun test**, porque intenta
"coleccionar" el propio `tests_results.txt` (por su nombre `..._test...`)
y no puede decodificarlo (es UTF-16, pytest espera UTF-8). El exit code es
`2` ("interrupted"), no `0` (todo paso) ni `1` (fallaron tests) — es un
tercer estado que significa "el runner no pudo ejecutar nada".

Si mutmut interpreta cualquier salida distinta de 0 como "el mutante fue
matado" (comportamiento tipico cuando el comando de test esta mal
configurado), entonces **cada uno de los 216 mutantes se marca "KILLED"
por el mismo motivo: el comando de test crashea siempre, para todos los
mutantes, incluidos los de `auth.py` y `api.py` que ningun test toca.**
Eso explica el 100% sin necesidad de que ningun test real haya verificado
esos archivos.

### Detalle adicional: como test_amounts.py logra importar `payments_svc`

Ejecutar pytest apuntando directo al archivo real falla:

```
$ python -m pytest tests/test_amounts.py
ModuleNotFoundError: No module named 'payments_svc'
```

Pero corrido sin argumentos (escaneo completo del repo) a veces "funciona"
porque, alfabeticamente, `scripts/smoke_test.py` se colecciona antes que
`tests/test_amounts.py`; `smoke_test.py` hace
`sys.path.insert(0, str(SRC))` a nivel de modulo, y ese efecto lateral dejaba
`payments_svc` importable para el resto del proceso de pytest. Es un
accidente de orden de import, no una configuracion real (no hay
`pip install -e .`, ni `conftest.py`, ni `pythonpath` en `pyproject.toml`
para este entorno) — y de cualquier forma, con `tests_results.txt` presente
en la raiz, ni siquiera llega a ese punto porque la coleccion se
interrumpe antes.

---

## 4. Conclusion

- Los **29 tests reales** de `test_amounts.py` si pasan, verificados de
  forma aislada con `unittest` (no con el `pytest` roto de esta carpeta).
- El **canario** (`CanaryDeliberateFailureTests`) falla como se espera,
  confirmando que el runner de `unittest` reporta fallos correctamente.
- El **0% de mutantes sobrevivientes en `tests_results.txt` no es
  confiable**: no hay evidencia de que los 216 mutantes hayan sido
  ejecutados contra tests reales. La causa mas probable, confirmada
  reproduciendo el comando en este entorno, es que el comando de test
  crashea por colision con el propio archivo de resultados (`UnicodeDecodeError`,
  exit code 2), y ese crash se cuenta como "killed" para todo.
- No existe tabla de "mutantes sobrevivientes" que mostrar porque el
  archivo no registra ninguno — el problema no es que falten
  sobrevivientes, es que el numero de "matados" no se puede tomar como
  cierto.

### Para obtener un resultado de mutation testing confiable (no aplicado, solo sugerido)

1. Sacar `tests_results.txt` de la raiz del repo antes de correr pytest/mutmut
   (o excluirlo via `--ignore`), para que la coleccion no se interrumpa.
2. Instalar el paquete en modo editable (`pip install -e .`) o fijar
   `pythonpath = ["src"]` en `[tool.pytest.ini_options]`, para no depender
   del efecto lateral accidental de `scripts/smoke_test.py`.
3. Re-correr mutmut solo sobre `amounts.py` primero (el unico archivo con
   tests reales) y confirmar que el numero de sobrevivientes ya no es 0
   automatico en los otros tres archivos sin cobertura.
