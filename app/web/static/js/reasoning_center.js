const traceForm = document.getElementById("rc-trace-form");
const traceStepsNode = document.getElementById("rc-trace-steps");
const rulesListNode = document.getElementById("rc-rules-list");

if (traceForm) {
  traceForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    traceStepsNode.innerHTML = "<div class='result-box'>处理中...</div>";

    const formData = new FormData(traceForm);
    const payload = {
      symptoms: window.tcmApi.parseCsv(formData.get("symptoms")),
      tongue_tags: window.tcmApi.parseCsv(formData.get("tongue_tags")),
      pulse_tags: window.tcmApi.parseCsv(formData.get("pulse_tags")),
      constraints: {},
    };

    try {
      const result = await window.tcmApi.fetchJson("/reason/trace", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderTraceSteps(result.steps || []);
    } catch (error) {
      traceStepsNode.innerHTML = `<div class='result-box'>请求失败: ${String(error)}</div>`;
    }
  });
}

function renderTraceSteps(steps) {
  if (!steps.length) {
    traceStepsNode.innerHTML = "<div class='result-box'>暂无推理链路。</div>";
    return;
  }

  traceStepsNode.innerHTML = steps
    .map((step, idx) => {
      const statusClass = step.status === "done" ? "ok" : step.status === "required" ? "watch" : "risk";
      const detail = formatStepDetail(step.detail);

      return `
      <div class="stack-item">
        <div class="stack-title">
          <span>${idx + 1}. ${window.tcmApi.escapeHtml(step.name || "step")}</span>
          <span class="badge ${statusClass}">${window.tcmApi.escapeHtml(step.status || "")}</span>
        </div>
        <div class="stack-desc">${detail}</div>
      </div>
    `;
    })
    .join("");
}

function formatStepDetail(detail) {
  if (typeof detail === "string") {
    return window.tcmApi.escapeHtml(detail);
  }
  if (detail && typeof detail === "object" && detail.message && Array.isArray(detail.checklist)) {
    const checklist = detail.checklist
      .map((item, idx) => `${idx + 1}. ${window.tcmApi.escapeHtml(item)}`)
      .join("<br>");
    return `<strong>${window.tcmApi.escapeHtml(detail.message)}</strong><br>${checklist}`;
  }
  if (Array.isArray(detail)) {
    if (!detail.length) return "无";
    return detail
      .slice(0, 5)
      .map((item) => {
        if (typeof item === "string") return window.tcmApi.escapeHtml(item);
        if (item && typeof item === "object") {
          return Object.entries(item)
            .map(([k, v]) => `${window.tcmApi.escapeHtml(k)}: ${window.tcmApi.escapeHtml(String(v))}`)
            .join(" | ");
        }
        return window.tcmApi.escapeHtml(String(item));
      })
      .join("<br>");
  }
  if (detail && typeof detail === "object") {
    return Object.entries(detail)
      .map(([k, v]) => `${window.tcmApi.escapeHtml(k)}: ${window.tcmApi.escapeHtml(String(v))}`)
      .join("<br>");
  }
  return "无";
}

async function loadRules() {
  rulesListNode.innerHTML = "<div class='result-box'>加载中...</div>";
  try {
    const result = await window.tcmApi.fetchJson("/governance/rules");
    document.getElementById("rc-rule-count").textContent = result.count || 0;

    const entries = Object.entries(result.rules || {});
    rulesListNode.innerHTML = entries
      .map(([name, rule]) => `
      <div class="stack-item">
        <div class="stack-title"><span>${window.tcmApi.escapeHtml(name)}</span><span class="badge ok">active</span></div>
        <div class="stack-desc">治法：${window.tcmApi.escapeHtml(rule.therapy || "")}</div>
        <div class="stack-desc">方药：${window.tcmApi.escapeHtml(rule.formula || "")}</div>
        <div class="stack-desc">症状特征：${window.tcmApi.escapeHtml((rule.symptoms || []).slice(0, 6).join("、"))}</div>
      </div>
    `)
      .join("");
  } catch (error) {
    rulesListNode.innerHTML = `<div class='result-box'>加载失败: ${String(error)}</div>`;
  }
}

loadRules();
traceForm?.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
