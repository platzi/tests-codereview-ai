# Reviewer — Code Review de `payments-svc`

## Objetivo

Revisa los cambios de la rama actual contra `develop`.

Trata este diff como si fuera un Pull Request hacia `develop`, aunque no exista un PR real en GitHub.

### Reglas de revisión

1. Usa **solo** el diff mostrado y los archivos incluidos en el contexto.
2. No inventes información de GitHub, CI, historial remoto, ramas remotas ni commits que no estén disponibles.
3. No reescribas el código.
4. No propongas refactors grandes ni cambios fuera del alcance del diff.
5. Reporta únicamente hallazgos **accionables** y directamente relacionados con el cambio.
6. No inventes archivos, líneas, contratos ni comportamiento que no pueda comprobarse con el material disponible.
7. Si un hallazgo depende de una decisión de contrato, consulta `FAILURES_MODE.md` cuando esté disponible.
8. Si no hay hallazgos claros en una categoría, escribe exactamente: `sin hallazgos`.
9. Da prioridad a bugs reales y regresiones sobre observaciones de estilo.
10. Para dinero, considera `Decimal` como el tipo correcto salvo que el contrato indique explícitamente otra cosa.

---

## Rubrica

Evalúa cada cambio en estas categorías:

1. **Corrección** — el código cumple el contrato del dominio de pagos.
2. **Seguridad** — autorización, autenticación, exposición de datos o entradas inseguras.
3. **Rendimiento** — complejidad innecesaria o trabajo costoso en rutas calientes.
4. **Tests faltantes** — cambios sin pruebas relevantes o sin casos de borde.
5. **Estilo** — legibilidad, nombres y mantenibilidad. Severidad baja.
6. **Documentación** — cambios públicos sin documentación suficiente.

### Severidad sugerida

- **P0 — crítico:** pérdida/corrupción de dinero, bypass de autorización, exposición grave de datos o fallo que compromete el sistema.
- **P1 — alto:** bug funcional importante, inconsistencia de pagos/reembolsos o regresión con impacto significativo.
- **P2 — medio:** bug acotado, validación incorrecta, caso de borde relevante o cobertura que deja una regresión probable.
- **P3 — bajo:** mejora de mantenibilidad, documentación o estilo cuando sea accionable.

No eleves un hallazgo de severidad solo porque exista un mutante superviviente. El mutante debe representar una diferencia de comportamiento relevante según el contrato.

---

## Instrucción de salida

Para cada categoría:

- indica si hay hallazgos;
- si los hay, cita **archivo y línea**;
- explica por qué importa;
- sugiere una **corrección breve**;
- asigna severidad cuando corresponda.

Formato recomendado:

```text
## Corrección
- P1 — `src/payments_svc/example.py:42`
  - Hallazgo: ...
  - Por qué importa: ...
  - Corrección sugerida: ...

## Seguridad
sin hallazgos

## Rendimiento
sin hallazgos

## Tests faltantes
- P2 — `tests/test_example.py:...`
  - Hallazgo: ...
  - Por qué importa: ...
  - Corrección sugerida: ...

## Estilo
sin hallazgos

## Documentación
sin hallazgos
```

Al final incluye:

```text
## Resumen
- P0: 0
- P1: 0
- P2: 0
- P3: 0
- Veredicto: ...
```

El veredicto debe ser breve y basarse únicamente en los hallazgos encontrados.

---

# Contexto del proyecto

```text
tests-codereview-ai/
├── src/
│   └── payments_svc/
│       ├── __init__.py
│       ├── amounts.py       # Lógica de montos, fees, validaciones
│       ├── api.py           # API endpoints (FastAPI)
│       ├── auth.py          # Autenticación y autorización
│       └── refunds.py       # Lógica de reembolsos
├── tests/
│   ├── test_amounts.py      # Tests existentes para amounts
│   └── test_auth.py         # Tests existentes para auth
├── FAILURES_MODE.md         # Catálogo de fallos conocidos y decisiones de contrato
└── pyproject.toml           # Configuración del proyecto
```

---

# Resultados actuales de Mutation Testing

Los siguientes mutantes supervivientes representan gaps potenciales de pruebas. **No asumas automáticamente que todos requieren un test**: primero verifica el código y el contrato en `FAILURES_MODE.md`.

## `amounts.py`

| Línea | Mutación | Descripción | Acción requerida |
|---:|---|---|---|
| 59 | `BitOr → BitXor/BitAnd` | Anotación de tipo `str \| int \| Decimal` | **Mutante equivalente** — no es código ejecutable |
| 60 | `If_Statement → If_False` | `if raw is None:` | Agregar test con `None` en `parse_amount()` si el contrato lo confirma |
| 60 | `None → True/False` | Valor de condición en `if raw is None:` | Agregar test con `None` en `parse_amount()` si el contrato lo confirma |
| 73 | `If_Statement → If_False` | `if isinstance(raw, float):` | Agregar test con `float` en `parse_amount()` |
| 98 | `None → False` | Validación de moneda | Agregar test con moneda inválida |
| 105 | `If_Statement → If_False` | `if amount < Decimal("0"):` | Agregar test con monto negativo |
| 105 | `Lt → Eq` | `amount < Decimal("0")` vs `amount == Decimal("0")` | Agregar test con `0.00` |
| 108 | `LtE → Eq` | `amount <= MIN_AMOUNT` vs `amount == MIN_AMOUNT` | **Posible mutante equivalente** — el guard previo ya filtra negativos; verificar contrato |
| 112 | `None → False` | Validación en `validate_amount` | Agregar test con moneda `None` si el contrato lo confirma |
| 117 | `If_Statement → If_False` | Validación de monto | Agregar test con monto inválido |
| 117 | `Gt → Eq` | `amount > MAX_AMOUNT` vs `amount == MAX_AMOUNT` | Agregar test en frontera del máximo |
| 121 | `None → True/False` | Validación de moneda | Agregar test con moneda `None` |
| 127 | `Gt → GtE` | `amount > max_amount` vs `amount >= max_amount` | Agregar test con monto exactamente igual al máximo |
| 131 | `None → True` | Validación | Agregar test con valor `None` |
| 167 | `Mult → Add/Mod/Sub/FloorDiv/Pow/Div` | Multiplicación en cálculo de fee | Agregar tests que validen el cálculo exacto |
| 177 | `Add → Sub/Mult/Div/Pow/FloorDiv/Mod` | Suma en `total_with_fee` | Agregar tests que validen la suma exacta |

## `auth.py`

| Línea | Mutación | Descripción | Acción requerida |
|---:|---|---|---|
| 13 | `True → False` | Valor booleano en configuración | Agregar test que valide la configuración |
| 20 | `BitOr → BitXor` | Anotación de tipo | **Mutante equivalente** |
| 20 | `None → False` | Validación de usuario | Agregar test con usuario `None` |
| 21 | `If_Statement → If_True/If_False` | `if user is None:` | Agregar test con usuario `None` |
| 21 | `Is → IsNot` | `user is None` vs `user is not None` | Agregar test con usuario `None` |
| 21 | `None → True/False` | Validación de usuario | Agregar test con usuario `None` |

## `api.py`

| Línea | Mutación | Descripción | Acción requerida |
|---:|---|---|---|
| 42 | `BitOr → BitXor` | Anotación de tipo | **Mutante equivalente** |
| 42 | `None → True/False` | Validación de parámetro | Agregar test con parámetro `None` |
| 78 | `Is → IsNot` | Validación de objeto | Agregar test de validación |
| 79 | `If_Statement → If_False` | Validación de condición | Agregar test que ejercite esta rama |
| 79 | `GtE → NotEq` | Comparación de monto | Agregar test en la frontera |

## `refunds.py`

| Línea | Mutación | Descripción | Acción requerida |
|---:|---|---|---|
| 20 | `True → None` | Valor booleano | Agregar test de configuración |
| 24 | `BitOr → BitAnd` | Anotación de tipo | **Mutante equivalente** |
| 24 | `None → True` | Validación de parámetro | Agregar test con parámetro `None` |
| 33 | `Sub → Pow` | Operación de resta en cálculo | Agregar test que valide el cálculo exacto |
| 47 | `If_Statement → If_False` | Validación de condición | Agregar test que ejercite esta rama |
| 47 | `Eq → LtE` | Comparación de estado | Agregar test de validación de estado |
| 54 | `If_Statement → If_False` | Validación de monto | Agregar test de monto |
| 54 | `LtE → NotEq` | Comparación de monto | Agregar test en la frontera |
| 64 | `None → True` | Validación | Agregar test con valor `None` |
| 68 | `None → False` | Validación | Agregar test con valor `None` |
| 70 | `If_Statement → If_True` | Validación de condición | Agregar test que ejercite esta rama |
| 70 | `Is → IsNot` | Comparación de identidad | Agregar test de comparación |
| 71 | `Or → And` | Operador lógico | Agregar test que valide la lógica |

---

# Patrones de testing

## Estructura recomendada

Los tests deben seguir el estilo existente del repositorio. Usa `tests/test_amounts.py` como referencia cuando esté disponible.

Ejemplo orientativo:

```python
from decimal import Decimal

import pytest

from payments_svc.amounts import parse_amount


def test_parse_amount_none_rejected():
    """Protege el contrato que rechaza un monto ausente."""
    with pytest.raises(ValueError):
        parse_amount(None)


@pytest.mark.parametrize(
    "raw",
    [Decimal("0.00"), Decimal("10.00")],
)
def test_parse_amount_valid_boundaries(raw):
    """Protege valores válidos y fronteras definidas por el contrato."""
    result = parse_amount(raw)
    assert result == raw
```

**No copies este ejemplo literalmente si el código o el contrato usan otra excepción, interfaz o resultado.** Adapta el test al comportamiento real observado.

---

# Test canario — NO MODIFICAR

Existe un test canario que **siempre debe fallar**.

Ese test se utiliza para comprobar que el runner reporta correctamente los fallos.

**Nunca lo modifiques, elimines, desactives, marques como `xfail` ni cambies sus expectativas.**

Si el test canario aparece en el diff, considéralo un hallazgo relevante.

---

# Decisiones de contrato — `FAILURES_MODE.md`

`FAILURES_MODE.md` contiene el catálogo de fallos conocidos y las decisiones de contrato.

Estados:

- **DEFINIDO-OK** — el código está correcto según el contrato definido.
- **DEFINIDO-INCORRECTO** — el código tenía un bug que ya fue corregido.
- **IMPLÍCITO** — no existe contrato explícito; queda como pregunta abierta.
- **INDEFINIDO** — nadie fijó la regla; requiere decisión humana.

### Regla importante

Solo considera como evidencia suficiente para exigir un test los nodos cuyo contrato esté confirmado:

- `DEFINIDO-OK`, o
- `DEFINIDO-INCORRECTO` cuando el bug ya esté corregido.

Para `IMPLÍCITO` o `INDEFINIDO`, no inventes el comportamiento esperado. Señala la ambigüedad únicamente si el diff la convierte en un riesgo accionable.

---

# Prioridades para crear tests

## Alta prioridad

### 1. `api.py` — falta de tests de integración

Revisar especialmente:

- endpoints;
- parámetros `None`;
- montos en frontera;
- autenticación y autorización;
- respuestas de error;
- interacción entre validación y lógica de negocio.

Si el cambio introduce comportamiento de endpoint sin cobertura, considerar un hallazgo **P2** salvo que exista evidencia de impacto mayor.

### 2. `refunds.py` — lógica de reembolsos

Revisar:

- cálculos exactos de reembolso;
- estados válidos e inválidos;
- montos límite;
- valores `None`;
- condiciones booleanas;
- casos donde el reembolso puede superar o no coincidir con el monto permitido.

Los cálculos monetarios incorrectos pueden elevarse a **P1** cuando puedan producir una cantidad incorrecta.

### 3. `amounts.py` — casos frontera

Priorizar:

- `None` en `parse_amount`;
- `float` en `parse_amount`;
- montos negativos;
- `0.00`;
- `MIN_AMOUNT`;
- `MAX_AMOUNT`;
- moneda inválida o `None`;
- cálculo exacto del fee;
- `total_with_fee`.

## Prioridad media

### 4. `auth.py`

Ya existe cobertura básica. Revisar únicamente edge cases que el diff afecte o que estén directamente relacionados con mutantes supervivientes relevantes:

- usuario `None`;
- configuración booleana;
- autorización;
- comportamiento ante entradas inválidas.

## No prioridad

### 5. Mutantes equivalentes

No reportar como gap de cobertura las mutaciones que solo afectan anotaciones de tipo y no cambian el comportamiento ejecutable, por ejemplo:

```python
str | int | Decimal
```

Si el sistema de mutation testing las marca como `SURVIVED`, trátalas como **mutantes equivalentes**, no como bugs.

---

# Checklist para crear un nuevo test

- [ ] Identificar la línea y mutación superviviente.
- [ ] Leer el código fuente correspondiente.
- [ ] Consultar `FAILURES_MODE.md` cuando aplique.
- [ ] Confirmar que el comportamiento esperado está definido.
- [ ] Crear un test que ejercite la línea específica.
- [ ] Verificar que cambiar el operador/valor mutado hace fallar el test.
- [ ] Verificar que el test pasa con el código correcto.
- [ ] Ejecutar mutation testing para confirmar que el mutante pasa de `SURVIVED` a `DETECTED`.
- [ ] Mantener el test canario intacto.
- [ ] No modificar `src/payments_svc/` para resolver un gap de tests.
- [ ] Evitar tests redundantes que no protejan un comportamiento distinto.

---

# Comandos de verificación

Usa los comandos definidos realmente en `pyproject.toml` y en la configuración del repositorio. Si están disponibles, la secuencia típica es:

```bash
pytest
```

Para un archivo concreto:

```bash
pytest tests/test_amounts.py
pytest tests/test_auth.py
pytest tests/test_api.py
pytest tests/test_refunds.py
```

Para mutation testing, usa el comando configurado por el proyecto. Por ejemplo, si el repositorio utiliza `mutmut`:

```bash
mutmut run
mutmut results
```

No inventes un comando de mutation testing si la herramienta configurada en `pyproject.toml` es diferente.

---

# Restricciones de implementación

1. **No modificar código fuente** en `src/payments_svc/` para solucionar los gaps de cobertura.
2. **Solo agregar o modificar tests** cuando el objetivo sea cubrir un comportamiento confirmado.
3. **Mantener el test canario**, aunque falle.
4. Usar `Decimal` para cantidades monetarias; no usar `float` para representar dinero.
5. Documentar cada clase de test explicando qué contrato protege cuando eso aporte claridad.
6. Seguir el estilo existente del proyecto.
7. Trabajar sobre la rama `developer`; no hacer commits directos a `master`.
8. No introducir dependencias nuevas salvo que el proyecto ya las use o el cambio las requiera explícitamente.
9. No crear tests para contratos `IMPLÍCITO` o `INDEFINIDO` como si fueran reglas confirmadas.
10. No convertir mutantes equivalentes en falsos positivos del code review.

---

# Criterios específicos de revisión del dominio de pagos

Presta especial atención a:

- precisión decimal;
- redondeos;
- límites mínimos y máximos;
- moneda;
- signos de los montos;
- cálculo de fees;
- total final;
- reembolsos parciales y totales;
- estados de transacción;
- autorización antes de operaciones sensibles;
- entradas `None`;
- errores y excepciones;
- idempotencia cuando el contrato la mencione;
- exposición de información sensible;
- diferencias entre validación de entrada y reglas de negocio.

No asumas reglas de negocio que no estén documentadas o demostradas por el código y `FAILURES_MODE.md`.

---

# Formato final del review

Devuelve únicamente hallazgos accionables y el resumen final.

```text
## Corrección
...

## Seguridad
...

## Rendimiento
...

## Tests faltantes
...

## Estilo
...

## Documentación
...

## Resumen
- P0: N
- P1: N
- P2: N
- P3: N
- Veredicto: APROBADO / CAMBIOS SOLICITADOS
```

### Regla de calidad

Un hallazgo válido debe poder responder claramente:

1. **Qué está mal.**
2. **Dónde está.**
3. **Por qué importa.**
4. **Cómo corregirlo de forma breve.**
5. **Qué evidencia del diff o del contrato lo sustenta.**

Si no puede responderse a esas preguntas con el contexto disponible, no inventes el hallazgo.
