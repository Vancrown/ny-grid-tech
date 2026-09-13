"""In-browser bootstrap for the static build.

Runs inside Pyodide after `boot.js` has written the application sources, the
shims and the NYISO zone CSVs under /app. It starts the real Dash app and
exposes `__bw_bridge`, the single function `boot.js` calls to serve every
request dash-renderer makes.

`app.py`, `vis_adj.py` and the `agentic_energy` modules are used unmodified.
"""

import asyncio
import base64
import os
import sys
import traceback
from urllib.parse import urlsplit

APP_ROOT = "/app"
os.chdir(APP_ROOT)

# Shims first so they win over anything else importable.
sys.path.insert(0, os.path.join(APP_ROOT, "shims"))
sys.path.append(os.path.join(APP_ROOT, "Agentics_Energy"))
sys.path.append(os.path.join(APP_ROOT, "Agentics_Energy", "agentic_energy"))
sys.path.append(os.path.join(APP_ROOT, "src"))


def _drive(awaitable):
    """Run a coroutine tree to completion without an event loop.

    Pyodide keeps its own event loop permanently running, so `asyncio.run()`
    inside `data_utils.load_energy_day` always raises. Every await on that path
    resolves immediately — reading a local CSV through the shimmed loader, no
    I/O — so the coroutines can simply be advanced by hand.
    """
    iterator = awaitable.__await__()
    result = None
    while True:
        try:
            pending = iterator.send(result)
        except StopIteration as finished:
            return finished.value
        result = _drive(pending)


class _EventLooplessAsyncio:
    """asyncio facade that drives coroutines synchronously.

    Only `agentic_energy.data_utils` gets this, so the rest of the runtime keeps
    the real asyncio.
    """

    def __getattr__(self, name):
        return getattr(asyncio, name)

    @staticmethod
    def run(coro):
        return _drive(coro)


import cvxpy as cp

# Gurobi does not exist in the browser. cvxpy ships HiGHS through scipy, and on
# this MILP it returns the identical optimum (verified: -2994.5103 for
# NYC 2025-07-15, matching Gurobi bit for bit). app.py still asks for "GUROBI",
# so the constant is repointed rather than the app being edited.
if "GUROBI" not in cp.installed_solvers():
    cp.GUROBI = cp.SCIPY


import app as dash_app
import agentic_energy.data_utils as _data_utils

_data_utils.asyncio = _EventLooplessAsyncio()

_BASE = globals().get("__bw_base", "/")

# dash-renderer builds every asset URL as `<requests_pathname_prefix>_dash-...`,
# including the lazily fetched plotly bundle, so the prefix has to point at the
# site base instead of the domain root. app.py builds Dash() without one and
# dash locks the config read-only after init, so the two keys are unlocked and
# set here rather than editing the app.
_CONFIG_KEYS = ("requests_pathname_prefix", "url_base_pathname")
_config = dash_app.app.config
for _key in _CONFIG_KEYS:
    getattr(_config, "_read_only", {}).pop(_key, None)
    setattr(_config, _key, _BASE)

# Let callback exceptions reach __bw_bridge so they surface as tracebacks
# instead of an opaque 500 page.
dash_app.app.server.config["PROPAGATE_EXCEPTIONS"] = True

_client = None


def _flask_client():
    global _client
    if _client is None:
        _client = dash_app.app.server.test_client()
    return _client


def __bw_bridge(method, path, body):
    """Serve one Dash HTTP request from the in-browser Flask app.

    Returns (status, content_type, base64_body) so the result survives the
    Python/JS boundary without proxy lifetime concerns.

    Callback exceptions are turned into a plain-text traceback: there is no
    server log to read in the browser, so the traceback is the only diagnostic
    available for a failed callback.
    """
    target = urlsplit(path).path or "/"
    client = _flask_client()

    try:
        if method == "POST":
            response = client.post(target, data=body, content_type="application/json")
        else:
            response = client.get(target)
        status = response.status_code
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        payload = response.get_data()
    except Exception:
        status = 500
        content_type = "text/plain; charset=utf-8"
        payload = traceback.format_exc().encode("utf-8")

    # The layout hard-codes "/assets/nyc_building.jpeg". On a project page that
    # resolves to the domain root, so it is re-anchored to the site base. Flask
    # escapes "/" as \u002f inside the JSON payload, hence both spellings.
    if target.startswith("/_dash-layout"):
        escaped_base = _BASE.replace("/", "\\u002f")
        payload = payload.replace(b'"/assets/', b'"' + (_BASE + "assets/").encode())
        payload = payload.replace(
            b"\\u002fassets\\u002f", (escaped_base + "assets\\u002f").encode()
        )

    return (status, content_type, base64.b64encode(payload).decode("ascii"))
