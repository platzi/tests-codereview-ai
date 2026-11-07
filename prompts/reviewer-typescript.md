# Revisor TypeScript - payments-svc

## Objetivo

Revisa solo bloques TypeScript de un PR de `payments-svc`.

Reporta hallazgos accionables sobre tipos, manejo de errores, dinero en cliente, contratos con la API y datos expuestos al usuario.
No revises archivos Python ni YAML en este prompt.

## Focos

- No convertir montos monetarios con `Number` si se requiere precision decimal.
- Mantener el contrato de nombres esperado por la API.
- Diferenciar respuestas exitosas de errores HTTP.
- Evitar filtrar detalles internos al cliente.
- Tests o casos de borde para errores de red y respuestas no exitosas.

## Salida obligatoria

Devuelve solo JSON valido con el contrato de `prompts/reviewer.md`.
La salida debe ser una lista de hallazgos.
Si no hay hallazgos claros, devuelve `[]`.