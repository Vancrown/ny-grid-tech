# Static build (GitHub Pages)

`app.py` normally needs a Python server. This directory makes the same app run
as a **plain static site**, so GitHub Pages can host it.

Nothing about the app changes: `app.py`, `src/vis_adj.py` and the
`agentic_energy` modules are shipped verbatim and executed by
[Pyodide](https://pyodide.org) (CPython compiled to WebAssembly) in the
visitor's browser. `boot.js` answers Dash's own HTTP protocol from inside the
browser, so `dash-renderer` cannot tell the difference between this and a real
server.

```
dash-renderer ──fetch/XHR──▶ window bridge ──▶ Flask test_client()
                                                   (inside Pyodide)
```

## Build

```bash
uv sync                                # first time only — the build imports app.py
uv run python tools/export_static.py   # writes _site/
python3 -m http.server 3000 --directory _site
```

Then open <http://localhost:3000/>.

To reproduce the GitHub Pages subdirectory layout (`/<repo>/`), serve the repo
root instead and open <http://localhost:3001/_site/>:

```bash
python3 -m http.server 3001   # run from the repo root
```

`_site/` is generated and git-ignored; `.github/workflows/pages.yml` builds it
in CI and publishes it.

> The build has to run with the project environment (`uv run`): it imports
> `app.py` to enumerate the Dash component suites out of the installed wheels,
> so the system `python3` fails on `import numpy`. Serving `_site/` needs no
> dependencies.

## What the build produces

| Path | Contents |
| --- | --- |
| `index.html`, `boot.js` | browser shell: progress UI + the bridge |
| `py/` | the app's Python, byte-identical to the repo |
| `py/shims/` | stand-ins for modules with no browser equivalent |
| `py/manifest.json` | what `boot.js` must load |
| `runtime.json` | Pyodide URL and the exact package pins |
| `_dash-component-suites/` | Dash's JS, extracted from the installed wheels |
| `data/NYISO_zones/` | the 15 zone CSVs the optimiser reads |
| `assets/` | `styles.css`, `nyc_building.jpeg` |

## Shims

Four imports have no browser equivalent. Each one is a stand-in that covers
only the surface the app touches at import time.

| Module | Why |
| --- | --- |
| `agentics` | `data_loader` loads CSVs through `AG.from_csv`; the shim does it with `csv` |
| `dotenv` | `data_loader` calls `load_dotenv(find_dotenv())`; a static site has no `.env` |
| `mcp` | `milp_mcp_server` builds a `FastMCP` server it never runs here |
| `crewai_tools` | `mcp_clients` imports `MCPServerAdapter`; the app never opens an MCP transport |

## Browser-specific adaptations

All of these live in `py/boot_app.py`; no repo source file is edited.

- **Solver.** `app.py` asks for Gurobi. `cvxpy.GUROBI` is repointed at
  `cvxpy.SCIPY`, which reaches HiGHS through scipy. Verified numerically
  identical: `CAPITL 2025-01-01` gives `-561.5242` on both Gurobi and HiGHS.
- **Event loop.** Pyodide's event loop is permanently running, so
  `asyncio.run()` inside `data_utils.load_energy_day` always raises. That one
  module gets a facade whose `run()` drives the coroutine tree synchronously —
  the load path only awaits local computation, never I/O.
- **Subdirectory hosting.** GitHub Pages serves project sites from
  `/<repo>/`. `requests_pathname_prefix` is set to that base so dash-renderer
  builds every asset URL inside it, including the lazily fetched
  `plotly.min.js`. Dash locks that config key read-only after `Dash()` is
  constructed, so the lock is released for those two keys first.
- **Hard-coded asset paths.** `app.py` uses `src="/assets/nyc_building.jpeg"`,
  which would resolve to the domain root. The `_dash-layout` response is
  re-anchored to the site base — in both plain and `\u002f`-escaped form,
  because Flask escapes slashes in JSON.

## Known limitations

- **First load is slow.** Pyodide plus the wheels is roughly 25 MB. The browser
  caches it, but a cold visit takes 10–30 s depending on the connection.
- **Mobile browsers** may run out of memory on low-end devices.
- **`assets/` must be staged into Pyodide's filesystem** before `import app`,
  otherwise Dash emits no `<link>` for `assets/styles.css`. The bytes still come
  from the static server; only the file listing matters.
- **`probe.html`** is a standalone diagnostic that checks Pyodide can install
  dash and drive a Flask `test_client()`. It is not part of the app.
