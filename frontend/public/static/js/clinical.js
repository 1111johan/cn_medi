const intakeForm = document.getElementById("intake-form");
const syndromeForm = document.getElementById("syndrome-form");
const formulaForm = document.getElementById("formula-form");
const draftForm = document.getElementById("draft-form");
const feedbackForm = document.getElementById("feedback-form");

const intakeResultBox = document.getElementById("intake-result-box");
const syndromeResultBox = document.getElementById("syndrome-result-box");
const formulaResultBox = document.getElementById("formula-result-box");
const draftResult = document.getElementById("draft-result");
const feedbackResult = document.getElementById("feedback-result");
const risksBox = document.getElementById("clinical-risks");
const traceStepList = document.getElementById("trace-step-list");
const loopActionForm = document.getElementById("loop-action-form");
const loopActionResult = document.getElementById("loop-action-result");

if (intakeForm) {
  intakeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    intakeResultBox.textContent = "处理中...";

    const formData = new FormData(intakeForm);
    const payload = {
      raw_text: formData.get("raw_text"),
      form_data: {},
      transcript: null,
    };

    try {
      const result = await window.tcmApi.fetchJson("/intake/parse", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      renderIntake(result);
      updateCheckpoint("intake");

      const symptomInput = syndromeForm.querySelector('input[name="symptoms"]');
      symptomInput.value = (result.standardized_fields?.symptoms || []).join(", ");

      const redFlags = result.red_flags || [];
      if (redFlags.length) {
        risksBox.textContent = `已触发红旗风险：${redFlags.join("、")}`;
      } else {
        risksBox.textContent = "暂未触发风险提示。";
      }
    } catch (error) {
      window.tcmApi.renderError(intakeResultBox, error);
    }
  });
}

if (syndromeForm) {
  syndromeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    syndromeResultBox.textContent = "处理中...";

    const formData = new FormData(syndromeForm);
    const payload = {
      symptoms: window.tcmApi.parseCsv(formData.get("symptoms")),
      tongue_tags: window.tcmApi.parseCsv(formData.get("tongue_tags")),
      pulse_tags: window.tcmApi.parseCsv(formData.get("pulse_tags")),
      constraints: {},
    };

    try {
      const result = await window.tcmApi.fetchJson("/reason/syndrome", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      renderSyndrome(result);
      await loadReasonTrace(payload);
      updateCheckpoint("syndrome");

      if (result.candidates && result.candidates[0]) {
        const top = result.candidates[0];
        formulaForm.querySelector('input[name="syndrome"]').value = top.syndrome;
        draftForm.querySelector('input[name="syndrome"]').value = top.syndrome;

        const riskHints = (top.counter_evidence || []).slice(0, 2);
        risksBox.textContent = riskHints.length
          ? `反证提示：${riskHints.join("；")}`
          : "暂未触发风险提示。";
      }
    } catch (error) {
      window.tcmApi.renderError(syndromeResultBox, error);
    }
  });
}

if (formulaForm) {
  formulaForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    formulaResultBox.textContent = "处理中...";

    const formData = new FormData(formulaForm);
    const payload = {
      syndrome: formData.get("syndrome"),
      contraindications: window.tcmApi.parseCsv(formData.get("contraindications")),
      patient_profile: {},
    };

    try {
      const result = await window.tcmApi.fetchJson("/reason/formula", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      renderFormula(result);
      updateCheckpoint("formula");

      draftForm.querySelector('input[name="therapy"]').value = result.therapy_principle || "待确认";
      draftForm.querySelector('input[name="formula"]').value = result.base_formula || "待确认";
    } catch (error) {
      window.tcmApi.renderError(formulaResultBox, error);
    }
  });
}

if (draftForm) {
  draftForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    draftResult.textContent = "处理中...";

    const formData = new FormData(draftForm);
    const payload = {
      template_type: "clinical_note",
      patient_info: {
        name: formData.get("name"),
        gender: "未填写",
        age: "未填写",
      },
      visit_data: {
        chief_complaint: formData.get("chief_complaint"),
        history: "由四诊结构化自动补录",
        tongue: "待补充",
        pulse: "待补充",
      },
      reasoning_result: {
        syndrome: formData.get("syndrome"),
        explanation: "由检索证据 + 规则推理联合生成",
        therapy: formData.get("therapy"),
        formula: formData.get("formula"),
      },
    };

    try {
      const result = await window.tcmApi.fetchJson("/document/draft", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(draftResult, result);
      updateCheckpoint("document");
    } catch (error) {
      window.tcmApi.renderError(draftResult, error);
    }
  });
}

if (feedbackForm) {
  feedbackForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedbackResult.textContent = "处理中...";

    const formData = new FormData(feedbackForm);
    const payload = {
      case_id: formData.get("case_id"),
      actor: "doctor",
      action: formData.get("action"),
      comments: formData.get("comments"),
      effectiveness: null,
      patched_formula: null,
    };

    try {
      const result = await window.tcmApi.fetchJson("/feedback/submit", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(feedbackResult, result);
      updateCheckpoint("feedback");
    } catch (error) {
      window.tcmApi.renderError(feedbackResult, error);
    }
  });
}

if (loopActionForm) {
  loopActionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loopActionResult.textContent = "处理中...";

    const formData = new FormData(loopActionForm);
    const payload = {
      case_id: formData.get("case_id"),
      action: formData.get("action"),
      comment: formData.get("comment") || null,
    };

    try {
      const result = await window.tcmApi.fetchJson("/feedback/loop-action", {
        method: "POST",
        headers: {
          "x-actor": "doctor",
        },
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(loopActionResult, result);
    } catch (error) {
      window.tcmApi.renderError(loopActionResult, error);
    }
  });
}

function renderIntake(result) {
  const fields = result.standardized_fields || {};
  const missing = result.missing_fields || [];

  intakeResultBox.innerHTML = `
    <strong>结构化字段</strong><br>
    主诉：${window.tcmApi.escapeHtml(fields.chief_complaint || "未识别")}<br>
    症状：${window.tcmApi.escapeHtml((fields.symptoms || []).join("、") || "未识别")}<br>
    年龄/性别：${window.tcmApi.escapeHtml(fields.age || "?")} / ${window.tcmApi.escapeHtml(fields.gender || "?")}<br>
    病程：${window.tcmApi.escapeHtml(fields.duration || "未识别")}<br>
    <br>
    <strong>缺失项</strong>：${window.tcmApi.escapeHtml(missing.join("、") || "无")}
  `;
}

function renderSyndrome(result) {
  const candidates = result.candidates || [];
  if (!candidates.length) {
    syndromeResultBox.textContent = "未获得候选证候。";
    return;
  }

  syndromeResultBox.innerHTML = candidates
    .map((item, idx) => {
      const supports = (item.support_evidence || []).slice(0, 4).join("；");
      const counters = (item.counter_evidence || []).slice(0, 2).join("；") || "无";
      return `
      <div class="evidence-item">
        <div class="evidence-head">
          <span>Top ${idx + 1} · ${window.tcmApi.escapeHtml(item.syndrome)}</span>
          <span class="badge ok">score ${item.score}</span>
        </div>
        <p>支持证据：${window.tcmApi.escapeHtml(supports)}</p>
        <p>反证：${window.tcmApi.escapeHtml(counters)}</p>
        <p>解释：${window.tcmApi.escapeHtml(item.explanation || "")}</p>
      </div>
    `;
    })
    .join("");
}

function renderFormula(result) {
  const mods = (result.modifications || []).map((x) => `- ${x}`).join("\n");
  const cautions = (result.cautions || []).map((x) => `- ${x}`).join("\n");

  formulaResultBox.innerHTML = `
    <strong>治法</strong>：${window.tcmApi.escapeHtml(result.therapy_principle || "待确认")}<br>
    <strong>基础方</strong>：${window.tcmApi.escapeHtml(result.base_formula || "待确认")}<br><br>
    <strong>加减建议</strong><br>${window.tcmApi.escapeHtml(mods || "无").replace(/\n/g, "<br>")}<br><br>
    <strong>风险提醒</strong><br>${window.tcmApi.escapeHtml(cautions || "无").replace(/\n/g, "<br>")}
  `;
}

function updateCheckpoint(step) {
  const node = document.querySelector(`#clinical-checkpoints li[data-step="${step}"]`);
  if (!node) return;
  node.classList.add("done");
}

async function loadReasonTrace(payload) {
  if (!traceStepList) return;

  traceStepList.innerHTML = "<div class='result-box'>推理链加载中...</div>";
  try {
    const result = await window.tcmApi.fetchJson("/reason/trace", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderTraceSteps(result.steps || []);
  } catch (error) {
    traceStepList.innerHTML = `<div class='result-box'>推理链加载失败: ${window.tcmApi.escapeHtml(String(error))}</div>`;
  }
}

function renderTraceSteps(steps) {
  if (!steps.length) {
    traceStepList.innerHTML = "<div class='result-box'>暂无推理链数据。</div>";
    return;
  }

  traceStepList.innerHTML = steps
    .map((step, idx) => {
      const statusClass = step.status === "done" ? "ok" : step.status === "required" ? "watch" : "risk";
      return `
      <div class="stack-item">
        <div class="stack-title">
          <span>${idx + 1}. ${window.tcmApi.escapeHtml(step.name || "")}</span>
          <span class="badge ${statusClass}">${window.tcmApi.escapeHtml(step.status || "")}</span>
        </div>
        <div class="stack-desc">${formatTraceDetail(step.detail)}</div>
      </div>
    `;
    })
    .join("");
}

function formatTraceDetail(detail) {
  if (typeof detail === "string") {
    return window.tcmApi.escapeHtml(detail);
  }
  if (Array.isArray(detail)) {
    if (!detail.length) return "无";
    return detail
      .slice(0, 4)
      .map((item) => {
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
    if (detail.message && Array.isArray(detail.checklist)) {
      const checklist = detail.checklist.map((x, i) => `${i + 1}. ${window.tcmApi.escapeHtml(x)}`).join("<br>");
      return `<strong>${window.tcmApi.escapeHtml(detail.message)}</strong><br>${checklist}`;
    }
    return Object.entries(detail)
      .map(([k, v]) => `${window.tcmApi.escapeHtml(k)}: ${window.tcmApi.escapeHtml(String(v))}`)
      .join("<br>");
  }
  return "无";
}
