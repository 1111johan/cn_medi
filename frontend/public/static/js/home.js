const ingestForm = document.getElementById("ingest-form");
const ingestResult = document.getElementById("ingest-result");

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
      metadata: {},
    };

    try {
      const result = await window.tcmApi.fetchJson("/knowledge/ingest", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(ingestResult, result);
      ingestForm.reset();
      await loadDashboard();
    } catch (error) {
      window.tcmApi.renderError(ingestResult, error);
    }
  });
}

async function loadDashboard() {
  try {
    const dashboard = await window.tcmApi.fetchJson("/platform/dashboard");
    const core = dashboard.core_metrics || {};

    setText("metric-knowledge", core.knowledge_count || 0);
    setText("metric-professional", core.professional_record_count || 0);
    setText("metric-feedback", core.feedback_count || 0);
    setText("metric-audit", core.audit_count || 0);
    setText("metric-clinical-loop", core.clinical_closed_loops || 0);
    setText("metric-trace", `${core.evidence_trace_ratio || 0}%`);
    setText("metric-adoption", `${core.adoption_ratio || 0}%`);

    const scenario = dashboard.scenario_metrics || {};
    setText("metric-clinical-events", scenario.clinical_events || 0);
    setText("metric-research-events", scenario.research_events || 0);
    setText("metric-rnd-events", scenario.rnd_events || 0);
    setText("metric-smart-qa-events", scenario.smart_qa_events || 0);

    renderArchitecture(dashboard.architecture || []);
    renderLoops(Object.values(dashboard.loops || {}));
    renderRoadmap(dashboard.roadmap || []);
    renderTaskQueue(dashboard.task_queue || []);
    renderSourceBreakdown(dashboard.source_breakdown || {}, core.knowledge_count || 1);
    renderRecentAudits(dashboard.recent_audits || []);
    renderTrends(core, scenario);
    await loadPendingReviews();
  } catch (error) {
    const target = document.getElementById("task-queue");
    if (target) target.textContent = `看板加载失败: ${String(error)}`;
  }
}

function renderArchitecture(items) {
  const node = document.getElementById("architecture-list");
  if (!node) return;

  node.innerHTML = items
    .map(
      (item) => `
      <div class="stack-item">
        <div class="stack-title">
          <span>${window.tcmApi.escapeHtml(item.name)}</span>
          <span class="badge ${window.tcmApi.badgeClassByStatus(item.status)}">${window.tcmApi.escapeHtml(item.status)}</span>
        </div>
        <div class="stack-desc">${window.tcmApi.escapeHtml(item.desc || "")}</div>
      </div>
    `
    )
    .join("");
}

function renderLoops(items) {
  const node = document.getElementById("loop-list");
  if (!node) return;

  node.innerHTML = items
    .map((item) => {
      const statusClass = window.tcmApi.badgeClassByStatus(item.status);
      return `
      <div class="stack-item">
        <div class="stack-title">
          <span>${window.tcmApi.escapeHtml(item.name)}</span>
          <span class="badge ${statusClass}">${window.tcmApi.escapeHtml(item.progress)}%</span>
        </div>
        <div class="stack-desc">${window.tcmApi.escapeHtml(item.desc || "")}</div>
        <div class="progress-wrap"><div class="progress-bar ${statusClass}" style="width:${item.progress}%"></div></div>
      </div>
    `;
    })
    .join("");
}

function renderRoadmap(items) {
  const node = document.getElementById("roadmap-list");
  if (!node) return;

  node.innerHTML = items
    .map(
      (item) => `
      <div class="roadmap-item">
        <div class="task-head">
          <span>${window.tcmApi.escapeHtml(item.phase)}</span>
          <span class="badge ${window.tcmApi.badgeClassByStatus(item.status)}">${window.tcmApi.escapeHtml(item.status)}</span>
        </div>
        <p>${window.tcmApi.escapeHtml(item.goal)}</p>
        <p>交付：${window.tcmApi.escapeHtml(item.deliverables)}</p>
      </div>
    `
    )
    .join("");
}

function renderTaskQueue(items) {
  const node = document.getElementById("task-queue");
  if (!node) return;

  node.innerHTML = items
    .map(
      (item) => `
      <div class="task-item">
        <div class="task-head">
          <span>${window.tcmApi.escapeHtml(item.owner)} · ${window.tcmApi.escapeHtml(item.title)}</span>
          <span class="prio ${(item.priority || "P1").toLowerCase()}">${window.tcmApi.escapeHtml(item.priority || "P1")}</span>
        </div>
        <p>${window.tcmApi.escapeHtml(item.detail || "")}</p>
      </div>
    `
    )
    .join("");
}

function renderSourceBreakdown(map, total) {
  const node = document.getElementById("source-breakdown");
  if (!node) return;

  const entries = Object.entries(map).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    node.textContent = "暂无知识源数据";
    return;
  }

  node.innerHTML = entries
    .map(([source, count]) => {
      const pct = Math.round((count / total) * 100);
      return `
      <div class="stack-item">
        <div class="stack-title">
          <span>${window.tcmApi.escapeHtml(source)}</span>
          <span>${count}</span>
        </div>
        <div class="progress-wrap"><div class="progress-bar" style="width:${pct}%"></div></div>
      </div>
    `;
    })
    .join("");
}

function renderRecentAudits(items) {
  const node = document.getElementById("recent-audits");
  if (!node) return;

  if (!items.length) {
    node.textContent = "暂无审计事件";
    return;
  }

  node.innerHTML = items
    .slice(0, 8)
    .map((item) => {
      const ts = formatTime(item.timestamp);
      return `
      <div class="audit-item">
        <div class="audit-head">
          <span>${window.tcmApi.escapeHtml(item.event_type || "unknown")}</span>
          <span>${window.tcmApi.escapeHtml(item.actor || "system")}</span>
        </div>
        <p>${ts}</p>
      </div>
    `;
    })
    .join("");
}

function renderTrends(core, scenario) {
  const node = document.getElementById("trend-strip");
  if (!node) return;

  const rows = [
    {
      label: "知识库增长",
      value: core.knowledge_count || 0,
      unit: "条",
      progress: Math.min(100, Math.round(((core.knowledge_count || 0) / 40) * 100)),
    },
    {
      label: "推理调用趋势",
      value: (scenario.clinical_events || 0) + (scenario.rnd_events || 0),
      unit: "次",
      progress: Math.min(100, Math.round((((scenario.clinical_events || 0) + (scenario.rnd_events || 0)) / 60) * 100)),
    },
    {
      label: "专家审核通过率",
      value: core.adoption_ratio || 0,
      unit: "%",
      progress: Math.min(100, core.adoption_ratio || 0),
    },
    {
      label: "证据可追溯率",
      value: core.evidence_trace_ratio || 0,
      unit: "%",
      progress: Math.min(100, core.evidence_trace_ratio || 0),
    },
  ];

  node.innerHTML = rows
    .map(
      (row) => `
      <div class="trend-row">
        <div class="trend-row-head">
          <span>${window.tcmApi.escapeHtml(row.label)}</span>
          <span>${window.tcmApi.escapeHtml(String(row.value))}${window.tcmApi.escapeHtml(row.unit)}</span>
        </div>
        <div class="progress-wrap"><div class="progress-bar" style="width:${row.progress}%"></div></div>
      </div>
    `
    )
    .join("");
}

async function loadPendingReviews() {
  const node = document.getElementById("pending-review-list");
  if (!node) return;

  try {
    const result = await window.tcmApi.fetchJson("/review/tasks?status=pending&limit=6");
    const tasks = result.tasks || [];
    if (!tasks.length) {
      node.innerHTML = "<div class='result-box'>暂无待审核任务。</div>";
      return;
    }

    node.innerHTML = tasks
      .map(
        (task) => `
        <div class="audit-item">
          <div class="audit-head">
            <span>${window.tcmApi.escapeHtml(task.title || "")}</span>
            <span class="badge watch">${window.tcmApi.escapeHtml(task.priority || "medium")}</span>
          </div>
          <p>${window.tcmApi.escapeHtml(task.summary || "")}</p>
        </div>
      `
      )
      .join("");
  } catch (error) {
    node.innerHTML = `<div class='result-box'>加载失败: ${window.tcmApi.escapeHtml(String(error))}</div>`;
  }
}

function formatTime(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString("zh-CN", { hour12: false });
  } catch (e) {
    return String(value);
  }
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (!node) return;
  node.textContent = value;
}

loadDashboard();
