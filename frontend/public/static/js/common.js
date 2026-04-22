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

function isStaticReadonlyMode() {
  return Boolean(window.__TCM_STATIC_READONLY__);
}

function getStaticDataRoot() {
  return String(window.__TCM_STATIC_DATA_ROOT__ || "/api-static").replace(/\/+$/, "");
}

function normalizePathname(pathname) {
  const clean = String(pathname || "").replace(/\/+$/, "");
  if (!clean) return "/";
  return clean.startsWith("/api/") ? clean.slice(4) || "/" : clean;
}

function tokenizeSearchQuery(query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return [];
  const rawTerms = q.split(/[\s,，。；;、/]+/).filter(Boolean);
  const terms = [q, ...rawTerms];
  return [...new Set(terms.filter(Boolean))];
}

function scoreSearchText(query, haystack) {
  const text = String(haystack || "").toLowerCase();
  if (!text) return 0;
  const terms = tokenizeSearchQuery(query);
  if (!terms.length) return 0;

  let score = 0;
  terms.forEach((term, idx) => {
    if (!term) return;
    if (text.includes(term)) {
      score += idx === 0 ? 8 : 2;
    }
  });
  return score;
}

function createSnippet(text, query, fallbackLength = 120) {
  const content = String(text || "");
  if (!content) return "";
  const q = String(query || "").trim();
  if (!q) return content.slice(0, fallbackLength);

  const idx = content.indexOf(q);
  if (idx < 0) return content.slice(0, fallbackLength);

  const start = Math.max(0, idx - Math.floor(fallbackLength / 2));
  return content.slice(start, start + fallbackLength);
}

function parseRequestTarget(url) {
  const parsed = new URL(String(url), window.location.origin);
  return {
    pathname: normalizePathname(parsed.pathname),
    searchParams: parsed.searchParams,
  };
}

function getStaticSnapshotFile(pathname) {
  const root = getStaticDataRoot();
  const path = normalizePathname(pathname);

  const directMap = {
    "/health": `${root}/health.json`,
    "/platform/dashboard": `${root}/platform/dashboard.json`,
    "/platform/global-search": `${root}/platform/global-search.json`,
    "/knowledge/list": `${root}/knowledge/list.json`,
    "/knowledge/search": `${root}/knowledge/search.json`,
    "/knowledge/professional/stats": `${root}/knowledge/professional/stats.json`,
    "/knowledge/professional/search": `${root}/knowledge/professional/search.json`,
    "/governance/audit": `${root}/governance/audit.json`,
    "/governance/rules": `${root}/governance/rules.json`,
    "/review/tasks": `${root}/review/tasks.json`,
    "/smart-qa/scenarios": `${root}/smart-qa/scenarios.json`,
  };

  if (directMap[path]) {
    return directMap[path];
  }

  if (/^\/review\/tasks\/[^/]+$/.test(path)) {
    return `${root}/review/tasks.json`;
  }

  return "";
}

function withLimitedList(items, searchParams, key = "limit", defaultLimit = items.length) {
  const limit = Number.parseInt(searchParams.get(key) || "", 10);
  const safeLimit = Number.isFinite(limit) && limit > 0 ? limit : defaultLimit;
  return items.slice(0, safeLimit);
}

function applyStaticReviewTasks(data, pathname, searchParams) {
  const payload = data || {};
  let tasks = Array.isArray(payload.tasks) ? payload.tasks.slice() : [];

  const status = String(searchParams.get("status") || "").trim();
  const taskType = String(searchParams.get("task_type") || "").trim();
  const priority = String(searchParams.get("priority") || "").trim();

  if (status) tasks = tasks.filter((item) => String(item.status || "") === status);
  if (taskType) tasks = tasks.filter((item) => String(item.task_type || "") === taskType);
  if (priority) tasks = tasks.filter((item) => String(item.priority || "") === priority);

  if (/^\/review\/tasks\/[^/]+$/.test(pathname)) {
    const taskId = pathname.split("/").pop();
    return tasks.find((item) => String(item.task_id || "") === String(taskId || "")) || null;
  }

  return {
    tasks: withLimitedList(tasks, searchParams),
    stats: payload.stats || {},
  };
}

function applyStaticAudit(data, searchParams) {
  let items = Array.isArray(data) ? data.slice() : [];
  const actor = String(searchParams.get("actor") || "").trim();
  const eventType = String(searchParams.get("event_type") || "").trim();

  if (actor) items = items.filter((item) => String(item.actor || "") === actor);
  if (eventType) items = items.filter((item) => String(item.event_type || "") === eventType);

  return withLimitedList(items, searchParams);
}

function applyStaticKnowledgeList(data, searchParams) {
  const items = Array.isArray(data) ? data.slice() : [];
  return withLimitedList(items, searchParams);
}

function applyStaticKnowledgeSearch(data, searchParams) {
  const query = String(searchParams.get("q") || "").trim();
  const topK = Number.parseInt(searchParams.get("top_k") || "", 10);
  const limit = Number.isFinite(topK) && topK > 0 ? topK : 10;
  const items = Array.isArray(data?.items) ? data.items : [];

  if (!query) return [];

  return items
    .map((item) => {
      const haystack = [item.title, item.content, (item.tags || []).join(" "), item.source_type].join(" ");
      const score = scoreSearchText(query, haystack);
      return {
        ...item,
        score: Number((score / 10).toFixed(3)),
        snippet: createSnippet(item.content || "", query),
      };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

function applyStaticProfessionalSearch(data, searchParams) {
  const query = String(searchParams.get("q") || "").trim();
  const topK = Number.parseInt(searchParams.get("top_k") || "", 10);
  const limit = Number.isFinite(topK) && topK > 0 ? topK : 10;
  const items = Array.isArray(data?.results) ? data.results : [];

  if (!query) return { query, results: [] };

  const results = items
    .map((item) => {
      const haystack = [item.title, item.content, item.snippet, item.source_path].join(" ");
      const score = scoreSearchText(query, haystack);
      return {
        ...item,
        score: Number((score / 10).toFixed(3)),
        snippet: createSnippet(item.content || item.snippet || "", query),
      };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  return { query, results };
}

function applyStaticGlobalSearch(data, searchParams) {
  const query = String(searchParams.get("q") || "").trim();
  const topK = Number.parseInt(searchParams.get("top_k") || "", 10);
  const limit = Number.isFinite(topK) && topK > 0 ? topK : 14;
  const items = Array.isArray(data?.results) ? data.results : [];

  if (!query) {
    return { query, total: 0, results: [] };
  }

  const results = items
    .map((item) => {
      const haystack = [item.title, item.snippet, item.source, item.category].join(" ");
      return {
        ...item,
        score: scoreSearchText(query, haystack),
      };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(({ score, ...rest }) => rest);

  return {
    query,
    total: results.length,
    results,
  };
}

function adaptStaticPayload(pathname, data, searchParams) {
  const path = normalizePathname(pathname);
  if (path === "/knowledge/list") return applyStaticKnowledgeList(data, searchParams);
  if (path === "/knowledge/search") return applyStaticKnowledgeSearch(data, searchParams);
  if (path === "/knowledge/professional/search") return applyStaticProfessionalSearch(data, searchParams);
  if (path === "/platform/global-search") return applyStaticGlobalSearch(data, searchParams);
  if (path === "/governance/audit") return applyStaticAudit(data, searchParams);
  if (path === "/review/tasks" || /^\/review\/tasks\/[^/]+$/.test(path)) {
    return applyStaticReviewTasks(data, path, searchParams);
  }
  return data;
}

async function fetchStaticSnapshot(url) {
  const { pathname, searchParams } = parseRequestTarget(url);
  const snapshotFile = getStaticSnapshotFile(pathname);
  if (!snapshotFile) {
    throw new Error(`static_snapshot_not_found:${pathname}`);
  }

  const response = await fetch(snapshotFile, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`静态数据加载失败: HTTP ${response.status}`);
  }

  const data = await response.json();
  return adaptStaticPayload(pathname, data, searchParams);
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
  const method = String(options.method || "GET").toUpperCase();
  const staticFile = getStaticSnapshotFile(parseRequestTarget(url).pathname);

  if (isStaticReadonlyMode() && method === "GET" && staticFile) {
    return fetchStaticSnapshot(url);
  }

  if (isStaticReadonlyMode() && method !== "GET") {
    throw new Error("当前部署为静态展示版，该操作需要后端 API 或函数版支持。");
  }

  const finalUrl = resolveApiUrl(url);
  let response;
  try {
    response = await fetch(finalUrl, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch (error) {
    if (method === "GET" && staticFile) {
      return fetchStaticSnapshot(url);
    }
    throw error;
  }

  if (response.status === 204) {
    return {};
  }

  if (!response.ok && method === "GET" && staticFile && [404, 500, 502, 503, 504].includes(response.status)) {
    return fetchStaticSnapshot(url);
  }

  const contentType = String(response.headers.get("content-type") || "").toLowerCase();
  if (!contentType.includes("application/json")) {
    if (method === "GET" && staticFile) {
      return fetchStaticSnapshot(url);
    }
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
    const result = await fetchJson("/health");
    chip.textContent = result?.mode === "static_snapshot" ? "数据: static" : "API: online";
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
