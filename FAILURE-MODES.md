# FAILURE-MODES.md - catalogo de fallos en payments-svc

Este archivo registra los modos de falla que aparecen al usar IA para generar pruebas y revisar codigo en `payments-svc`.

En `n1` se ejecuto dos veces el prompt ingenuo `Escribe los tests para amounts.py`: una ejecucion principal y otra ejecucion temporal de validacion. Las suites generadas no fueron identicas, pero repitieron el mismo patron: mucho codigo de test plausible, dependencia en `pytest`, cobertura de helpers internos y aceptacion de la implementacion actual como contrato.

## n1 - Prompt ingenuo

### Categoria: Generacion de tests

- [n1] La IA genera suites que se ven completas, pero aceptan la implementacion actual como contrato. En ambas corridas trato `calculate_fee(Decimal("0.00"), "USD") == Decimal("0.00")` como comportamiento esperado, aunque el contrato de negocio todavia debe discutirse.
- [n1] La IA cubre muchos casos nominales y de error, pero no distingue entre "esto pasa hoy" y "esto debe pasar". Ese salto convierte bugs sembrados en especificacion accidental.
- [n1] La IA introduce dependencias y estilo de test no pedidos. En las dos corridas uso `pytest`, aunque el plan del modulo propone empezar con comandos simples de `unittest`.
- [n1] La IA prueba helpers internos y constantes en ambas corridas, pero no siempre valida los contratos de negocio relevantes para pagos: fee minimo, fronteras exactas, montos maximos combinados con fee y reglas de redondeo desde la perspectiva del producto.
- [n1] La IA no deja una trazabilidad clara entre cada test y un modo de falla. Sin catalogo previo, no sabemos que casos faltan, cuales sobran ni que riesgo cubre cada prueba.

### Categoria: Revision de codigo

- [n1] Una revision ingenua puede quedarse en estilo o cobertura aparente y no retar decisiones de negocio como `amount == 0`, redondeo bancario o reembolsos por encima del monto original.
- [n1] La IA puede dar por seguro que una funcion valida autenticacion o autorizacion solo porque el flujo compila y tiene nombres plausibles.

### Categoria: Dominio de pagos

- [n1] `amount == 0` es una frontera critica: debe decidirse explicitamente si aplica fee minimo, devuelve cero o se rechaza.
- [n1] `refund_amount > original_amount` es una frontera critica: debe rechazarse, aunque la implementacion inicial lo aprueba como sentinel para trabajo futuro.
- [n1] El redondeo decimal debe probarse contra reglas de negocio, no solo contra el metodo de redondeo que hoy usa la implementacion.

## n2 - Catalogo de modos de falla y contratos de `amounts.py`

Este documento detalla el analisis de modos de falla del modulo de montos, clasificados en cuatro categorias: **Null/Vacio**, **Frontera**, **Equivalencia** y **Contrato de Negocio**. Para cada caso se separa el comportamiento actual observado del contrato esperado recomendado.

### 1. Null / Vacío

#### FM-NULL-01: Entrada nula en [parse_amount](src/payments_svc/amounts.py#L31)
- **ID**: FM-NULL-01
- **Categoría**: Null/vacío
- **Riesgo**: Caída del flujo de ejecución en capas superiores por excepciones no controladas si no se captura [AmountError](src/payments_svc/amounts.py#L23).
- **Entrada que lo dispara**: `raw = None`
- **Comportamiento actual observado en el código**: Lanza [AmountError](src/payments_svc/amounts.py#L23) con el mensaje `"amount is required"`.
- **Contrato esperado recomendado**: Lanzar [AmountError](src/payments_svc/amounts.py#L23) indicando la ausencia del parámetro.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: No se puede procesar una transacción sin conocer el monto a cobrar; debe abortarse el proceso de inmediato.

#### FM-NULL-02: String vacío o espacios en blanco en [parse_amount](src/payments_svc/amounts.py#L31)
- **ID**: FM-NULL-02
- **Categoría**: Null/vacío
- **Riesgo**: Mensaje de error confuso que dificulta el diagnóstico en API públicas (trata la ausencia como un error de formato).
- **Entrada que lo dispara**: `raw = ""` o `raw = "   "`
- **Comportamiento actual observado en el código**: Lanza [AmountError](src/payments_svc/amounts.py#L23) con el mensaje `"amount must be numeric"` (debido a que `Decimal("")` lanza `InvalidOperation`, atrapada en la línea 37).
- **Contrato esperado recomendado**: Lanzar [AmountError](src/payments_svc/amounts.py#L23) con el mensaje `"amount is required"` porque una cadena vacia representa ausencia de monto.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Facilita a las capas API retornar el código de error HTTP preciso (como `400 Bad Request` distinguiendo campos vacíos de tipos inválidos) y ayuda en la depuración del cliente de integración.

#### FM-NULL-03: Moneda nula en [normalize_currency](src/payments_svc/amounts.py#L46)
- **ID**: FM-NULL-03
- **Categoría**: Null/vacío
- **Riesgo**: Excepción de tipo `AttributeError` o procesamiento inconsistente si el flujo continúa sin una divisa válida.
- **Entrada que lo dispara**: `currency = None`
- **Comportamiento actual observado en el código**: Lanza [CurrencyError](src/payments_svc/amounts.py#L27) con el mensaje `"currency is required"`.
- **Contrato esperado recomendado**: Lanzar [CurrencyError](src/payments_svc/amounts.py#L27) indicando que la moneda es obligatoria.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: La divisa determina las comisiones y las reglas de cargo de los adquirentes externos. Un pago sin divisa es inválido.

#### FM-NULL-04: Moneda vacía o con espacios en blanco en [normalize_currency](src/payments_svc/amounts.py#L46)
- **ID**: FM-NULL-04
- **Categoría**: Null/vacío
- **Riesgo**: Intentar procesar una transacción con divisa ausente o mal formateada que fallará en etapas posteriores del adquirente.
- **Entrada que lo dispara**: `currency = ""` o `currency = "   "`
- **Comportamiento actual observado en el código**: Lanza [CurrencyError](src/payments_svc/amounts.py#L27) con el mensaje `"currency is required"`.
- **Contrato esperado recomendado**: Mantener el comportamiento actual.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Evita ensuciar la base de datos de auditoría transaccional con strings vacíos o inválidos.

---

### 2. Frontera (Boundary)

#### FM-FRONT-01: Monto negativo en [validate_amount](src/payments_svc/amounts.py#L60)
- **ID**: FM-FRONT-01
- **Categoría**: Frontera
- **Riesgo**: Fuga involuntaria de fondos, transacciones fraudulentas o cobros inversos no deseados.
- **Entrada que lo dispara**: `amount = Decimal("-0.01")` (o cualquier valor `< 0`)
- **Comportamiento actual observado en el código**: Lanza [AmountError](src/payments_svc/amounts.py#L23) con el mensaje `"amount cannot be negative"`.
- **Contrato esperado recomendado**: Mantener la validación estricta y bloquear todo monto negativo.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Los flujos de cobro solo permiten montos positivos. Los movimientos negativos pertenecen a flujos separados de reembolso u operaciones contables controladas.

#### FM-FRONT-02: Límite máximo en [validate_amount](src/payments_svc/amounts.py#L60)
- **ID**: FM-FRONT-02
- **Categoría**: Frontera
- **Riesgo**: Aprobación de cargos por encima del límite regulatorio o de prevención de fraude (AML), o rechazo incorrecto de transacciones legítimas.
- **Entrada que lo dispara**: `amount = Decimal("100000.01")` (cualquier valor que exceda la constante `MAX_AMOUNT`)
- **Comportamiento actual observado en el código**: Lanza [AmountError](src/payments_svc/amounts.py#L23) con el mensaje `"amount exceeds maximum allowed"`.
- **Contrato esperado recomendado**: Para el alcance actual mantener un limite maximo global mediante `MAX_AMOUNT`. La parametrizacion por moneda queda documentada como mejora futura, no como contrato vigente.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Los límites de transacciones individuales son regulaciones operativas de prevención de fraude obligatorias para evitar cargos excesivos no autorizados o lavado de dinero.

#### FM-FRONT-03: Descontinuidad y comportamiento del límite de cero en [calculate_fee](src/payments_svc/amounts.py#L72)
- **ID**: FM-FRONT-03
- **Categoría**: Frontera
- **Riesgo**: Discontinuidad drástica en el cobro de comisiones y posible pérdida operativa o inconsistencia en la lógica.
- **Entrada que lo dispara**: `amount = Decimal("0")` o `amount = Decimal("0.00")`
- **Comportamiento actual observado en el código**: Retorna inmediatamente `Decimal("0.00")`. Sin embargo, para `amount = Decimal("0.01")` se aplica la comisión mínima de la divisa (ej. `0.30` USD), lo cual causa una discontinuidad matemática abrupta.
- **Contrato esperado recomendado**: Los montos de cobro en cero son inválidos; `validate_amount` debe exigir que el monto sea estrictamente mayor que cero (`amount > 0`), lanzando `AmountError` en caso contrario.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Un monto de cero puede indicar un error en la cesta de compra del cliente o en el cálculo de precios. Permitir cobros de montos extremadamente bajos como `0.01` con una tarifa de comisión de `0.30` genera una deuda neta para el comercio.

#### FM-FRONT-04: Valores no finitos (`NaN`, `Infinity`) en [parse_amount](src/payments_svc/amounts.py#L31)
- **ID**: FM-FRONT-04
- **Categoría**: Frontera
- **Riesgo**: Corrupción en cálculos de bases de datos financieras, caídas lógicas o desborde de memoria.
- **Entrada que lo dispara**: `raw = "NaN"` o `raw = "Infinity"`
- **Comportamiento actual observado en el código**: Lanza [AmountError](src/payments_svc/amounts.py#L23) con el mensaje `"amount must be finite"`.
- **Contrato esperado recomendado**: Bloquear de forma segura cualquier entrada no finita antes de que alcance cualquier cálculo o sistema externo.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Los sistemas financieros operan estrictamente sobre números reales acotados. Permitir infinitos o nulos aritméticos puede corromper los saldos agregados o las pasarelas externas.

#### FM-FRONT-05: Redondeo en la frontera media (`ROUND_HALF_EVEN`) en [round_money](src/payments_svc/amounts.py#L68)
- **ID**: FM-FRONT-05
- **Categoría**: Frontera
- **Riesgo**: Discrepancias de centavos (sobre todo pérdidas/ganancias hormiga) entre los cálculos del negocio, los balances del libro contable y el procesador de pagos.
- **Entrada que lo dispara**: Fracciones de centavo que caen exactamente a la mitad, ej. `Decimal("1.005")` y `Decimal("1.015")`.
- **Comportamiento actual observado en el código**: Aplica redondeo bancario (`ROUND_HALF_EVEN`). Así, `1.005` se redondea a `1.00` y `1.015` se redondea a `1.02`.
- **Contrato esperado recomendado**: Usar redondeo comercial (`ROUND_HALF_UP`) para montos cobrados al cliente.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: La acumulación de diferencias de centavos por redondeos no estandarizados causa descuadres en los balances mensuales agregados de contabilidad y facturación.

---

### 3. Equivalencia

#### FM-EQUIV-01: Pérdida de precisión al inicializar desde tipo float en [parse_amount](src/payments_svc/amounts.py#L31)
- **ID**: FM-EQUIV-01
- **Categoría**: Equivalencia
- **Riesgo**: Pérdida o adición involuntaria de precisión por la representación IEEE 754 de coma flotante binaria, modificando el monto real cobrado.
- **Entrada que lo dispara**: `raw = 0.1 + 0.2` (tipo float, evaluado como `0.30000000000000004`) o `raw = 100.03`
- **Comportamiento actual observado en el código**: Se ejecuta `str(raw)` que produce `"0.30000000000000004"` y resulta en `Decimal("0.30000000000000004")` en lugar del valor lógico `0.3`.
- **Contrato esperado recomendado**: `parse_amount` debe rechazar de forma estricta entradas de tipo `float` lanzando `AmountError`, aceptando únicamente `str`, `int` o `Decimal`.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Los centavos flotantes adicionales introducen inconsistencias en las pasarelas externas que esperan exactamente dos decimales y alteran las facturas de los clientes.

#### FM-EQUIV-02: Formato de string numérico localizado (Separadores de miles/decimales)
- **ID**: FM-EQUIV-02
- **Categoría**: Equivalencia
- **Riesgo**: Interpretación incorrecta de cifras (ej. cobrar 1,000 veces más o menos del monto original si se malinterpretan las comas o puntos decimales) o rechazo de entradas válidas según la región.
- **Entrada que lo dispara**: `"1,000.50"`, `"1.000,50"`, `"1 000.50"`
- **Comportamiento actual observado en el código**: Lanza [AmountError](src/payments_svc/amounts.py#L23) con `"amount must be numeric"` para cualquier string que contenga separadores que la clase `Decimal` no admita de forma nativa.
- **Contrato esperado recomendado**: Aceptar solo formato canonico con punto decimal y sin separadores de miles, por ejemplo `1000.50`. Los formatos localizados deben rechazarse en esta capa.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: La confusión entre la coma `,` y el punto `.` decimal es una de las fuentes principales de cobros erróneos de gran magnitud (e.g. cobrar $10.000 como $10 o viceversa).

#### FM-EQUIV-03: Tipo de datos no soportados en [parse_amount](src/payments_svc/amounts.py#L31)
- **ID**: FM-EQUIV-03
- **Categoría**: Equivalencia
- **Riesgo**: Lanzamiento de excepciones genéricas o comportamientos indefinidos ante payloads corruptos.
- **Entrada que lo dispara**: `raw = []` o `raw = {}`
- **Comportamiento actual observado en el código**: Lanza [AmountError](src/payments_svc/amounts.py#L23) con el mensaje `"amount must be numeric"`.
- **Contrato esperado recomendado**: Validar explícitamente que la entrada sea de tipo `str`, `int` o `Decimal` antes de intentar el casteo y lanzar `AmountError` en caso contrario. El tipo `float` se rechaza por contrato en `FM-EQUIV-01`.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Previene inyecciones de tipos de datos inesperados en los motores de cálculo financiero.

#### FM-EQUIV-04: Robustez en la normalización de la moneda en [normalize_currency](src/payments_svc/amounts.py#L46)
- **ID**: FM-EQUIV-04
- **Categoría**: Equivalencia
- **Riesgo**: Rechazo erróneo de peticiones de pago por discrepancias cosméticas de formato (ej. minúsculas o espacios).
- **Entrada que lo dispara**: `currency = "  usd  "` o `currency = "Usd"`
- **Comportamiento actual observado en el código**: Retorna `"USD"`.
- **Contrato esperado recomendado**: Mantener el comportamiento actual de limpiar espacios y convertir a mayúsculas.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Asegura que las monedas se almacenen en formato estándar ISO 4217, facilitando las conciliaciones contables.

---

### 4. Contrato de Negocio

#### FM-BIZ-01: Límite máximo estático global para múltiples divisas en [validate_amount](src/payments_svc/amounts.py#L60)
- **ID**: FM-BIZ-01
- **Categoría**: Contrato de negocio
- **Riesgo**: Bloqueo injustificado de transacciones cotidianas de montos estándar en monedas con alta denominación nominal (ej. COP).
- **Entrada que lo dispara**: `amount = Decimal("100000.01")` y `currency = "COP"`
- **Comportamiento actual observado en el código**: Aplica la validación de `MAX_AMOUNT` de forma global con el límite estático `100000.00`. Para COP, esto significa un límite de aproximadamente $25 USD.
- **Contrato esperado recomendado**: Mantener un limite maximo global para el alcance actual. Los limites por divisa se reconocen como necesidad realista, pero quedan fuera del contrato vigente.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Hace inviable el cobro de la mayoría de los productos legítimos en el mercado de Colombia debido a un límite inapropiado para la divisa local.

#### FM-BIZ-02: Límite de monto máximo respecto a la tarifa total en [total_with_fee](src/payments_svc/amounts.py#L84)
- **ID**: FM-BIZ-02
- **Categoría**: Contrato de negocio
- **Riesgo**: Exceder el límite de transacción del adquirente y recibir declinaciones al enviar el cobro final.
- **Entrada que lo dispara**: `amount = Decimal("100000.00")` (USD)
- **Comportamiento actual observado en el código**: `total_with_fee` retorna `102900.00 USD` (excediendo `MAX_AMOUNT` en el cobro total).
- **Contrato esperado recomendado**: Para el alcance actual `MAX_AMOUNT` se evalua sobre el monto base (`amount`). El limite sobre el cargo final al tarjetahabiente queda fuera de alcance.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Los límites de procesamiento bancario suelen evaluarse sobre el monto total debitado de la tarjeta. Dejar pasar montos de base en el límite máximo que aumenten por comisiones resultará en rechazos del procesador.

#### FM-BIZ-03: Tasas de comisión y mínimos acoplados en el código
- **ID**: FM-BIZ-03
- **Categoría**: Contrato de negocio
- **Riesgo**: Pérdidas operacionales por no poder actualizar tarifas ante cambios en los contratos con los procesadores, o caídas del servicio por no poder habilitar nuevas monedas rápidamente.
- **Entrada que lo dispara**: Cambios de tarifas de comisiones del procesador o adición de nuevas monedas como `MXN` o `BRL`.
- **Comportamiento actual observado en el código**: Las tarifas de comisión (`FEE_RATES`) y mínimos (`MINIMUM_FEES`) están definidos estáticamente en constantes `Final` en el código. Cualquier moneda ausente en la lista arroja `CurrencyError`.
- **Contrato esperado recomendado**: Mantener las tasas y minimos como constantes de codigo para el ejercicio. Externalizarlos queda como evolucion posterior.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Las tarifas cobradas a los comercios fluctúan constantemente y varían según la negociación de la cuenta bancaria. Forzar cambios de código para actualizar tarifas es un riesgo operativo alto.

#### FM-BIZ-04: Transacciones de bajo valor con tarifas mínimas desproporcionadas
- **ID**: FM-BIZ-04
- **Categoría**: Contrato de negocio
- **Riesgo**: Rentabilidad negativa para el comercio o recargos abusivos a los clientes en micro-transacciones.
- **Entrada que lo dispara**: `amount = Decimal("0.10")` (USD)
- **Comportamiento actual observado en el código**: Se calcula una comisión de `0.30 USD` (el mínimo para USD). El cobro total es `0.40 USD` (un 300% de la compra).
- **Contrato esperado recomendado**: El monto minimo de cobro para este modulo es `0.01`. Las politicas de microtransacciones y rentabilidad quedan fuera de alcance.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Protege al comercio de incurrir en pérdidas financieras por micro-transacciones procesadas.

#### FM-BIZ-05: Redondeo doble e independiente
- **ID**: FM-BIZ-05
- **Categoría**: Contrato de negocio
- **Riesgo**: Discrepancias aritméticas acumulativas en el cálculo final del total transaccionado debido al doble redondeo.
- **Entrada que lo dispara**: Valores con precisión decimal alta que se redondean en `calculate_fee` y nuevamente en `total_with_fee`.
- **Comportamiento actual observado en el código**:
  - [calculate_fee](src/payments_svc/amounts.py#L72) hace `round_money(fee)`.
  - [total_with_fee](src/payments_svc/amounts.py#L84) hace `round_money(amount + calculate_fee(amount, currency))`.
- **Contrato esperado recomendado**: Para el alcance actual se acepta redondear la comision y luego redondear el total. Se documenta como simplificacion contable aceptada para esta implementacion.
- **Estado del contrato**: confirmado
- **Por qué importa para pagos**: Previene pérdidas hormiga y errores de conciliación por redondeos independientes y sucesivos sobre la misma transacción.