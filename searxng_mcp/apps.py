"""SearXNG MCP App: an interactive search-UI panel (`ui://searxng-mcp/search.html`).

CONCEPT:SR-ECO.ui.mcp-app-frontend

Renders a small, self-contained search interface — a query box, category
filters, and a clickable results list — so a human (or an agent-facing host
that renders MCP Apps, per the ``io.modelcontextprotocol/ui`` extension
already advertised by fastmcp 4) gets an actual visual, interactive search
experience instead of raw JSON. It follows the exact same shape as
``agent_utilities.mcp.tools.mcp_apps`` (``graph_task_progress_app`` /
``graph_trace_waterfall_app``): an entry-point tool whose result carries
``_meta.ui.resourceUri``, plus the ``ui://`` HTML resource itself, wired
through the SAME host-mediated postMessage bridge (``mcpapp/ready`` ->
``mcpapp/init`` -> ``mcpapp/tool-call`` -> ``mcpapp/tool-result`` |
``mcpapp/tool-error``) that ``agent-webui``'s bridge already implements. The
app never gets its own network access or a direct handle to the running
instance — every search goes back through the host to the ordinary
``web_search`` tool this server already exposes, so it inherits that tool's
existing resolution order (explicit config -> embedded -> random public ->
``searx.be``), KG ingestion, and auth/policy posture for free.

**Deliberately scoped — this is a search-UI app, not a browser.** It does
NOT: drive a headless browser, execute script on or scrape arbitrary third-
party pages, take screenshots, hold cookies/sessions, or navigate anywhere
except through ``web_search``. Clicking a result opens the target site in the
user's own browser tab (a plain ``<a target="_blank">``, subject to whatever
sandbox/popup policy the host's iframe grants) — the app itself never fetches
or renders that page's content. Rendering SearXNG's OWN Flask/Jinja HTML
templates is a different, heavier feature (would need the embedded instance's
loopback bind reachable from the end user's browser, which the privacy
posture in ``embedded/settings.yml`` deliberately does not allow) and is out
of scope here; this reimplements the same query/filter/results workflow
against the existing ``web_search`` tool instead.
"""

from __future__ import annotations

from typing import Any

from agent_utilities.core.config import setting
from pydantic import Field

SEARCH_APP_RESOURCE_URI = "ui://searxng-mcp/search.html"

# Self-contained: no external script/style/font/image loads beyond the result
# links a user explicitly clicks, so the CSP this app needs is the empty set
# (no connect/resource/frame domains) -- the strictest possible declaration.
# The host still decides what it actually grants.
_SEARCH_APP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>SearXNG Search</title>
<style>
  body { font: 13px system-ui, sans-serif; margin: 12px; color: #1a1a1a; }
  #bar { display: flex; gap: 6px; margin-bottom: 10px; }
  #q { flex: 1; padding: 6px 8px; font-size: 13px; }
  button { padding: 6px 10px; font-size: 13px; cursor: pointer; }
  #cats { margin-bottom: 10px; color: #444; }
  #cats label { margin-right: 10px; }
  .result { margin-bottom: 12px; }
  .result a.title { font-size: 14px; color: #1a0dab; text-decoration: none; }
  .result a.title:hover { text-decoration: underline; }
  .result .url { color: #006621; font-size: 12px; }
  .result .content { color: #444; font-size: 12px; }
  #pager { margin-top: 10px; }
  #err { color: #991b1b; margin-top: 8px; }
  #status { color: #666; margin-bottom: 8px; }
</style>
</head>
<body>
  <div id="bar">
    <input id="q" type="text" placeholder="Search the web...">
    <button id="go">Search</button>
  </div>
  <div id="cats">
    <label><input type="checkbox" value="general" checked> general</label>
    <label><input type="checkbox" value="news"> news</label>
    <label><input type="checkbox" value="images"> images</label>
    <label><input type="checkbox" value="it"> it</label>
    <label><input type="checkbox" value="science"> science</label>
  </div>
  <div id="status"></div>
  <div id="results"></div>
  <div id="pager" hidden><button id="more">More results</button></div>
  <div id="err" hidden></div>
<script>
(function () {
  "use strict";
  // Bridge protocol (see apps.py / agent-webui bridge.ts docstrings):
  //   iframe -> host: {type: "mcpapp/ready"}
  //   host -> iframe: {type: "mcpapp/init", props: {query}}
  //   iframe -> host: {type: "mcpapp/tool-call", id, name, arguments}
  //   host -> iframe: {type: "mcpapp/tool-result", id, result}
  //                 | {type: "mcpapp/tool-error", id, error: {message}}
  var pending = Object.create(null);
  var seq = 0;
  var pageno = 1;

  function post(message) {
    window.parent.postMessage(message, "*");
  }

  function callTool(name, args) {
    var id = "call-" + (++seq);
    return new Promise(function (resolve, reject) {
      pending[id] = { resolve: resolve, reject: reject };
      post({ type: "mcpapp/tool-call", id: id, name: name, arguments: args });
    });
  }

  window.addEventListener("message", function (event) {
    var data = event.data;
    if (!data || typeof data !== "object") return;
    if (data.type === "mcpapp/init") {
      var q = (data.props && data.props.query) || "";
      document.getElementById("q").value = q;
      if (q) search(false);
      return;
    }
    if (data.type === "mcpapp/tool-result" && pending[data.id]) {
      pending[data.id].resolve(data.result);
      delete pending[data.id];
      return;
    }
    if (data.type === "mcpapp/tool-error" && pending[data.id]) {
      pending[data.id].reject(new Error((data.error && data.error.message) || "tool error"));
      delete pending[data.id];
    }
  });

  function showError(message) {
    var el = document.getElementById("err");
    el.hidden = !message;
    el.textContent = message || "";
  }

  function selectedCategories() {
    var boxes = document.querySelectorAll("#cats input[type=checkbox]:checked");
    return Array.prototype.map.call(boxes, function (b) { return b.value; });
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s || "";
    return div.innerHTML;
  }

  function render(data, append) {
    var el = document.getElementById("results");
    if (!append) el.innerHTML = "";
    var results = (data && data.results) || [];
    document.getElementById("status").textContent =
      results.length ? "" : (append ? "No more results." : "No results.");
    results.forEach(function (r) {
      var div = document.createElement("div");
      div.className = "result";
      div.innerHTML =
        '<div><a class="title" target="_blank" rel="noopener noreferrer" href="' +
          escapeHtml(r.url || "#") + '">' + escapeHtml(r.title || r.url || "") + "</a></div>" +
        '<div class="url">' + escapeHtml(r.url || "") + "</div>" +
        '<div class="content">' + escapeHtml(r.content || "") + "</div>";
      el.appendChild(div);
    });
    document.getElementById("pager").hidden = results.length === 0;
  }

  function search(append) {
    var q = document.getElementById("q").value.trim();
    if (!q) return;
    showError("");
    if (!append) {
      pageno = 1;
      document.getElementById("status").textContent = "Searching...";
    } else {
      pageno += 1;
    }
    callTool("web_search", {
      query: q,
      categories: selectedCategories(),
      pageno: pageno,
    })
      .then(function (result) {
        var parsed = typeof result === "string" ? JSON.parse(result) : result;
        if (parsed && parsed.error) { showError(parsed.error); return; }
        render(parsed, append);
      })
      .catch(function (err) { showError(String(err && err.message || err)); });
  }

  document.getElementById("go").addEventListener("click", function () { search(false); });
  document.getElementById("q").addEventListener("keydown", function (e) {
    if (e.key === "Enter") search(false);
  });
  document.getElementById("more").addEventListener("click", function () { search(true); });

  post({ type: "mcpapp/ready" });
})();
</script>
</body>
</html>
"""


def register_search_app_tools(mcp: Any) -> None:
    """Register the search-app entry-point tool + its ``ui://`` HTML resource,
    unless disabled via ``SEARCH_APPTOOL`` (the framework's auto-derived
    ``register_<tag>_tools`` -> ``<TAG>TOOL`` toggle convention)."""
    if not bool(setting("SEARCH_APPTOOL", True)):
        return

    from fastmcp.apps.config import AppConfig, ResourceCSP, ResourcePermissions

    @mcp.tool(
        name="searxng_search_app",
        description=(
            "Launch an interactive SearXNG search-UI app: a query box, "
            "category filters, and a clickable results list, backed by the "
            "existing web_search tool through the host-mediated MCP Apps "
            "bridge. Use this when a human should see and interact with "
            "search results visually rather than read raw JSON. Does NOT "
            "drive a browser or render arbitrary web pages -- only this "
            "search workflow."
        ),
        tags=["searxng", "search_app", "mcp-apps"],
        app=AppConfig(
            resource_uri=SEARCH_APP_RESOURCE_URI,
            visibility=["model"],
            csp=ResourceCSP(),
            permissions=ResourcePermissions(),
        ),
    )
    async def searxng_search_app(
        query: str = Field(
            default="", description="Optional initial query to run on load."
        ),
    ) -> dict[str, Any]:
        return {"query": query}

    # Wrapped defensively, matching mcp_apps.py's own registration: some unit
    # tests build a server against a minimal FastMCP test double that only
    # implements `.tool()`, not `.resource()`. A real FastMCP always has it.
    resource = getattr(mcp, "resource", None)
    if callable(resource):

        @resource(
            uri=SEARCH_APP_RESOURCE_URI,
            name="SearXNG Search",
            description="Interactive search UI backed by the web_search tool.",
            mime_type="text/html",
        )
        async def search_app_resource() -> str:
            return _SEARCH_APP_HTML
