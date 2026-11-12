# gh-tui

Interfaz de terminal (TUI) para [GitHub CLI](https://cli.github.com), hecha con Python y [Textual](https://textual.textualize.io). Usa `gh` como subproceso, así que reutiliza tu login, SSH y configuración: no guarda ningún token propio.

Permite, sin salir de la terminal:

- **Cuenta:** ver el estado de sesión, login y logout.
- **Repos:** listar, filtrar, clonar y abrir en el navegador.
- **Pull requests:** listar con estado de CI y review, ver detalle y diff, aprobar y hacer merge (squash / merge / rebase).
- **Pipelines (Actions):** listar runs, ver detalle, logs (completos o solo los fallidos) y relanzar.

## Requisitos

- [`gh`](https://cli.github.com) instalado y en el `PATH`
- Python 3.10+
- [`pipx`](https://pipx.pypa.io) (recomendado)

## Instalación

```bash
pipx install git+https://github.com/njpd57/gh-tui.git
```

Desde un clon local:

```bash
git clone https://github.com/njpd57/gh-tui.git
cd gh-tui
pipx install .
```

Actualizar: `pipx upgrade gh-tui` (o `pipx install --force .` desde el clon).

## Uso

```bash
ghtui
```

Si aún no has iniciado sesión, ve a la pestaña **Cuenta** (`1`) y pulsa `l`, o ejecuta `gh auth login` antes.

Si lo lanzas dentro de un repositorio git, ese repo queda seleccionado para las pestañas PRs y Pipelines. Si no, elige uno en **Repos** y pulsa `Enter`.

### Atajos

| Tecla | Acción |
|---|---|
| `1` `2` `3` `4` | Cuenta / Repos / PRs / Pipelines |
| `r` | Refrescar (fuerza consulta a GitHub, ignorando la caché) |
| `/` | Filtrar la tabla actual |
| `Enter` | Repos: seleccionar repo · PRs / Runs: ver detalle |
| `c` | Repos: clonar |
| `o` | Repos: abrir en navegador · Cuenta: logout |
| `a` | PRs: aprobar |
| `m` | PRs: merge |
| `d` | PRs: ver diff |
| `l` | Cuenta: login · Pipelines: logs |
| `f` | Pipelines: solo logs fallidos |
| `R` | Pipelines: relanzar run |
| `Esc` / `q` | Cerrar visor o modal · `q` en la pantalla principal sale |

Las acciones que modifican algo (aprobar, merge, rerun, logout) piden confirmación.

### Configuración

- `GHTUI_CLONE_DIR`: directorio por defecto al clonar (por defecto `~/Proyects`).
- `GHTUI_CACHE_TTL`: segundos que la caché se considera fresca (por defecto `300`).

### Listados completos y caché

Repos, PRs y pipelines se listan completos (sin límite fijo). Los resultados se guardan en
`~/.cache/ghtui` (o `$XDG_CACHE_HOME/ghtui`): al abrir se muestra lo cacheado al instante y,
si está vencido, se actualiza en segundo plano. Si falla la red, se conservan los datos cacheados.

## Desarrollo

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ghtui
```

## Licencia

MIT
