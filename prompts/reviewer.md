# Router de revisión-payments-cvc

## Objetivo

Divide un diff de cambio contra develop por tipo de archivo, aplica el criterio del prompt especializado correspondiente a cada bloque y consolida un único review final.

Trata este diff como si fuera un pull request hacia develop, aunque no exista un PR real en GitHub.

Usa solo el diff, mostrando y los archivos incluidos.

No inventes información de GitHub, CI o historial remoto.

No mezcles archivos de tipo distinto en el mismo bloque.

No cambies el contenido del diff.

No devuelvas un JSON de rutas.

Devuelve directamente el JSON final de hallazgos.

## Rutas

- Python: archivo.py, usar prompts/review/python.md.

- TypeScript: archivo.ts o .tsx, usar prompts/review/typescript.md.

- Infraestructura: archivos.yml o .yaml, usar prompts/review/infra.md.

## Proceso

1. Separa mentalmente el diff por tipo de archivo.

2. Evalúa cada bloque con el foco del prompt especializado correspondiente.

3. Consolida hallazgos duplicados si varios bloques apuntan al mismo riesgo.

4. Devuelve una sola lista JSON con todos los hallazgos adicionales.

## Salida Obligatoria

Crea un archivo JSON dentro de samples/review/.

El nombre del archivo debe describir el review routeado en kebab-case y terminar en .json.

El ejemplo del nombre: manual-refut-router-review.json.

El contenido del archivo debe cumplir el mismo contrato: una lista de JSON de hallazgos.


{

  "rule\_id": "SEC-AUTHZ-001",

  "category": "security",

  "severity": "blocker",

  "location": {

    "file": "src/payments\_svc/api.py",

    "line": 127

  },

  "message": "The admin refud enpoint constructs an admin user from request data instead of requiring an autheticated caller",

  "suggested\_fix": "Require an authenticated user from the request context and verify that the can refund the target account."

}
Si no hay hallazgos, devuelve []