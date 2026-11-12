# gh-tui

Interfaz de terminal (TUI) para [GitHub CLI](https://cli.github.com), hecha con Python y [Textual](https://textual.textualize.io). Usa `gh` como subproceso, así que reutiliza tu login, SSH y configuración: no guarda ningún token propio.

Permite, sin salir de la terminal:

- **Cuenta:** ver el estado de sesión, login, logout y cambiar entre cuentas.
- **Repos:** listar, filtrar, clonar, abrir en el navegador, crear (con README, `.gitignore`, licencia y clonado opcional), renombrar, archivar, cambiar visibilidad o descripción y borrar.
- **Pull requests:** listar con estado de CI y review, ver detalle y diff, crear, aprobar (con comentario), pedir cambios, comentar, alternar borrador/listo y hacer merge (squash / merge / rebase).
- **Pipelines (Actions):** listar runs, ver detalle, logs (completos o solo los fallidos), relanzar, cancelar y lanzar un workflow a mano.
- **Releases:** listar, ver, crear (con notas automáticas si las dejas vacías) y borrar.
- **Notificaciones:** ver la bandeja y marcar como leídas.
- **Búsqueda global:** repos, issues, PRs y código.

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

Muchas teclas dependen de la pestaña activa.

| Tecla | Acción |
|---|---|
| `1`–`6` | Cuenta / Repos / PRs / Pipelines / Releases / Notifs |
| `r` | Refrescar (fuerza consulta a GitHub, ignorando la caché) |
| `/` | Filtrar la tabla actual |
| `S` | Buscar en GitHub (repos, issues, PRs o código) |
| `Enter` | Repos: seleccionar repo · PRs / Runs / Releases: ver detalle · Notifs: marcar leída |
| `n` | Crear: repo, PR o release según la pestaña |
| `c` | Repos: clonar |
| `o` | Repos: abrir en navegador · Cuenta: logout |
| `D` | Repos / Releases: borrar |
| `A` | Repos: archivar o desarchivar |
| `N` | Repos: renombrar |
| `v` | Repos: cambiar visibilidad |
| `E` | Repos: editar descripción |
| `a` | PRs: aprobar (con comentario opcional) |
| `x` | PRs: pedir cambios · Pipelines: cancelar run |
| `C` | PRs: comentar |
| `t` | PRs: alternar borrador / listo para revisión |
| `m` | PRs: merge · Notifs: marcar leída |
| `M` | Notifs: marcar todas como leídas |
| `d` | PRs: ver diff |
| `l` | Cuenta: login · Pipelines: logs |
| `s` | Cuenta: cambiar de cuenta |
| `f` | Pipelines: solo logs fallidos |
| `R` | Pipelines: relanzar run |
| `w` | Pipelines: lanzar workflow |
| `Esc` / `q` | Cerrar visor o modal · `q` en la pantalla principal sale |

Las acciones que modifican algo piden confirmación. Borrar un repo pide además escribir su nombre completo.

### Permisos de `gh`

Borrar repos necesita el scope `delete_repo` (`gh auth refresh -s delete_repo`) y las notificaciones el scope `notifications`. Si falta alguno, `gh` devuelve el error y se muestra en un aviso.

Al crear un PR, la rama origen se rellena con la rama git del directorio desde donde lanzaste `ghtui`. Si marcas «clonar» al crear un repo, se clona en ese mismo directorio.

### Configuración

- `GHTUI_CLONE_DIR`: directorio por defecto al clonar (por defecto `~/Proyects`).
- `GHTUI_CACHE_TTL`: segundos que la caché se considera fresca (por defecto `300`).

### Listados completos y caché

Repos, PRs, pipelines y releases se listan completos (sin límite fijo). Los resultados se guardan en
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
