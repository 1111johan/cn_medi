function parseCsv(input) {
  if (!input) return [];
  return input
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

function escapeHtml(input) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return String(input).replace(/[&<>"']/g, (m) => map[m]);
}

function badgeClassByStatus(status) {
  if (status === "healthy" || status === "running" || status === "completed") return "ok";
  if (status === "watch" || status === "in_progress") return "watch";
  return "risk";
}

function resolveApiUrl(url) {
  const rawBase = String(window.__TCM_API_BASE__ || "").trim();
  const value = String(url);

  if (/^https?:\/\//i.test(value)) {
    return url;
  }

  const suffix = value.startsWith("/") ? value : `/${value}`;
  const isLocalHost = /^(127\.0\.0\.1|localhost)$/i.test(window.location.hostname);
  const isBackendHost = isLocalHost && (window.location.port === "8000" || window.location.port === "");

  if (rawBase) {
    const base = rawBase.replace(/\/+$/, "");
    return `${base}${suffix}`;
  }

  // Local static pages (Vite dev/preview) should call FastAPI directly.
  if (isLocalHost && !isBackendHost) {
    return `http://127.0.0.1:8000${suffix}`;
  }

  // FastAPI local pages are served on same origin.
  if (isBackendHost) {
    return suffix;
  }

  // Production static deployment (Vercel): API is exposed under /api/*.
  return `/api${suffix}`;
}

async function fetchJson(url, options = {}) {
  const finalUrl = resolveApiUrl(url);
  const response = await fetch(finalUrl, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return {};
  }

  const contentType = String(response.headers.get("content-type") || "").toLowerCase();
  if (!contentType.includes("application/json")) {
    const preview = (await response.text().catch(() => "")).replace(/\s+/g, " ").slice(0, 120);
    throw new Error(
      `API返回非JSON响应(${response.status})${preview ? `: ${preview}` : ""}，请求地址=${finalUrl}`
    );
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail ? JSON.stringify(data.detail, null, 2) : `HTTP ${response.status}`);
  }
  return data;
}

function renderJson(node, data) {
  node.textContent = JSON.stringify(data, null, 2);
}

function renderError(node, error) {
  node.textContent = `请求失败: ${String(error)}`;
}

async function initGlobalHealth() {
  const chip = document.getElementById("api-health-chip");
  if (!chip) return;

  try {
    await fetchJson("/health");
    chip.textContent = "API: online";
    chip.className = "status-chip";
  } catch (error) {
    chip.textContent = "API: offline";
    chip.className = "status-chip risk";
  }
}

function debounce(fn, delay = 260) {
  let timer = null;
  return (...args) => {
    if (timer) {
      clearTimeout(timer);
    }
    timer = setTimeout(() => fn(...args), delay);
  };
}

function ensureGlobalSearchPanel() {
  const input = document.getElementById("global-search");
  if (!input) return null;

  let panel = document.getElementById("global-search-results");
  if (!panel) {
    panel = document.createElement("div");
    panel.id = "global-search-results";
    panel.className = "global-search-results";
    panel.hidden = true;
    input.closest(".global-search-wrap")?.appendChild(panel);
  }
  return panel;
}

function toFrontendRoute(route) {
  const routeMap = {
    "/": "/index.html",
    "/workbench/clinical": "/clinical.html",
    "/clinical": "/clinical.html",
    "/workbench/research": "/research.html",
    "/research": "/research.html",
    "/workbench/smart-qa": "/smart-qa.html",
    "/smart-qa": "/smart-qa.html",
    "/qa-assistant": "/smart-qa.html",
    "/workbench/rnd": "/rnd.html",
    "/rnd": "/rnd.html",
    "/middle/knowledge": "/knowledge-center.html",
    "/knowledge": "/knowledge-center.html",
    "/middle/reasoning": "/reasoning-center.html",
    "/reasoning": "/reasoning-center.html",
    "/review/expert": "/expert-review.html",
    "/expert-review": "/expert-review.html",
    "/governance/operations": "/operations.html",
    "/operations": "/operations.html",
  };
  return routeMap[String(route || "").trim()] || route || "#";
}

function renderGlobalSearchResult(panel, payload) {
  const results = payload.results || [];
  if (!results.length) {
    panel.innerHTML = "<div class='search-empty'>未找到匹配结果</div>";
    panel.hidden = false;
    return;
  }

  panel.innerHTML = results
    .map(
      (item) => `
      <a class="search-item" href="${escapeHtml(toFrontendRoute(item.route))}">
        <div class="search-item-head">
          <span class="search-title">${escapeHtml(item.title || "")}</span>
          <span class="search-category">${escapeHtml(item.category || "")}</span>
        </div>
        <div class="search-snippet">${escapeHtml(item.snippet || "")}</div>
        <div class="search-source">${escapeHtml(item.source || "")}</div>
      </a>
    `
    )
    .join("");
  panel.hidden = false;
}

function initGlobalSearch() {
  const input = document.getElementById("global-search");
  const panel = ensureGlobalSearchPanel();
  if (!input || !panel) return;

  const onInput = debounce(async () => {
    const q = input.value.trim();
    if (q.length < 2) {
      panel.hidden = true;
      return;
    }
    panel.innerHTML = "<div class='search-empty'>搜索中...</div>";
    panel.hidden = false;
    try {
      const result = await fetchJson(`/platform/global-search?q=${encodeURIComponent(q)}&top_k=14`);
      renderGlobalSearchResult(panel, result);
    } catch (error) {
      panel.innerHTML = `<div class='search-empty'>搜索失败: ${escapeHtml(String(error))}</div>`;
      panel.hidden = false;
    }
  }, 220);

  input.addEventListener("input", onInput);
  input.addEventListener("focus", onInput);

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.closest(".global-search-wrap")) return;
    panel.hidden = true;
  });
}

window.tcmApi = {
  parseCsv,
  escapeHtml,
  badgeClassByStatus,
  fetchJson,
  renderJson,
  renderError,
};

initGlobalHealth();
initGlobalSearch();
