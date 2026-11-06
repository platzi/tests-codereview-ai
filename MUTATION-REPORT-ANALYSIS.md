# Análisis del reporte de mutation testing

## Alcance y evidencia

Análisis del reporte de `cr-report.exe mutation.sqlite` compartido en la conversación para `src/payments_svc/amounts.py`, contrastado con el código y los contratos confirmados en `FAILURE-MODES.md`.

- Mutantes totales: **91**.
- Detectados (`KILLED`): **63**.
- Sobrevivientes (`SURVIVED`): **28** (30.77%).
- Todos los trabajos finalizaron con `WorkerOutcome.NORMAL`.

Un mutante sobreviviente indica que la suite no detectó su cambio; no demuestra por sí solo que falte cobertura de negocio. `KILLED` indica que la suite detectó el cambio, pero este reporte no muestra qué test lo detectó ni si ocurrió mediante una aserción o un error.

El reporte no contiene diffs ni números de línea. Las ubicaciones indicadas se infieren de las apariciones de los operadores en el código actual. Si la ejecución utilizó otra revisión del módulo, se deben confirmar esas ubicaciones con los diffs de los mutantes antes de adoptar conclusiones definitivas.

## Clasificación

Se omite el prefijo `core/ReplaceBinaryOperator_` o `core/ReplaceComparisonOperator_` en los identificadores. Cada fila que indica índices **0 y 1** representa dos mutantes distintos. Los 63 detectados se agrupan porque no requieren trabajo adicional a partir de este reporte.

| Mutante | Función | Qué cambio hizo | Qué comportamiento podría estar sin cubrir | Clasificación | Por qué | Lo resolveríamos en una siguiente iteración de test |
|---|---|---|---|---|---|---|
| `BitOr_Add`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `+` en la unión de tipos | Evaluación de anotaciones en tiempo de ejecución | no accionable | Con las anotaciones pospuestas, no altera el procesamiento del monto. No hay contrato confirmado sobre introspección. | no |
| `BitOr_Sub`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `-` | Evaluación de anotaciones | no accionable | Afecta la anotación, sin cambiar las validaciones ejecutadas. | no |
| `BitOr_Mul`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `*` | Evaluación de anotaciones | no accionable | No corresponde a un contrato confirmado de pagos. | no |
| `BitOr_Div`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `/` | Evaluación de anotaciones | no accionable | No cambia el comportamiento monetario ejecutado. | no |
| `BitOr_FloorDiv`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `//` | Evaluación de anotaciones | no accionable | No existe un contrato confirmado para evaluar estas anotaciones. | no |
| `BitOr_Mod`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `%` | Evaluación de anotaciones | no accionable | Afecta metadatos de tipos fuera del contrato probado. | no |
| `BitOr_Pow`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `**` | Evaluación de anotaciones | no accionable | No afecta las validaciones ni los resultados del parser. | no |
| `BitOr_RShift`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `>>` | Evaluación de anotaciones | no accionable | No hay una obligación confirmada sobre estos metadatos. | no |
| `BitOr_LShift`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `<<` | Evaluación de anotaciones | no accionable | No modifica el procesamiento monetario ejecutado. | no |
| `BitOr_BitAnd`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `&` | Evaluación de anotaciones | no accionable | No está conectado con un contrato confirmado de comportamiento. | no |
| `BitOr_BitXor`, índices 0 y 1; 2 sobrevivientes | Anotación de `parse_amount` | Sustituye `\|` por `^` | Evaluación de anotaciones | no accionable | No justifica agregar tests de introspección solo para eliminarlo. | no |
| `Eq_Lt`, índice 0; sobreviviente | `calculate_fee` | Cambia `amount == 0` por `amount < 0` | Ninguno dentro del contrato vigente | equivalente | La validación previa rechaza montos menores a `0.01`. Ambas condiciones son falsas para los montos admitidos que llegan a esa línea. | no |
| `Eq_LtE`, índice 0; sobreviviente | `calculate_fee` | Cambia `amount == 0` por `amount <= 0` | Ninguno dentro del contrato vigente | equivalente | Cero y negativos se rechazan antes de llegar a la condición, según FM-FRONT-03 y FM-BIZ-04. | no |
| `Eq_Is`, índice 0; sobreviviente | `calculate_fee` | Cambia igualdad de valor por identidad de objetos | Ninguno dentro del contrato vigente | equivalente | Para los montos admitidos, la comparación con un objeto cero sigue siendo falsa. La rama de cero es inalcanzable. | no |
| `Lt_Eq`, índice 0; sobreviviente | `validate_amount` | Cambia `amount < 0` por `amount == 0` | Diferenciar el mensaje de negativos y cero | no accionable | Los negativos siguen rechazándose por `amount < CENT`; cero también se rechaza. FM-FRONT-01 no fija un mensaje y FM-FRONT-03 explícitamente no lo exige. | no |
| `Lt_LtE`, índice 0; sobreviviente | `validate_amount` | Cambia `amount < 0` por `amount <= 0` | Mensaje específico para cero | no accionable | Cero sigue lanzando `AmountError`, como exige FM-FRONT-03; cambia la rama que lo rechaza. | no |
| `Lt_Is`, índice 0; sobreviviente | `validate_amount` | Cambia `amount < 0` por `amount is Decimal("0")` | Mensaje específico para negativos | no accionable | La validación posterior del mínimo sigue rechazando negativos y cero. Cambia el diagnóstico, sin incumplir los contratos confirmados. | no |
| Otros 63 mutantes, detectados (`KILLED`) | Funciones del módulo según el operador; el reporte no individualiza sus ubicaciones | Alteran aritmética, comparaciones, condiciones o manejo de excepciones | No se evidencia una brecha adicional para estos mutantes | no accionable | La suite ya detectó los cambios. Este reporte resumido no identifica qué test detectó cada uno. | no |

## Interpretación y límites

Los 28 sobrevivientes se distribuyen en **22 mutantes de anotaciones**, **3 equivalentes dentro del contrato vigente** y **3 que cambian mensajes no exigidos por los contratos confirmados**.

Los mutantes de anotaciones se clasifican como no accionables, en lugar de equivalentes: una herramienta que evalúe las anotaciones podría observar diferencias, aunque esa capacidad no forma parte del contrato confirmado.

Los tres mutantes de la primera comparación de `validate_amount` tampoco se consideran equivalentes en sentido estricto: pueden cambiar el texto de la excepción. Los contratos exigen rechazar los montos con `AmountError`, sin exigir esa distinción de mensajes.

Con esta evidencia no se identifica un sobreviviente que requiera nuevos tests para satisfacer los contratos confirmados. Tampoco se identifica una decisión de negocio pendiente. Exigir mensajes específicos adicionales o evaluación de anotaciones ampliaría el contrato y no se propone aquí.

Este resultado no demuestra cobertura completa del módulo: las conclusiones se limitan a los operadores y mutantes incluidos en el reporte. No se propone código de tests ni se modifica producción, la suite o `FAILURE-MODES.md` como parte de este análisis.
