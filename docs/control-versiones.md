# Control de versiones del proyecto (GitFlow — datamaq-ml)

Este documento define la taxonomía de ramas, políticas de integración y ciclo de vida de versiones en `datamaq-ml`.

---

## 1. Ramas principales

- `main`: Versión estable y entregable a producción. Cada commit en `main` representa un hito productivo o una versión liberada, etiquetada con su correspondiente tag SemVer (`vX.Y.Z`).
- `develop`: Rama base de desarrollo e integración continua. Recibe los aportes de las ramas de trabajo que hayan superado las revisiones y el guantelete de pruebas.

Ambas ramas son protegidas: no se permite push directo ni force-push; toda integración se realiza a través de Pull Requests con CI en verde.

---

## 2. Ramas de soporte y trabajo temporal

Las ramas de soporte se abren desde `develop` (o desde `main` en caso de hotfix) y siguen la convención de tipos de commit:

| Prefijo | Origen | Destino | Propósito | Ejemplo |
|---|---|---|---|---|
| `feat/issue-<n>-<slug>` | `develop` | `develop` | Nuevas capacidades o funcionalidades del motor NILM. | `feat/issue-208-banco-capacitores` |
| `fix/issue-<n>-<slug>` | `develop` | `develop` | Corrección de defectos o desvíos en desarrollo. | `fix/issue-35-parser-timestamp` |
| `docs/issue-<n>-<slug>` | `develop` | `develop` | Documentación técnica, pedagógica o de arquitectura. | `docs/issue-22-rubrica-educativa` |
| `chore/<slug>` | `develop` | `develop` | Tareas de CI/CD, configuración de entorno o dependencias. | `chore/ci-runner-config` |
| `hotfix/<slug>` | `main` | `main` y `develop` | Corrección crítica urgente sobre la versión productiva. | `hotfix/tolerancia-corte-critico` |

---

## 3. Política de Integración (Merge Strategy)

Para mantener un historial limpio, trazable y sin ramas huérfanas:

1. **De ramas de trabajo hacia `develop`:**
   - **Squash and merge** (o Rebase): condensa los commits exploratorios en uno o varios commits atómicos con formato de [Conventional Commits](https://www.conventionalcommits.org/).
   - **Auto-eliminación:** La rama de trabajo se elimina automáticamente del repositorio remoto una vez completada la fusión.
2. **De `develop` hacia `main` (Promoción de Release):**
   - **Merge commit explícito (`--no-ff`)**: Preserva el hito de lanzamiento de la versión.
   - **Etiquetado:** Se genera el tag `vX.Y.Z` directamente sobre el commit resultante en `main`.
3. **De `hotfix` hacia `main` y `develop`:**
   - Se integra en `main` con tag de parche (`vX.Y.Z+1`) y se propaga inmediatamente a `develop` mediante merge o cherry-pick.

---

## 4. Flujo de trabajo habitual

```text
main (v1.0.0)
  └─► develop
        └─► feat/issue-208-banco-capacitores
              │ (commits atómicos + TDD)
        ◄─────┘ PR: Squash & Merge (elimina rama remota)
  ◄─── PR de Release: Merge Commit (--no-ff) + Tag v1.1.0
```

### Comandos frecuentes

```bash
# 1. Iniciar trabajo sincronizado con develop
git switch develop
git pull
git switch -c feat/issue-208-banco-capacitores

# 2. Desarrollo con commits atómicos por fase
git add src/domain/cargas/banco_capacitores.py tests/unit/cargas/test_banco_capacitores.py
git commit -m "feat(domain): agregar deteccion de conmutaciones en banco de capacitores"

# 3. Validar localmente antes de subir
./run.sh test
./run.sh gauntlet
./run.sh lint

# 4. Publicar la rama para Pull Request
git push -u origin feat/issue-208-banco-capacitores
```

### Configuración local recomendada

Para que Git limpie automáticamente referencias a ramas remotas ya eliminadas:
```bash
git config --global fetch.prune true
```
