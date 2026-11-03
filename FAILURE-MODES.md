# Modos de falla de amounts.py

Revisión de `src/payments_svc/amounts.py`. No se escribieron ni ejecutaron tests.

Los resultados son deducidos por lectura, no comprobados mediante ejecución. Interpreto «Entrada que lo desestima» como un caso que permite cuestionar la garantía señalada. Sin una especificación independiente, las reglas comerciales quedan pendientes.

## Frontera

- ID: F-01
- Categoria: Frontera — rango permitido.
- Riesgo: Aceptar o rechazar importes con límites comerciales incorrectos.
- Entrada que lo desestima: `Decimal("-0.01")`, `Decimal("0")`, `Decimal("100000")`, `Decimal("100000.01")`.
- Comportamiento actual observado en el código: `validate_amount` admite entre cero y cien mil, ambos incluidos, para cualquier moneda.
- Contrato esperado recomendado: Confirmar extremos inclusivos y límites por moneda.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Un mismo límite numérico representa valores económicos distintos según la moneda.

---

- ID: F-02
- Categoria: Frontera — máximo del total.
- Riesgo: El débito final supera el máximo validado.
- Entrada que lo desestima: `total_with_fee(Decimal("100000"), "USD")`.
- Comportamiento actual observado en el código: El total resulta `102900.00`; el máximo solo se aplica al principal.
- Contrato esperado recomendado: Definir si el límite corresponde al principal, al total o a ambos.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: El cargo podría superar el límite autorizado para la operación.

---

- ID: F-03
- Categoria: Frontera — cero y mínimo positivo.
- Riesgo: Una variación pequeña del importe genera un salto considerable en comisión.
- Entrada que lo desestima: Comparar `calculate_fee(Decimal("0"), "COP")` con `calculate_fee(Decimal("0.01"), "COP")`.
- Comportamiento actual observado en el código: Devuelve `0.00` y `900.00`, respectivamente.
- Contrato esperado recomendado: Decidir si se aceptan operaciones de cero, si existe importe mínimo y si la comisión puede superar el principal.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Un pago pequeño podría generar un cargo desproporcionado.

## Equivalencia

- ID: E-01
- Categoria: Equivalencia — formatos numéricos.
- Riesgo: Admitir representaciones no previstas por el canal.
- Entrada que lo desestima: `"1e2"`, `"1_000"`, `"1,23"` en `parse_amount`.
- Comportamiento actual observado en el código: `Decimal` admite las dos primeras; la coma decimal produce `AmountError`.
- Contrato esperado recomendado: Definir formatos admitidos, incluida notación científica, separadores y formatos locales.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Evita diferencias de interpretación entre formularios e integraciones.

---

- ID: E-02
- Categoria: Equivalencia — `float` y decimal exacto.
- Riesgo: Importes conceptualmente iguales llegan con distinta precisión.
- Entrada que lo desestima: `parse_amount(0.1 + 0.2)` frente a `parse_amount("0.30")`.
- Comportamiento actual observado en el código: Produce `Decimal("0.30000000000000004")` y `Decimal("0.30")`; no normaliza la escala.
- Contrato esperado recomendado: Decidir si se admiten `float` y cómo se trata su precisión.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Los residuos pueden afectar comparaciones, límites y redondeos.

---

- ID: E-03
- Categoria: Equivalencia — no finitos según el punto de entrada.
- Riesgo: La protección depende de pasar primero por `parse_amount`.
- Entrada que lo desestima: `validate_amount(Decimal("NaN"))` y `round_money(Decimal("NaN"))`.
- Comportamiento actual observado en el código: El parser rechaza no finitos. Con el contexto decimal habitual, la validación directa lanza `InvalidOperation`; el redondeo devuelve `NaN`.
- Contrato esperado recomendado: Documentar la precondición de valores finitos o aplicar un rechazo uniforme con `AmountError`.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Otros consumidores del módulo podrían obtener errores no controlados o valores monetarios inválidos.

## Null / vacío

- ID: N-01
- Categoria: Null/vacío — importe ausente.
- Riesgo: Manejo inconsistente de ausencia entre funciones públicas.
- Entrada que lo desestima: `parse_amount(None)`, `parse_amount("")`, `validate_amount(None)`.
- Comportamiento actual observado en el código: El parser lanza `AmountError`; la validación directa de `None` produce `TypeError`. Esta última entrada está fuera de su anotación `Decimal`.
- Contrato esperado recomendado: Rechazar ausencia sin convertirla en cero y definir si la validación de tipos pertenece al parser o a cada función pública.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Determina si entradas inválidas reciben errores controlados y consistentes.

---

- ID: N-02
- Categoria: Null/vacío — moneda ausente.
- Riesgo: Que rutas alternativas omitan la validación de moneda.
- Entrada que lo desestima: `calculate_fee(Decimal("0"), None)` y `normalize_currency("   ")`.
- Comportamiento actual observado en el código: Lanza `CurrencyError`, incluso para importe cero; no aplica moneda predeterminada.
- Contrato esperado recomendado: Exigir moneda explícita para calcular cargos y confirmar si también se exige en operaciones de cero.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Sin moneda no puede interpretarse el importe ni seleccionarse la tarifa.

## Contrato de negocio

- ID: C-01
- Categoria: Contrato de negocio — precisión y reconciliación.
- Riesgo: El principal informado más la comisión no coincide exactamente con el total.
- Entrada que lo desestima: Principal `Decimal("1.005")`, moneda `"USD"`.
- Comportamiento actual observado en el código: Conserva el principal con tres decimales, calcula comisión `0.30` y total `1.30`. Redondea a centavos con `ROUND_HALF_EVEN`.
- Contrato esperado recomendado: Definir precisión por moneda, tratamiento de fracciones adicionales y orden del redondeo para reconciliar principal, comisión y total.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Afecta recibos, conciliación y reembolsos.

---

- ID: C-02
- Categoria: Contrato de negocio — tabla y fórmula de comisiones.
- Riesgo: Cobrar tarifas que no cuenten con aprobación comercial.
- Entrada que lo desestima: `calculate_fee(Decimal("100"), "USD")`, y sus equivalentes con `"EUR"` y `"COP"`.
- Comportamiento actual observado en el código: Devuelve `2.90`, `2.50` y `900.00`. Elige el mayor entre porcentaje y mínimo, y después redondea.
- Contrato esperado recomendado: Confirmar monedas habilitadas, tasas, mínimos y fórmula. Las constantes actuales no prueban su corrección comercial.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Una regla incorrecta provoca sobrecobros o pérdida de ingresos sistemática.

---

- ID: C-03
- Categoria: Contrato de negocio — contexto decimal.
- Riesgo: El resultado depende de configuración numérica externa al módulo.
- Entrada que lo desestima: `total_with_fee(Decimal("100000"), "USD")` con precisión decimal configurada en `6`.
- Comportamiento actual observado en el código: Multiplicaciones y sumas usan el contexto activo; `quantize` puede lanzar `InvalidOperation` al requerir más dígitos. El módulo no fija contexto ni traduce esa excepción.
- Contrato esperado recomendado: Establecer la precisión requerida y si el módulo debe garantizarla internamente.
- Estado del contrato: pendiente de decisión.
- Por que importa para pagos: Cambios de contexto en otro componente pueden interrumpir cálculos que antes funcionaban.
