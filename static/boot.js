/*
 * Borrow Watts — static bootstrap.
 *
 * Runs the original Dash app (app.py, unchanged) inside Pyodide and answers
 * Dash's own HTTP protocol from the browser, so the app needs no server.
 *
 *   dash-renderer  --fetch/XHR-->  window bridge  -->  Flask test_client()
 *                                                        (inside Pyodide)
 */

const RUNTIME_CONFIG_URL = "runtime.json";

// Requests carrying these markers are answered locally by the Python app.
const DYNAMIC_MARKERS = [
  "_dash-update-component",
  "_dash-layout",
  "_dash-dependencies",
  "_dash-config",
  "_favicon.ico",
];

const nativeFetch = window.fetch.bind(window);

// ── UI helpers ────────────────────────────────────────────────────────────────
const statusEl = document.getElementById("boot-status");
const detailEl = document.getElementById("boot-detail");
const barEl = document.querySelector("#bar > i");
const logPre = document.getElementById("boot-log-pre");
const t0 = performance.now();

function stage(pct, message, detail = "") {
  if (barEl) barEl.style.width = `${pct}%`;
  if (statusEl) statusEl.textContent = message;
  if (detailEl) detailEl.textContent = detail;
  log(`${message}${detail ? " — " + detail : ""}`);
}

function log(message) {
  const ms = String(Math.round(performance.now() - t0)).padStart(6);
  if (logPre) logPre.textContent += `[${ms}ms] ${message}\n`;
}

function fail(error) {
  log("FATAL " + (error && error.stack ? error.stack : error));
  if (statusEl) {
    statusEl.className = "err";
    statusEl.textContent =
      "Failed to start: " + (error && error.message ? error.message : error);
  }
  const details = document.getElementById("boot-log");
  if (details) details.open = true;
}

// ── Base path ─────────────────────────────────────────────────────────────────
// '/' for a user/org site, '/<repo>/' for a project site. Everything the app
// emits is rewritten against this so it works from a subdirectory.
const BASE = (() => {
  const p = window.location.pathname;
  return p.endsWith("/") ? p : p.replace(/[^/]*$/, "");
})();

function siteUrl(relPath) {
  return BASE + relPath.replace(/^\/+/, "");
}

/** Map a browser URL onto a request the Flask app understands, or null. */
function toDynamicPath(rawUrl) {
  let url;
  try {
    url = new URL(rawUrl, window.location.href);
  } catch {
    return null;
  }
  if (url.origin !== window.location.origin) return null;

  let path = url.pathname;
  if (BASE !== "/" && path.startsWith(BASE))
    path = "/" + path.slice(BASE.length);
  if (!path.startsWith("/")) path = "/" + path;
  if (!DYNAMIC_MARKERS.some((marker) => path.includes(marker))) return null;

  return path + url.search;
}

// ── Python bridge ─────────────────────────────────────────────────────────────
function base64ToBytes(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/** Ask the in-browser Flask app for a response. Returns {status, contentType, bytes}. */
function bridgeRequest(method, path, body) {
  const py = window.__bw.py;
  py.globals.set("__bw_method", method);
  py.globals.set("__bw_path", path);
  py.globals.set("__bw_body", body || "");

  let proxy;
  try {
    proxy = py.runPython("__bw_bridge(__bw_method, __bw_path, __bw_body)");
    const [status, contentType, bodyB64] = proxy.toJs({ depth: 1 });
    return { status, contentType, bytes: base64ToBytes(bodyB64) };
  } finally {
    if (proxy && proxy.destroy) proxy.destroy();
  }
}

function toResponse({ status, contentType, bytes }) {
  if (status >= 500) {
    console.error(
      `[borrow-watts] ${status} from the app:\n${new TextDecoder().decode(bytes)}`,
    );
  }
  return new Response(bytes, {
    status,
    headers: { "content-type": contentType || "application/octet-stream" },
  });
}

function interceptFetch() {
  window.fetch = function bridgedFetch(input, init) {
    const rawUrl =
      typeof input === "string"
        ? input
        : input instanceof Request
          ? input.url
          : String(input);
    const path = toDynamicPath(rawUrl);
    if (!path) return nativeFetch(input, init);

    const method = (
      (init && init.method) ||
      (input instanceof Request ? input.method : "GET") ||
      "GET"
    ).toUpperCase();

    const readBody = async () => {
      if (init && typeof init.body === "string") return init.body;
      if (input instanceof Request) return input.clone().text();
      return "";
    };

    return readBody()
      .then((body) => toResponse(bridgeRequest(method, path, body)))
      .catch((error) => new Response(String(error), { status: 500 }));
  };
}

function interceptXhr() {
  const proto = window.XMLHttpRequest.prototype;
  const originalOpen = proto.open;
  const originalSend = proto.send;

  proto.open = function bridgedOpen(method, url, ...rest) {
    this.__bwMethod = method;
    this.__bwUrl = url;
    return originalOpen.call(this, method, url, ...rest);
  };

  proto.send = function bridgedSend(body) {
    const path = toDynamicPath(this.__bwUrl);
    if (!path) return originalSend.call(this, body);

    const xhr = this;
    Promise.resolve()
      .then(() =>
        bridgeRequest(
          (xhr.__bwMethod || "GET").toUpperCase(),
          path,
          body || "",
        ),
      )
      .then(({ status, contentType, bytes }) => {
        const text = new TextDecoder().decode(bytes);
        Object.defineProperties(xhr, {
          readyState: { value: 4, configurable: true },
          status: { value: status, configurable: true },
          responseText: { value: text, configurable: true },
          response: {
            value: xhr.responseType === "arraybuffer" ? bytes.buffer : text,
            configurable: true,
          },
        });
        xhr.getAllResponseHeaders = () => `content-type: ${contentType}\r\n`;
        xhr.getResponseHeader = (name) =>
          String(name).toLowerCase() === "content-type" ? contentType : null;
        if (xhr.onreadystatechange) xhr.onreadystatechange();
        if (xhr.onload) xhr.onload();
        if (xhr.onloadend) xhr.onloadend();
      })
      .catch((error) => {
        if (xhr.onerror) xhr.onerror(error);
      });
  };
}

// ── Static asset staging ──────────────────────────────────────────────────────
async function writeFileIntoFs(py, fsPath, url) {
  const response = await nativeFetch(url);
  if (!response.ok)
    throw new Error(`cannot load ${url} (HTTP ${response.status})`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  py.FS.mkdirTree(fsPath.replace(/\/[^/]*$/, ""));
  py.FS.writeFile(fsPath, bytes);
  return bytes.length;
}

async function stagePythonSources(py, manifest, onProgress) {
  let count = 0;
  for (const rel of manifest.python) {
    await writeFileIntoFs(py, `/app/${rel}`, siteUrl(`py/${rel}`));
    count += 1;
    onProgress(count, manifest.python.length);
  }
}

async function stageZoneData(py, manifest, onProgress) {
  const dest = "/app/Agentics_Energy/agentic_energy/data/NYISO_zones";
  py.FS.mkdirTree(dest);
  let count = 0;
  await Promise.all(
    manifest.zones.map(async (zone) => {
      await writeFileIntoFs(
        py,
        `${dest}/${zone}.csv`,
        siteUrl(`data/NYISO_zones/${zone}.csv`),
      );
      count += 1;
      onProgress(count, manifest.zones.length);
    }),
  );
}

/**
 * Dash only emits a <link> for assets/* if the files exist in its assets
 * folder, and that folder is resolved relative to the app. Staging them into
 * the Pyodide filesystem is what makes assets/styles.css load; the bytes
 * themselves are served from the real static file.
 */
async function stageAppAssets(py, manifest) {
  if (!manifest.assets || !manifest.assets.length) return;
  py.FS.mkdirTree("/app/assets");
  for (const name of manifest.assets) {
    await writeFileIntoFs(py, `/app/assets/${name}`, siteUrl(`assets/${name}`));
  }
}

// ── Index HTML rewrite ────────────────────────────────────────────────────────
/**
 * Dash stamps a `<name>.v<version>m<mtime>.js` cache-buster onto every eager
 * suite URL. The static build ships those files under their plain names, and
 * the cache-buster is redundant here because the build is immutable, so the
 * token is stripped and the URL anchored to the site base.
 *
 * URLs that already carry the base are left anchored; ones that do not (the
 * pre-prefix form) get the base prepended.
 */
function toVendoredSuiteUrl(url) {
  const withoutMungeToken = url.replace(/\.v[^.]+?(?=\.)/, "");
  const path = withoutMungeToken.replace(/^[^/]*\/\//, "");
  if (path.startsWith(BASE)) return path;
  return BASE + path.replace(/^\/+/, "");
}

function rewriteIndexHtml(html) {
  let out = html.replace(
    /(["'])([^"']*\/_dash-component-suites\/[^"']+)\1/g,
    (_match, quote, url) => quote + toVendoredSuiteUrl(url) + quote,
  );

  out = out.replace(/(["'(])[^"')]*\/_favicon\.ico[^"')]*/g, "$1data:,");

  // /assets/... must resolve inside the deployed subdirectory, not the domain
  // root. With requests_pathname_prefix set, dash already emits the base, so
  // this only catches the paths app.py hard-codes.
  out = out.replace(/(["'(])\/assets\//g, `$1${BASE}assets/`);

  return out;
}

// ── Boot ──────────────────────────────────────────────────────────────────────
async function boot() {
  stage(3, "Reading build manifest…");
  const runtime = await nativeFetch(RUNTIME_CONFIG_URL).then((response) => {
    if (!response.ok)
      throw new Error("runtime.json is missing — run tools/export_static.py");
    return response.json();
  });
  const pyodideIndex = runtime.pyodideIndex;

  stage(6, "Loading Python runtime…", pyodideIndex.split("/pyodide/")[1] || "");
  const { loadPyodide } = await import(`${pyodideIndex}pyodide.mjs`);
  const py = await loadPyodide({ indexURL: pyodideIndex });
  window.__bw = { py, BASE };

  py.setStdout({ batched: (line) => log("py: " + line) });
  py.setStderr({ batched: (line) => log("py! " + line) });

  stage(12, "Preparing package installer…");
  await py.loadPackage("micropip");

  stage(
    18,
    "Downloading dash, scipy, pandas, plotly…",
    "one-time, then cached",
  );
  await py.runPythonAsync(`
import micropip
await micropip.install(${JSON.stringify(runtime.packages)})
`);

  stage(48, "Loading application sources…");
  const manifest = await nativeFetch(siteUrl("py/manifest.json")).then((r) => {
    if (!r.ok)
      throw new Error(
        "py/manifest.json is missing — run tools/export_static.py",
      );
    return r.json();
  });
  await stagePythonSources(py, manifest, (done, total) => {
    stage(
      48 + Math.round((done / total) * 22),
      "Loading application sources…",
      `${done}/${total} modules`,
    );
  });

  stage(72, "Loading NYISO zone data…");
  await stageZoneData(py, manifest, (done, total) => {
    stage(
      72 + Math.round((done / total) * 6),
      "Loading NYISO zone data…",
      `${done}/${total} zones`,
    );
  });

  stage(79, "Loading assets…");
  await stageAppAssets(py, manifest);

  stage(82, "Starting the application…");
  py.globals.set("__bw_base", BASE);
  await py.runPythonAsync(
    await nativeFetch(siteUrl("py/boot_app.py")).then((r) => r.text()),
  );

  stage(92, "Rendering interface…");
  const indexHtml = bridgeRequest("GET", "/", "").bytes;
  const rewritten = rewriteIndexHtml(new TextDecoder().decode(indexHtml));

  interceptFetch();
  interceptXhr();

  log("handing over to dash-renderer");
  document.open();
  document.write(rewritten);
  document.close();
}

boot().catch(fail);
