Este archivo describe los fallos que puedan haber en el código.

##Categoria generación de tests
- [n1] Para amount == 0 en calculate_fee/total_fee la IA documento el comportamiento del código sin el fee como si fuera el contrato y contexto de negocio, sin estimar que se debe aplicar como mínimo en cualquier monto.