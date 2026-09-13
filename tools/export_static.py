"""Assemble the static build of the Dash app into _site/.

The site is a plain folder of static files: the app sources are shipped as
Python text, the zone CSVs as data, the Dash component suites as real JS, and
everything else is the browser shell. `boot.js` loads the Python side into
Pyodide at runtime.

Usage:
    python tools/export_static.py [--out _site]

The repo's own files are copied, never rewritten, so app.py and vis_adj.py stay
byte-identical to what runs locally.

The dash / dash-bootstrap-components versions installed here are written into
the build's runtime.json, so the browser installs exactly the versions the
vendored component suites came from.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STATIC_SOURCES = REPO_ROOT / "static"
ASSET_SOURCES = REPO_ROOT / "assets"
ZONE_DATA_SOURCES = (
    REPO_ROOT / "Agentics_Energy" / "agentic_energy" / "data" / "NYISO_zones"
)

# Imported so the component suites can be enumerated from the app that is
# actually being deployed.
APP_IMPORT_PATHS = (
    REPO_ROOT / "Agentics_Energy",
    REPO_ROOT / "Agentics_Energy" / "agentic_energy",
    REPO_ROOT / "src",
)

APP_SOURCE_FILES = (
    "app.py",
    "src/vis_adj.py",
    "Agentics_Energy/agentic_energy/schemas.py",
    "Agentics_Energy/agentic_energy/data_utils.py",
    "Agentics_Energy/agentic_energy/data_loader.py",
    "Agentics_Energy/agentic_energy/mcp_clients.py",
    "Agentics_Energy/agentic_energy/milp/milp_mcp_server.py",
)

SHELL_FILES = ("index.html", "boot.js", "boot_app.py", "probe.html")

# Pinned to whatever the app itself depends on, so the shipped JS matches.
PINNED_PACKAGES = ("dash", "dash-bootstrap-components")

SUITE_URL_PREFIX = "/_dash-component-suites"
MAX_SUITE_BYTES = 12 * 1024 * 1024


def load_dash_app():
    """Load the repo-root app.py by path.

    A plain `import app` is ambiguous here: `Agentics_Energy/app.py` (the
    Streamlit variant) is also importable once the app's own sys.path entries
    are installed.
    """
    for path in reversed(APP_IMPORT_PATHS):
        sys.path.insert(0, str(path))
    os.chdir(REPO_ROOT)

    spec = importlib.util.spec_from_file_location("bw_dash_app", REPO_ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["bw_dash_app"] = module
    spec.loader.exec_module(module)
    return module


def copy_shell(site_dir: Path) -> list[str]:
    for name in SHELL_FILES:
        shutil.copy2(STATIC_SOURCES / name, site_dir / name)
    return list(SHELL_FILES)


def copy_python_payload(site_dir: Path) -> list[str]:
    py_dir = site_dir / "py"
    for relative in APP_SOURCE_FILES:
        destination = py_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)

    shutil.copytree(STATIC_SOURCES / "shims", py_dir / "shims", dirs_exist_ok=True)
    shutil.copy2(STATIC_SOURCES / "boot_app.py", py_dir / "boot_app.py")

    shim_files = sorted(
        path.relative_to(py_dir).as_posix() for path in (py_dir / "shims").rglob("*.py")
    )
    return list(APP_SOURCE_FILES) + shim_files


def copy_zone_data(site_dir: Path) -> list[str]:
    zone_names = sorted(path.stem for path in ZONE_DATA_SOURCES.glob("*.csv"))
    destination = site_dir / "data" / "NYISO_zones"
    destination.mkdir(parents=True, exist_ok=True)
    for zone in zone_names:
        shutil.copy2(ZONE_DATA_SOURCES / f"{zone}.csv", destination / f"{zone}.csv")
    return zone_names


def copy_assets(site_dir: Path) -> list[str]:
    shutil.copytree(ASSET_SOURCES, site_dir / "assets", dirs_exist_ok=True)
    return sorted(
        path.name for path in (site_dir / "assets").iterdir() if path.is_file()
    )


def suite_urls(dash_app) -> list[str]:
    """Every component suite the app can serve, as served URLs.

    Source maps are skipped: dash-renderer never requests them.
    """
    registered = dash_app.app.registered_paths
    return sorted(
        f"{SUITE_URL_PREFIX}/{package}/{relative_path}"
        for package, relative_paths in registered.items()
        for relative_path in relative_paths
        if not relative_path.endswith(".map")
    )


def extract_component_suites(site_dir: Path, dash_app) -> tuple[list[str], int]:
    client = dash_app.app.server.test_client()

    # Component suites are registered lazily, the first time the layout is
    # served. Render once so registered_paths is populated.
    client.get("/_dash-layout")

    written: list[str] = []
    total_bytes = 0

    urls = suite_urls(dash_app)
    if not urls:
        raise SystemExit("no component suites were registered by the app")

    for url in urls:
        response = client.get(url)
        if response.status_code != 200:
            raise SystemExit(f"cannot extract {url} (HTTP {response.status_code})")
        payload = response.data
        if len(payload) > MAX_SUITE_BYTES:
            raise SystemExit(f"{url} is unexpectedly large ({len(payload)} bytes)")

        destination = site_dir / url.lstrip("/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        written.append(url)
        total_bytes += len(payload)

    return written, total_bytes


def write_runtime_config(site_dir: Path, suite_count: int) -> dict:
    runtime = json.loads((STATIC_SOURCES / "runtime.json").read_text(encoding="utf-8"))
    pinned = [f"{name}=={importlib.metadata.version(name)}" for name in PINNED_PACKAGES]
    runtime["packages"] = pinned + runtime.pop("extraPackages", [])
    runtime["suiteCount"] = suite_count
    (site_dir / "runtime.json").write_text(
        json.dumps(runtime, indent=2) + "\n", encoding="utf-8"
    )
    return runtime


def write_manifest(
    site_dir: Path,
    python_files: list[str],
    zone_names: list[str],
    asset_files: list[str],
) -> None:
    manifest = {"python": python_files, "zones": zone_names, "assets": asset_files}
    (site_dir / "py" / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def build(site_dir: Path) -> None:
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)
    (site_dir / ".nojekyll").touch()

    shell_files = copy_shell(site_dir)
    python_files = copy_python_payload(site_dir)
    zone_names = copy_zone_data(site_dir)
    asset_files = copy_assets(site_dir)

    dash_app = load_dash_app()
    suites, suite_bytes = extract_component_suites(site_dir, dash_app)
    runtime = write_runtime_config(site_dir, len(suites))

    write_manifest(site_dir, python_files, zone_names, asset_files)

    megabytes = directory_size(site_dir) / 1024 / 1024
    print(f"built {site_dir.relative_to(REPO_ROOT)}  ({megabytes:.1f} MB)")
    print(f"  shell   : {', '.join(shell_files)}")
    print(f"  python  : {len(python_files)} modules")
    print(f"  zones   : {len(zone_names)} csv files")
    print(f"  assets  : {', '.join(asset_files)}")
    print(f"  suites  : {len(suites)} files, {suite_bytes / 1024 / 1024:.1f} MB")
    print(f"  runtime : {', '.join(runtime['packages'])}")
    print("  serve   : python3 -m http.server 3000 --directory _site")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", default="_site", help="output directory (default: _site)"
    )
    arguments = parser.parse_args()
    build((REPO_ROOT / arguments.out).resolve())


if __name__ == "__main__":
    main()
