const typeListNode = document.getElementById("kc-type-list");
const objectListNode = document.getElementById("kc-object-list");
const detailNode = document.getElementById("kc-object-detail");
const sourceBreakdownNode = document.getElementById("kc-source-breakdown");
const ingestForm = document.getElementById("kc-ingest-form");
const ingestResult = document.getElementById("kc-ingest-result");
const refreshBtn = document.getElementById("kc-refresh");

let allObjects = [];
let activeType = "all";

if (typeListNode) {
  typeListNode.addEventListener("click", (event) => {
    const target = event.target.closest("button[data-type]");
    if (!target) return;

    typeListNode.querySelectorAll("button").forEach((btn) => btn.classList.remove("active"));
    target.classList.add("active");

    activeType = target.dataset.type || "all";
    document.getElementById("kc-active-type").textContent = target.textContent.trim();
    renderObjectList();
  });
}

if (refreshBtn) {
  refreshBtn.addEventListener("click", async () => {
    await Promise.all([loadObjects(), loadDashboardSummary(), loadProfessionalStats()]);
  });
}

if (ingestForm) {
  ingestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    ingestResult.textContent = "处理中...";

    const formData = new FormData(ingestForm);
    const payload = {
      source_type: formData.get("source_type"),
      title: formData.get("title"),
      content: formData.get("content"),
      tags: window.tcmApi.parseCsv(formData.get("tags")),
      metadata: {
        module: "knowledge_center",
      },
    };

    try {
      const result = await window.tcmApi.fetchJson("/knowledge/ingest", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(ingestResult, result);
      ingestForm.reset();
      await Promise.all([loadObjects(), loadDashboardSummary()]);
    } catch (error) {
      window.tcmApi.renderError(ingestResult, error);
    }
  });
}

async function loadObjects() {
  objectListNode.innerHTML = "<div class='result-box'>加载中...</div>";
  try {
    allObjects = await window.tcmApi.fetchJson("/knowledge/list?limit=200");
    document.getElementById("kc-knowledge-count").textContent = allObjects.length;
    renderObjectList();
  } catch (error) {
    objectListNode.innerHTML = `<div class='result-box'>加载失败: ${String(error)}</div>`;
  }
}

function renderObjectList() {
  const filtered = allObjects.filter((item) => matchType(item, activeType));

  if (!filtered.length) {
    objectListNode.innerHTML = "<div class='result-box'>当前类型下暂无对象。</div>";
    detailNode.textContent = "请选择左侧对象查看详情。";
    return;
  }

  objectListNode.innerHTML = filtered
    .map(
      (item) => `
      <button class="queue-item" data-id="${item.object_id}">
        ${window.tcmApi.escapeHtml(item.title)}
        <br><small>${window.tcmApi.escapeHtml(item.source_type)} · ${(item.tags || []).join("/")}</small>
      </button>
    `
    )
    .join("");

  objectListNode.querySelectorAll("button[data-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const obj = filtered.find((x) => x.object_id === btn.dataset.id);
      if (!obj) return;
      objectListNode.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderObjectDetail(obj);
    });
  });

  renderObjectDetail(filtered[0]);
  objectListNode.querySelector("button[data-id]")?.classList.add("active");
}

function renderObjectDetail(obj) {
  detailNode.innerHTML = `
    <strong>标题</strong>：${window.tcmApi.escapeHtml(obj.title)}<br>
    <strong>类型</strong>：${window.tcmApi.escapeHtml(obj.source_type)}<br>
    <strong>标签</strong>：${window.tcmApi.escapeHtml((obj.tags || []).join("、") || "无")}<br>
    <strong>创建时间</strong>：${window.tcmApi.escapeHtml(obj.created_at || "")}
    <hr>
    <strong>内容摘要</strong><br>
    ${window.tcmApi.escapeHtml(obj.content || "").slice(0, 600)}
  `;
}

function matchType(item, type) {
  if (type === "all") return true;
  if (type === "syndrome") return hasAnyToken(item, ["证候", "病机"]);
  if (type === "therapy") return hasAnyToken(item, ["治法"]);
  if (type === "formula") return item.source_type === "formula" || hasAnyToken(item, ["方剂", "方药"]);
  if (type === "herb") return item.source_type === "herb" || hasAnyToken(item, ["药材", "中药"]);
  if (type === "classic") return item.source_type === "classic";
  if (type === "case") return item.source_type === "case" || hasAnyToken(item, ["医案"]);
  if (type === "guideline") return item.source_type === "guideline";
  if (type === "paper") return item.source_type === "paper";
  if (type === "symptom") return hasAnyToken(item, ["症状", "主诉", "体征"]);
  return true;
}

function hasAnyToken(item, tokens) {
  const text = `${item.title || ""} ${(item.content || "").slice(0, 200)} ${(item.tags || []).join(" ")}`;
  return tokens.some((t) => text.includes(t));
}

async function loadDashboardSummary() {
  try {
    const dashboard = await window.tcmApi.fetchJson("/platform/dashboard");
    renderSourceBreakdown(dashboard.source_breakdown || {}, dashboard.core_metrics?.knowledge_count || 1);
  } catch (error) {
    sourceBreakdownNode.innerHTML = `<div class='result-box'>加载失败: ${String(error)}</div>`;
  }
}

function renderSourceBreakdown(map, total) {
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    sourceBreakdownNode.innerHTML = "<div class='result-box'>暂无统计。</div>";
    return;
  }

  sourceBreakdownNode.innerHTML = entries
    .map(([k, v]) => {
      const pct = Math.round((v / total) * 100);
      return `
      <div class="stack-item">
        <div class="stack-title"><span>${window.tcmApi.escapeHtml(k)}</span><span>${v}</span></div>
        <div class="progress-wrap"><div class="progress-bar" style="width:${pct}%"></div></div>
      </div>
    `;
    })
    .join("");
}

async function loadProfessionalStats() {
  try {
    const stats = await window.tcmApi.fetchJson("/knowledge/professional/stats");
    document.getElementById("kc-prof-count").textContent = stats.record_count || 0;
  } catch (error) {
    document.getElementById("kc-prof-count").textContent = "-";
  }
}

Promise.all([loadObjects(), loadDashboardSummary(), loadProfessionalStats()]);
