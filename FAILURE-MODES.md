# FAILURE-MODES.md - catalogo de fallos en payments-svc

Este archivo registra los modos de falla que aparecen al usar IA para generar pruebas y revisar codigo en `payments-svc`.

## Categoría: Generación de tests
- [n1] La IA genera solo happy-path. Omite frontera amount == 0 y casos de equivalencia. Tests pasando que no prueban nada.
 
## Categoría: Revisión de código
- [n1] La IA comenta estilo (nombres, espacios) y se pierde lo crítico:
       autorización ausente y reembolso por encima del monto original.