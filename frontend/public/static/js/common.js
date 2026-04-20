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
  if (!rawBase || /^https?:\/\//i.test(String(url))) {
    return url;
  }

  const base = rawBase.replace(/\/+$/, "");
  const suffix = String(url).startsWith("/") ? String(url) : `/${String(url)}`;
  return `${base}${suffix}`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(resolveApiUrl(url), {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

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
      <a class="search-item" href="${escapeHtml(item.route || "#")}">
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
