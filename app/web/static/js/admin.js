const auditForm = document.getElementById("audit-form");
const loadKnowledgeBtn = document.getElementById("load-knowledge");
const loadProfStatsBtn = document.getElementById("load-prof-stats");
const loadRulesBtn = document.getElementById("load-rules");
const loadDashboardBtn = document.getElementById("load-dashboard");

const auditList = document.getElementById("audit-list");
const knowledgeResult = document.getElementById("knowledge-result");
const profStatsResult = document.getElementById("prof-stats-result");
const rulesList = document.getElementById("rules-list");
const governanceLoopList = document.getElementById("governance-loop-list");

if (auditForm) {
  auditForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    auditList.innerHTML = "<div class='result-box'>处理中...</div>";

    const formData = new FormData(auditForm);
    const actor = String(formData.get("actor") || "").trim();
    const eventType = String(formData.get("event_type") || "").trim();
    const limit = Number(formData.get("limit") || 50);

    const query = new URLSearchParams();
    if (actor) query.set("actor", actor);
    if (eventType) query.set("event_type", eventType);
    query.set("limit", String(limit));

    try {
      const result = await window.tcmApi.fetchJson(`/governance/audit?${query.toString()}`);
      renderAuditList(result || []);
    } catch (error) {
      auditList.innerHTML = `<div class='result-box'>请求失败: ${String(error)}</div>`;
    }
  });
}

if (loadKnowledgeBtn) {
  loadKnowledgeBtn.addEventListener("click", async () => {
    knowledgeResult.textContent = "处理中...";
    try {
      const result = await window.tcmApi.fetchJson("/knowledge/list?limit=100");
      window.tcmApi.renderJson(knowledgeResult, result);
    } catch (error) {
      window.tcmApi.renderError(knowledgeResult, error);
    }
  });
}

if (loadProfStatsBtn) {
  loadProfStatsBtn.addEventListener("click", async () => {
    profStatsResult.textContent = "处理中...";
    try {
      const result = await window.tcmApi.fetchJson("/knowledge/professional/stats");
      window.tcmApi.renderJson(profStatsResult, result);
      const countNode = document.getElementById("admin-prof-count");
      if (countNode) countNode.textContent = result.record_count || 0;
    } catch (error) {
      window.tcmApi.renderError(profStatsResult, error);
    }
  });
}

if (loadRulesBtn) {
  loadRulesBtn.addEventListener("click", async () => {
    rulesList.innerHTML = "<div class='result-box'>处理中...</div>";
    try {
      const result = await window.tcmApi.fetchJson("/governance/rules");
      renderRules(result.rules || {});
      const countNode = document.getElementById("rule-count");
      if (countNode) countNode.textContent = result.count || 0;
    } catch (error) {
      rulesList.innerHTML = `<div class='result-box'>请求失败: ${String(error)}</div>`;
    }
  });
}

if (loadDashboardBtn) {
  loadDashboardBtn.addEventListener("click", async () => {
    governanceLoopList.innerHTML = "<div class='result-box'>处理中...</div>";
    try {
      const result = await window.tcmApi.fetchJson("/platform/dashboard");
      renderLoopList(result.loops || {});
    } catch (error) {
      governanceLoopList.innerHTML = `<div class='result-box'>请求失败: ${String(error)}</div>`;
    }
  });
}

function renderAuditList(items) {
  if (!items.length) {
    auditList.innerHTML = "<div class='result-box'>暂无匹配审计记录。</div>";
    return;
  }

  auditList.innerHTML = items
    .map((item) => `
      <div class="audit-item">
        <div class="audit-head">
          <span>${window.tcmApi.escapeHtml(item.event_type || "unknown")}</span>
          <span>${window.tcmApi.escapeHtml(item.actor || "system")}</span>
        </div>
        <p>${window.tcmApi.escapeHtml(item.timestamp || "")}</p>
      </div>
    `)
    .join("");
}

function renderRules(rules) {
  const entries = Object.entries(rules);
  if (!entries.length) {
    rulesList.innerHTML = "<div class='result-box'>暂无规则配置。</div>";
    return;
  }

  rulesList.innerHTML = entries
    .map(([name, rule]) => {
      const symptoms = (rule.symptoms || []).slice(0, 5).join("、");
      const formula = rule.formula || "待定";
      const therapy = rule.therapy || "待定";
      return `
      <div class="stack-item">
        <div class="stack-title">
          <span>${window.tcmApi.escapeHtml(name)}</span>
          <span class="badge ok">rule</span>
        </div>
        <div class="stack-desc">治法：${window.tcmApi.escapeHtml(therapy)}</div>
        <div class="stack-desc">方剂：${window.tcmApi.escapeHtml(formula)}</div>
        <div class="stack-desc">核心症状：${window.tcmApi.escapeHtml(symptoms)}</div>
      </div>
    `;
    })
    .join("");
}

function renderLoopList(loops) {
  const entries = Object.values(loops);
  if (!entries.length) {
    governanceLoopList.innerHTML = "<div class='result-box'>暂无治理指标。</div>";
    return;
  }

  governanceLoopList.innerHTML = entries
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

// 初次自动加载
if (loadDashboardBtn) loadDashboardBtn.click();
if (loadRulesBtn) loadRulesBtn.click();
if (loadProfStatsBtn) loadProfStatsBtn.click();
