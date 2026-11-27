# Cómo aportar a datamaq-ml

Gracias por aportar. Este repositorio se licencia bajo la **AGPL-3.0-or-later** (ver [`LICENSE`](LICENSE)).
Todo aporte se recibe bajo esa misma licencia.

## Certificado de origen del desarrollador (DCO)

No pedimos ceder derechos ni firmar un CLA. Cada commit tiene que llevar, en cambio, una línea
`Signed-off-by` con tu nombre y tu email:

```text
Signed-off-by: Nombre Apellido <email@ejemplo.com>
```

Git la agrega sola con `-s`:

```bash
git commit -s -m "fix(cargas): corregir el umbral de arranque"
```

Con esa línea certificás lo que dice el [Developer Certificate of Origin 1.1](https://developercertificate.org/):
que el aporte es tuyo, o que tenés derecho a enviarlo bajo la licencia del proyecto, y que aceptás que quede
registrado públicamente junto con tu firma.

- Usá tu nombre real y un email que recibas. El de `Signed-off-by` tiene que coincidir con el autor del commit.
- Si olvidaste firmar el último commit: `git commit --amend -s --no-edit`.
- Si olvidaste firmar varios commits de tu rama: `git rebase --signoff origin/develop`.
- Un PR con commits sin firmar no se mergea.

## Flujo de trabajo

1. Creá una rama desde `develop` con un nombre temático: `feat|fix|chore|test|docs/issue-N-slug`.
2. Hacé commits atómicos con [Conventional Commits](https://www.conventionalcommits.org/) en español, con el
   "por qué" en el cuerpo.
3. Antes de abrir el PR, corré el gauntlet local:

   ```bash
   ./run.sh install
   ./run.sh test
   ./run.sh gauntlet
   ./run.sh audit
   ./run.sh lint
   ```

4. Abrí el PR hacia `develop`. El CI corre esos mismos comandos y tiene que quedar en verde.

## Datos y privacidad

- No subas mediciones reales, nombres de clientes, IPs, emails ni credenciales. El único dataset versionado
  es el sintético (`./run.sh simulate`).
- Los nombres de clientes que tapa el exportador educativo van en un archivo local no versionado. Ver el
  ejemplo versionado en `config/`.

## Marca

Aportar código no da derechos sobre el nombre ni el logo de DataMaq. Ver [`TRADEMARKS.md`](TRADEMARKS.md).
