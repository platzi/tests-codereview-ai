Este archivo describe los fallos que puedan haber en el código.

##Categoria generación de tests
- [n1] Para amount == 0 en calculate_fee/total_fee la IA documento el comportamiento del código sin el fee como si fuera el contrato y contexto de negocio, sin estimar que se debe aplicar como mínimo en cualquier monto.

## Catálogo de fallas — `amounts.py`

Análisis exhaustivo de `src/payments_svc/amounts.py` (y su consumo en `api.py`), agrupado por frontera, equivalencia, null/vacío y contrato de negocio. Sirve como base para decidir contrato antes de generar o corregir tests.

Convención de **Estado del contrato**:
- `INDEFINIDO` — nada en código ni docs fija la regla.
- `IMPLÍCITO` — el código define un comportamiento, pero por accidente (no hay intención documentada); es el caso peligroso para la IA, que lo confunde con contrato.
- `DEFINIDO-INCORRECTO` — la regla existe y contradice el negocio.
- `DEFINIDO-OK` — correcto, pero frágil ante regresión.

### 1. Frontera (boundary)

**FR-01 · Límite superior inclusivo no documentado**
- Categoría: frontera | Riesgo: Medio
- Entrada: `amount = 100000.00` vs `100000.01`
- Observado: `validate_amount` usa `amount > MAX_AMOUNT`, así que 100000.00 pasa y 100000.01 falla. Ningún comentario, docstring ni test fija si el máximo es inclusivo.
- Contrato esperado: declarar explícitamente `MAX_AMOUNT` como máximo inclusivo por transacción y por moneda.
- Estado: `IMPLÍCITO`

**FR-02 · El total puede superar `MAX_AMOUNT`**
- Categoría: frontera | Riesgo: Alto
- Entrada: `total_with_fee(Decimal("100000.00"), "USD")`
- Observado: valida sólo `amount`; devuelve `102900.00`, o sea el importe realmente cobrado excede el tope del sistema sin error.
- Contrato esperado: el tope debe evaluarse sobre el monto liquidado (`amount + fee`), o documentar que `MAX_AMOUNT` es tope de principal y que existe un tope distinto de captura.
- Estado: `INDEFINIDO`

**FR-03 · Frontera inferior: cero es válido pero discontinuo**
- Categoría: frontera | Riesgo: Alto
- Entrada: `amount = 0` frente a `amount = 0.01`
- Observado: `0` → fee `0.00`; `0.01` → fee `0.30` (mínimo). Salto de 30x en la frontera y un pago de importe cero se acepta como transacción válida.
- Contrato esperado: definir un `MIN_AMOUNT` por moneda (> 0) y rechazar `0`, o bien aplicar el mínimo también a `0`. Ver CN-01.
- Estado: `DEFINIDO-INCORRECTO`

**FR-04 · Frontera del mínimo vs porcentaje sin redondear**
- Categoría: frontera | Riesgo: Medio
- Entrada: USD `10.34` (`0.29986` → mínimo `0.30`) vs `10.35` (`0.30015` → `0.30`)
- Observado: `max()` se aplica antes de `round_money`, así que el punto de cruce real entre "mínimo" y "porcentaje" no coincide con el que ve el usuario (ambos muestran `0.30`). El orden `max`-luego-`redondeo` nunca se justificó.
- Contrato esperado: fijar y documentar el orden (redondear el porcentaje antes de comparar contra el mínimo es lo habitual, para que el cruce sea observable).
- Estado: `IMPLÍCITO`

**FR-05 · `round_money` revienta con exponentes grandes**
- Categoría: frontera | Riesgo: Medio
- Entrada: `round_money(Decimal("1E+30"))` (función pública, sin validación previa)
- Observado: `quantize` lanza `InvalidOperation` cruda, no `AmountError`. En la API eso sería un 500, no un 400.
- Contrato esperado: `round_money` debe ser privada o traducir `InvalidOperation` a `AmountError`.
- Estado: `INDEFINIDO`

**FR-06 · Escala de entrada sin límite (más de 2 decimales)**
- Categoría: frontera | Riesgo: Alto
- Entrada: `amount = "10.005"`, moneda USD
- Observado: `parse_amount` acepta cualquier escala. La API responde `amount="10.005"`, `fee="0.30"`, `total="10.30"` → `amount + fee ≠ total` (10.305 vs 10.30). El céntimo desaparece silenciosamente.
- Contrato esperado: rechazar entradas con más decimales que el exponente menor de la moneda, o normalizar `amount` y devolver el valor normalizado en la respuesta.
- Estado: `INDEFINIDO`

**FR-07 · Precisión del contexto Decimal por defecto (28 dígitos)**
- Categoría: frontera | Riesgo: Bajo
- Entrada: montos altos con muchos decimales, p. ej. `"99999.999999999999999999999999"`
- Observado: la multiplicación `amount * FEE_RATES[c]` usa el contexto global de `decimal`, que un tercero puede mutar (`getcontext().prec = 5`) y alterar todos los cálculos del servicio.
- Contrato esperado: usar un `localcontext()` propio con precisión y traps fijados por el módulo.
- Estado: `INDEFINIDO`

### 2. Equivalencia (clases de entrada)

**EQ-01 · `NaN` cruza `parse_amount`… y rompe con la excepción equivocada**
- Categoría: equivalencia | Riesgo: Alto
- Entrada: `calculate_fee(Decimal("NaN"), "USD")` (llamada directa, sin pasar por `parse_amount`)
- Observado: en `validate_amount`, los operadores `<` y `>` sobre `Decimal("NaN")` lanzan `InvalidOperation`, que no deriva de `AmountError`/`CurrencyError`. La API no la captura → 500. `parse_amount` sí lo filtra, pero las funciones públicas de cálculo no.
- Contrato esperado: `validate_amount` debe ser el guardián único y comprobar `is_finite()` antes de comparar, elevando `AmountError`.
- Estado: `DEFINIDO-INCORRECTO`

**EQ-02 · `float` aceptado como tipo de dinero**
- Categoría: equivalencia | Riesgo: Alto
- Entrada: `parse_amount(0.1 + 0.2)` → `"0.30000000000000004"`
- Observado: la firma acepta `float` y lo convierte vía `str()`. Se admite dinero en binario, con error de representación, y sin validación de escala (ver FR-06).
- Contrato esperado: aceptar sólo `str | int | Decimal`; rechazar `float` con `AmountError` explícito.
- Estado: `DEFINIDO-INCORRECTO`

**EQ-03 · Formatos numéricos exóticos admitidos**
- Categoría: equivalencia | Riesgo: Medio
- Entrada: `"1_000"`, `"1e3"`, `"+10"`, `"١٢٣"` (dígitos árabo-índicos)
- Observado: `Decimal(str)` acepta guiones bajos de agrupación, notación exponencial, signo positivo explícito y dígitos Unicode. `"1e3"` además se ecoa como `"1E+3"` en la respuesta de la API.
- Contrato esperado: validar el formato con una expresión canónica (`^-?\d+(\.\d{1,N})?$`) antes de construir el `Decimal`.
- Estado: `IMPLÍCITO`

**EQ-04 · `bool` como monto**
- Categoría: equivalencia | Riesgo: Bajo
- Entrada: `parse_amount(True)`
- Observado: `str(True)` → `"True"` → `InvalidOperation` → `AmountError`. Funciona por accidente; si alguien "optimiza" a `Decimal(raw)`, `True` pasaría a valer `1`.
- Contrato esperado: rechazo explícito de `bool` (`isinstance(raw, bool)`) antes de cualquier conversión.
- Estado: `IMPLÍCITO`

**EQ-05 · Moneda no-string produce `AttributeError`**
- Categoría: equivalencia | Riesgo: Medio
- Entrada: `normalize_currency(840)` o `normalize_currency(["USD"])`
- Observado: el guard sólo cubre `None`; cualquier otro no-str explota en `.strip()` con `AttributeError` no capturado → 500 en vez de 400.
- Contrato esperado: comprobar `isinstance(currency, str)` y elevar `CurrencyError`.
- Estado: `DEFINIDO-INCORRECTO`

**EQ-06 · Cero negativo**
- Categoría: equivalencia | Riesgo: Bajo
- Entrada: `"-0.00"`
- Observado: `-0.00 < 0` es falso → pasa validación; fee `0.00`; la API devuelve `amount="-0.00"`.
- Contrato esperado: normalizar el cero con signo, o rechazarlo junto con FR-03.
- Estado: `INDEFINIDO`

**EQ-07 · `except (AttributeError, InvalidOperation)` con rama muerta**
- Categoría: equivalencia | Riesgo: Bajo
- Entrada: ninguna alcanzable
- Observado: `str(raw).strip()` no puede lanzar `AttributeError` (`str()` siempre devuelve `str`). La rama sugiere una intención (aceptar objetos sin `.strip`) que ya no existe. En cambio, `TypeError` desde un `__str__` de usuario no se captura.
- Contrato esperado: eliminar `AttributeError` y capturar `(InvalidOperation, TypeError, ValueError)`.
- Estado: `IMPLÍCITO`

**EQ-08 · Clase de equivalencia "moneda soportada" con dos fuentes de verdad**
- Categoría: equivalencia | Riesgo: Medio
- Entrada: añadir `"GBP"` a `FEE_RATES` y olvidarlo en `MINIMUM_FEES`
- Observado: `normalize_currency` valida sólo contra `FEE_RATES`; `calculate_fee` haría `KeyError` en `MINIMUM_FEES[currency]` → 500. Nada acopla ambos diccionarios.
- Contrato esperado: una sola tabla de configuración por moneda (`rate`, `min_fee`, `exponent`, `max_amount`) y validación contra ella.
- Estado: `DEFINIDO-INCORRECTO`

### 3. Null / vacío

**NV-01 · `None` en monto: guard redundante y contradictorio con la firma**
- Categoría: null/vacío | Riesgo: Bajo
- Entrada: `parse_amount(None)`
- Observado: hay un `if raw is None` explícito, pero `None` no está en el tipo declarado (`str | int | float | Decimal`). Sin el guard el resultado sería el mismo `AmountError` por otra vía. Es contrato-por-implementación.
- Contrato esperado: decidir si `None` es entrada legítima (entonces tiparlo `| None`) o no (entonces es un error de programación, no de dominio).
- Estado: `IMPLÍCITO`

**NV-02 · Cadena vacía y sólo-espacios en monto**
- Categoría: null/vacío | Riesgo: Medio
- Entrada: `""`, `"   "`, `"\t\n"`
- Observado: `Decimal("")` → `InvalidOperation` → `AmountError("amount must be numeric")`. El mensaje miente sobre la causa (falta el dato, no es "no numérico").
- Contrato esperado: distinguir "amount is required" de "amount must be numeric" para que el cliente pueda reaccionar distinto.
- Estado: `IMPLÍCITO`

**NV-03 · Moneda vacía vs moneda ausente: mismo mensaje, distinto caso**
- Categoría: null/vacío | Riesgo: Bajo
- Entrada: `None`, `""`, `"   "`
- Observado: los tres → `CurrencyError("currency is required")`. Correcto por unificación, pero indistinguible de un fallo de serialización aguas arriba.
- Contrato esperado: aceptable; documentarlo como decisión deliberada para que la IA no lo reescriba.
- Estado: `DEFINIDO-OK`

**NV-04 · `already_refunded` por defecto `"0.00"` en la API sin pasar por `parse_amount`**
- Categoría: null/vacío | Riesgo: Medio
- Entrada: `POST /refunds` con `original_amount: "abc"`
- Observado: `api.py:71-73` llama `Decimal(...)` directo, saltándose `parse_amount`; una cadena vacía o no numérica lanza `InvalidOperation` no capturada → 500. El módulo `amounts` ofrece el parser y nadie lo usa en esa ruta.
- Contrato esperado: toda entrada monetaria de la API debe pasar por `parse_amount` + `validate_amount`.
- Estado: `DEFINIDO-INCORRECTO`

**NV-05 · Diccionarios `Final` mutables**
- Categoría: null/vacío (integridad de configuración) | Riesgo: Bajo
- Entrada: `FEE_RATES["USD"] = Decimal("0")` desde cualquier módulo
- Observado: `Final` sólo lo comprueba el type-checker; en runtime son `dict` mutables y globales. Una tarifa puede quedar vacía o a cero sin que nada lo detecte.
- Contrato esperado: `MappingProxyType` y validación de arranque (todas las monedas con rate > 0 y min_fee ≥ 0).
- Estado: `INDEFINIDO`

### 4. Contrato de negocio

**CN-01 · Monto cero elude la comisión mínima** ← el fallo `[n1]` original
- Categoría: contrato de negocio | Riesgo: Alto
- Entrada: `calculate_fee(Decimal("0"), "USD")`
- Observado: `if amount == Decimal("0"): return Decimal("0.00")` es un atajo antes de aplicar `MINIMUM_FEES`. El código define que un pago de cero no cuesta nada; la IA que genera tests documenta ese atajo como si fuera el contrato de negocio.
- Contrato esperado: o el monto cero no es una transacción válida (rechazo en `validate_amount`), o si se acepta, la comisión mínima aplica a todo monto. La regla "mínimo por transacción" no admite excepción silenciosa.
- Estado: `DEFINIDO-INCORRECTO`

**CN-02 · La comisión puede superar el principal**
- Categoría: contrato de negocio | Riesgo: Alto
- Entrada: `total_with_fee(Decimal("0.01"), "USD")` → fee `0.30`, total `0.31`
- Observado: la comisión es 30x el importe y nada lo señala. Es matemáticamente coherente con el mínimo, pero es exactamente el escenario que suele estar prohibido por regulación/PSP.
- Contrato esperado: definir un `MIN_AMOUNT` por moneda tal que `min_fee / min_amount` quede bajo un techo aceptable, o rechazar cuando `fee > amount`.
- Estado: `INDEFINIDO`

**CN-03 · `MAX_AMOUNT` único para todas las monedas**
- Categoría: contrato de negocio | Riesgo: Alto
- Entrada: `total_with_fee(Decimal("100000"), "COP")`
- Observado: 100 000 COP son ~25 USD, y la comisión mínima COP (900) equivale a ~0.22 USD. El tope global convierte el límite en absurdamente restrictivo para COP y laxo para USD/EUR. Además la comisión mínima COP se activa por debajo de ~47 368 COP, un umbral que nadie declaró.
- Contrato esperado: `max_amount` (y `min_amount`) por moneda, en la misma tabla de EQ-08.
- Estado: `DEFINIDO-INCORRECTO`

**CN-04 · COP se cuantiza a 2 decimales (moneda sin unidad menor)**
- Categoría: contrato de negocio | Riesgo: Alto
- Entrada: `calculate_fee(Decimal("50000"), "COP")` → `950.00`
- Observado: `round_money` usa `CENT = 0.01` para toda moneda. COP tiene exponente 0; producir `950.00` genera importes no liquidables y descuadres al integrar con el adquirente.
- Contrato esperado: exponente por moneda (ISO 4217) y cuantización con ese exponente.
- Estado: `DEFINIDO-INCORRECTO`

**CN-05 · Política de redondeo (`ROUND_HALF_EVEN`) sin justificación**
- Categoría: contrato de negocio | Riesgo: Medio
- Entrada: fee de `0.305` → `0.30`; fee de `0.315` → `0.32`
- Observado: redondeo bancario, que en comisiones al consumidor suele sustituirse por `ROUND_HALF_UP` (o `ROUND_CEILING` a favor del PSP). Elegido sin nota; la mitad de los casos redondea a la baja.
- Contrato esperado: fijar la política de redondeo de comisiones como constante documentada y separarla de la de importes.
- Estado: `IMPLÍCITO`

**CN-06 · Precedencia de errores incoherente entre las dos puertas de entrada**
- Categoría: contrato de negocio | Riesgo: Medio
- Entrada: `amount = -5`, `currency = "XXX"`
- Observado: `calculate_fee` normaliza la moneda primero → `CurrencyError("unsupported currency: XXX")`. `total_with_fee` valida el monto primero → `AmountError("amount cannot be negative")`. Misma entrada inválida, dos mensajes distintos según la función; y la API llama a ambas en secuencia (`api.py:54-55`).
- Contrato esperado: un único orden de validación documentado (o acumular todos los errores y devolverlos juntos).
- Estado: `DEFINIDO-INCORRECTO`

**CN-07 · Validación duplicada y no idempotente por diseño**
- Categoría: contrato de negocio | Riesgo: Bajo
- Entrada: cualquier llamada a `total_with_fee`
- Observado: valida el monto, luego `calculate_fee` lo revalida y renormaliza la moneda. Hoy es inocuo, pero fija dos puntos donde la regla puede divergir en futuras ediciones (y donde una IA puede "limpiar" el equivocado).
- Contrato esperado: una capa de validación en el borde y funciones de cálculo que asuman entrada ya validada (o viceversa), no las dos cosas a medias.
- Estado: `IMPLÍCITO`

**CN-08 · La respuesta de pago no devuelve el importe normalizado**
- Categoría: contrato de negocio | Riesgo: Alto
- Entrada: `{"amount": "1e3", "currency": "usd"}`
- Observado: la API ecoa `str(amount)` → `"1E+3"`, con `fee="29.00"` y `total="1029.00"`. El cliente recibe un importe en un formato que él no envió y que no puede sumar con el resto.
- Contrato esperado: `amounts` debe exponer el importe canónico cuantizado y la API devolver ese, no el eco del parseo. Invariante publicable: `amount + fee == total`, siempre.
- Estado: `INDEFINIDO`

**CN-09 · Eco de la entrada en el mensaje de error de moneda**
- Categoría: contrato de negocio | Riesgo: Bajo
- Entrada: `currency = "<script>…"` o una cadena de 1 MB
- Observado: `f"unsupported currency: {normalized}"` viaja al `detail` del HTTP 400 y a los logs sin límite de longitud ni saneado.
- Contrato esperado: truncar y sanear el valor reflejado, o no reflejarlo.
- Estado: `INDEFINIDO`

### Resumen por estado

| Estado | Nodos |
|---|---|
| `DEFINIDO-INCORRECTO` (10) | FR-03, EQ-01, EQ-02, EQ-05, EQ-08, NV-04, CN-01, CN-03, CN-04, CN-06 |
| `IMPLÍCITO` — trampa para tests generados por IA (9) | FR-01, FR-04, EQ-03, EQ-04, EQ-07, NV-01, NV-02, CN-05, CN-07 |
| `INDEFINIDO` (9) | FR-02, FR-05, FR-06, FR-07, EQ-06, NV-05, CN-02, CN-08, CN-09 |
| `DEFINIDO-OK` (1) | NV-03 |

### Prioridad de resolución de contrato

Antes de generar o corregir cualquier test, fijar contrato en este orden:

1. **CN-01** — el atajo de monto cero (el `[n1]` original).
2. **CN-03 / CN-04 / EQ-08** — tabla de configuración por moneda (rate, min_fee, max_amount, exponent).
3. **FR-06 / CN-08** — invariante `amount + fee == total` y devolución del importe normalizado.
4. **EQ-01** — `NaN` escapando como `InvalidOperation` en vez de `AmountError`.
5. **EQ-02 / EQ-05** — tipos de entrada aceptados (`float`, moneda no-string) que deberían rechazarse con error de dominio, no con excepción cruda.

Los nodos marcados `IMPLÍCITO` son el riesgo más alto para generación asistida por IA: un modelo que "documenta el comportamiento observado" los congelará como especificación en vez de señalarlos como bug.
