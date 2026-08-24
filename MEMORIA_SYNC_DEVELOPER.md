# Memoria: sync de `developer` rechazado por push (2026-08-24)

## Que paso

```
$ git push origin developer
 ! [rejected]  developer -> developer (fetch first)
```

El push se rechazo porque en GitHub (remoto) `developer` tiene un commit que
tu copia local no tenia: `90d67b3 - Merge branch 'platzi:prep/modulo-0-base-funcional' into developer`.

Ese commit sucedio al mergear la PR de `prep/modulo-0-base-funcional` hacia
`developer` (probablemente al aceptar una sugerencia de GitHub o al confundir
la direccion del merge). Como las dos ramas tienen estructuras de carpeta
distintas (una con archivos en la raiz, la otra con todo bajo
`tests-codereview-ai/`) y son historias no relacionadas, Git no encontro
rutas en comun para pisar: **el merge solo AGREGO una copia duplicada del
proyecto en la raiz del repo** (README.md, pyproject.toml, src/payments_svc/*
sin el prefijo `tests-codereview-ai/`). Verificado con
`git diff developer origin/developer` antes de tocar nada:
cero cambios en ningun archivo bajo `tests-codereview-ai/` (nuestro codigo,
tests, workflow y el resto de lo trabajado en esta sesion quedan intactos).

## Punto de restauracion (backup)

Antes de hacer nada se creo un branch local que apunta exactamente al commit
que tenias antes de tocar nada:

```
git branch backup-developer-antes-de-pull-20260824   # -> commit 0e4213b "Subiendo yml de test"
```

Este branch es SOLO local (no se pusheo a GitHub). Sirve como punto de
restauracion si el merge/pull sale mal.

## Plan (paso a paso)

1. Confirmar que no hay cambios sin commitear:
   ```
   git status
   ```
   (debe decir "nothing to commit, working tree clean"; si no, `git stash push -u` antes de seguir)

2. Traer las referencias remotas actualizadas (no toca archivos locales):
   ```
   git fetch origin
   ```

3. Mergear explicitamente (evita ambiguedad con la config de pull.rebase):
   ```
   git merge origin/developer --no-edit
   ```
   Esto crea un commit de merge combinando tu commit local
   (`0e4213b Subiendo yml de test`) con el remoto (`90d67b3`). No deberia
   haber conflictos (paths distintos, ver seccion "Que paso").

4. Verificar que nada bajo `tests-codereview-ai/` cambio respecto a antes del
   merge:
   ```
   git diff backup-developer-antes-de-pull-20260824 HEAD -- tests-codereview-ai/
   ```
   Salida esperada: vacia (sin diferencias).

5. Revisar que junto se sumaron los archivos duplicados en la raiz (esperado,
   ver seccion "Que paso"; se puede limpiar despues si se quiere):
   ```
   git status
   git log --oneline -3
   ```

6. Recien ahi, push:
   ```
   git push origin developer
   ```

## Si algo sale mal (rollback)

Si en el paso 3 aparecen conflictos y no queres resolverlos ahora:
```
git merge --abort
```
Esto deja todo como estaba antes del merge, sin perder nada.

Si ya se hizo el merge (commit creado) y se quiere deshacer por completo,
volviendo exactamente al estado de antes de este intento:
```
git reset --hard backup-developer-antes-de-pull-20260824
```
ADVERTENCIA: `--hard` descarta cualquier cambio no commiteado en el working
tree en ese momento. Como el working tree estaba limpio antes de empezar
(confirmado en el paso 1), esto es seguro en este caso puntual.

Si ya se hizo push y se necesita revertir en GitHub tambien, avisar antes de
hacer un push --force: preferir un commit nuevo que revierta
(`git revert -m 1 <hash-del-merge>`) en vez de forzar, para no reescribir
historia que otros ya puedan tener.

## Pendiente para despues (no urgente)

La copia duplicada del proyecto en la raiz del repo (fuera de
`tests-codereview-ai/`) quedo mezclada en el historial de `developer` por el
merge de `prep/modulo-0-base-funcional`. No rompe nada hoy, pero conviene
decidir en algun momento si se borra esa copia duplicada o se documenta por
que existen dos.
