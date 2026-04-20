const loopListNode = document.getElementById("op-loop-list");
const riskAuditsNode = document.getElementById("op-risk-audits");
const taskListNode = document.getElementById("op-task-list");
const auditForm = document.getElementById("op-audit-form");
const auditListNode = document.getElementById("op-audit-list");
const loadRulesBtn = document.getElementById("op-load-rules");
const rulesListNode = document.getElementById("op-rules-list");

if (auditForm) {
  auditForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    auditListNode.innerHTML = "<div class='result-box'>处理中...</div>";

    const formData = new FormData(auditForm);
    const query = new URLSearchParams();
    ["actor", "event_type", "limit"].forEach((k) => {
      const v = String(formData.get(k) || "").trim();
      if (v) query.set(k, v);
    });

    try {
      const result = await window.tcmApi.fetchJson(`/governance/audit?${query.toString()}`);
      renderAuditList(result || [], auditListNode);
    } catch (error) {
      auditListNode.innerHTML = `<div class='result-box'>请求失败: ${String(error)}</div>`;
    }
  });
}

if (loadRulesBtn) {
  loadRulesBtn.addEventListener("click", async () => {
    rulesListNode.innerHTML = "<div class='result-box'>处理中...</div>";
    try {
      const result = await window.tcmApi.fetchJson("/governance/rules");
      const entries = Object.entries(result.rules || {});
      rulesListNode.innerHTML = entries
        .map(([name, rule]) => `
        <div class="stack-item">
          <div class="stack-title"><span>${window.tcmApi.escapeHtml(name)}</span><span class="badge ok">active</span></div>
          <div class="stack-desc">治法：${window.tcmApi.escapeHtml(rule.therapy || "")}</div>
          <div class="stack-desc">方剂：${window.tcmApi.escapeHtml(rule.formula || "")}</div>
        </div>
      `)
        .join("");
    } catch (error) {
      rulesListNode.innerHTML = `<div class='result-box'>请求失败: ${String(error)}</div>`;
    }
  });
}

async function loadDashboard() {
  try {
    const dashboard = await window.tcmApi.fetchJson("/platform/dashboard");
    const core = dashboard.core_metrics || {};
    const scenario = dashboard.scenario_metrics || {};

    setText("op-audit-count", core.audit_count || 0);
    setText("op-feedback-count", core.feedback_count || 0);
    setText("op-clinical-events", scenario.clinical_events || 0);
    setText("op-research-events", scenario.research_events || 0);
    setText("op-rnd-events", scenario.rnd_events || 0);
    setText("op-smart-qa-events", scenario.smart_qa_events || 0);
    setText("op-trace", `${core.evidence_trace_ratio || 0}%`);
    setText("op-adoption", `${core.adoption_ratio || 0}%`);
    setText("op-loops", core.clinical_closed_loops || 0);
    setText("op-prof-count", core.professional_record_count || 0);

    renderLoopList(Object.values(dashboard.loops || {}));
    renderTaskList(dashboard.task_queue || []);
  } catch (error) {
    loopListNode.innerHTML = `<div class='result-box'>加载失败: ${String(error)}</div>`;
  }
}

function renderLoopList(items) {
  if (!items.length) {
    loopListNode.innerHTML = "<div class='result-box'>暂无治理指标。</div>";
    return;
  }

  loopListNode.innerHTML = items
    .map((item) => {
      const statusClass = window.tcmApi.badgeClassByStatus(item.status);
      return `
      <div class="stack-item">
        <div class="stack-title"><span>${window.tcmApi.escapeHtml(item.name)}</span><span class="badge ${statusClass}">${item.progress}%</span></div>
        <div class="stack-desc">${window.tcmApi.escapeHtml(item.desc || "")}</div>
        <div class="progress-wrap"><div class="progress-bar ${statusClass}" style="width:${item.progress}%"></div></div>
      </div>
    `;
    })
    .join("");
}

function renderTaskList(items) {
  if (!items.length) {
    taskListNode.innerHTML = "<div class='result-box'>暂无任务。</div>";
    return;
  }

  taskListNode.innerHTML = items
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

async function loadRiskAudits() {
  try {
    const items = await window.tcmApi.fetchJson("/governance/audit?limit=120");
    const riskItems = items.filter((item) => {
      const text = JSON.stringify(item.details || {});
      return (
        item.event_type === "review.decision"
        || text.includes("风险")
        || text.includes("禁忌")
        || text.includes("孕期")
      );
    });

    if (!riskItems.length) {
      riskAuditsNode.innerHTML = "<div class='result-box'>近期无高危事件。</div>";
      return;
    }

    renderAuditList(riskItems.slice(0, 12), riskAuditsNode);
  } catch (error) {
    riskAuditsNode.innerHTML = `<div class='result-box'>加载失败: ${String(error)}</div>`;
  }
}

function renderAuditList(items, node) {
  if (!items.length) {
    node.innerHTML = "<div class='result-box'>暂无审计记录。</div>";
    return;
  }

  node.innerHTML = items
    .map((item) => `
      <div class="audit-item">
        <div class="audit-head">
          <span>${window.tcmApi.escapeHtml(item.event_type || "")}</span>
          <span>${window.tcmApi.escapeHtml(item.actor || "")}</span>
        </div>
        <p>${window.tcmApi.escapeHtml(item.timestamp || "")}</p>
      </div>
    `)
    .join("");
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

loadDashboard();
loadRiskAudits();
loadRulesBtn?.click();
auditForm?.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
