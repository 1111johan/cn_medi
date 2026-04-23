const clinicalForm = document.getElementById("clinical-demo-form");
const commitForm = document.getElementById("clinical-commit-form");
const patientListNode = document.getElementById("clinical-patient-list");
const patientCardNode = document.getElementById("clinical-patient-card");
const structuredPanel = document.getElementById("clinical-structured-panel");
const topnPanel = document.getElementById("clinical-topn-panel");
const rulesPanel = document.getElementById("clinical-rules-panel");
const evidencePanel = document.getElementById("clinical-evidence-panel");
const formulaPanel = document.getElementById("clinical-formula-panel");
const riskPanel = document.getElementById("clinical-risk-panel");
const tracePanel = document.getElementById("clinical-trace-panel");
const compareBox = document.getElementById("clinical-compare-box");
const draftResult = document.getElementById("clinical-draft-result");
const writebackResult = document.getElementById("clinical-writeback-result");
const topSyndromeChip = document.getElementById("clinical-top-syndrome-chip");
const adoptChip = document.getElementById("clinical-adopt-chip");

const demoCases = [
  {
    case_id: "case-20260424-001",
    patient_id: "P202604001",
    name: "王某某",
    gender: "女",
    age: 45,
    department: "中医内科",
    visit_type: "复诊",
    visit_time: "2026-04-24 09:10",
    chief_complaint: "失眠2周，伴心烦口干",
    present_illness: "近2周入睡困难，多梦易醒，夜间烦躁，晨起口干，近3天心烦明显。",
    tongue: "舌红，苔黄腻",
    pulse: "滑数",
    symptoms: ["失眠", "心烦", "口干"],
    exam_results: "常规检查未见明显异常。",
    past_history: "否认重大慢病史。",
    summary: "复诊 · 失眠 / 心烦 / 口干",
  },
  {
    case_id: "case-20260424-002",
    patient_id: "P202604002",
    name: "刘某",
    gender: "男",
    age: 36,
    department: "中医内科",
    visit_type: "初诊",
    visit_time: "2026-04-24 10:20",
    chief_complaint: "胸闷痰多1月",
    present_illness: "胸闷反复1月，咳痰较多，纳差，体倦困重。",
    tongue: "舌胖，苔白腻",
    pulse: "滑",
    symptoms: ["胸闷", "痰多", "纳差", "乏力"],
    exam_results: "胸片未见明显实变。",
    past_history: "吸烟10年。",
    summary: "初诊 · 胸闷 / 痰多",
  },
  {
    case_id: "case-20260424-003",
    patient_id: "P202604003",
    name: "陈某",
    gender: "女",
    age: 52,
    department: "中医内科",
    visit_type: "复诊",
    visit_time: "2026-04-24 14:00",
    chief_complaint: "乏力纳差伴便溏3周",
    present_illness: "近3周乏力明显，食欲下降，餐后腹胀，大便偏溏。",
    tongue: "舌淡胖，苔白腻",
    pulse: "濡涩",
    symptoms: ["乏力", "纳差", "腹胀", "便溏"],
    exam_results: "血糖波动偏高。",
    past_history: "2型糖尿病5年。",
    summary: "复诊 · 乏力 / 纳差 / 便溏",
  },
];

let selectedCase = demoCases[0] || null;
let latestAnalysis = null;

function markStep(step) {
  const node = document.querySelector(`#clinical-checkpoints li[data-step="${step}"]`);
  if (node) node.classList.add("done");
}

function renderPatientList() {
  if (!patientListNode) return;
  patientListNode.innerHTML = demoCases
    .map(
      (item) => `
      <button type="button" class="queue-item ${selectedCase && selectedCase.case_id === item.case_id ? "active" : ""}" data-case-id="${window.tcmApi.escapeHtml(item.case_id)}">
        <strong>${window.tcmApi.escapeHtml(item.name)}</strong>
        <span>${window.tcmApi.escapeHtml(item.summary)}</span>
      </button>
    `
    )
    .join("");

  patientListNode.querySelectorAll(".queue-item").forEach((button) => {
    button.addEventListener("click", () => {
      const hit = demoCases.find((item) => item.case_id === button.dataset.caseId);
      if (!hit) return;
      selectedCase = hit;
      renderPatientList();
      fillClinicalForm(hit);
      renderPatientCard(hit);
      markStep("patient");
    });
  });
}

function renderPatientCard(item) {
  if (!patientCardNode || !item) return;
  patientCardNode.innerHTML = `
    <div class="patient-summary-head">
      <div>
        <h4>${window.tcmApi.escapeHtml(item.name)}</h4>
        <p>${window.tcmApi.escapeHtml(item.patient_id)} · ${window.tcmApi.escapeHtml(item.visit_type)} · ${window.tcmApi.escapeHtml(item.department)}</p>
      </div>
      <span class="badge ok">${window.tcmApi.escapeHtml(item.visit_time)}</span>
    </div>
    <div class="patient-summary-grid">
      <div><span>性别/年龄</span><strong>${window.tcmApi.escapeHtml(item.gender)} / ${window.tcmApi.escapeHtml(String(item.age))}</strong></div>
      <div><span>主诉</span><strong>${window.tcmApi.escapeHtml(item.chief_complaint)}</strong></div>
      <div><span>舌象</span><strong>${window.tcmApi.escapeHtml(item.tongue || "未填写")}</strong></div>
      <div><span>脉象</span><strong>${window.tcmApi.escapeHtml(item.pulse || "未填写")}</strong></div>
    </div>
  `;
}

function fillClinicalForm(item) {
  if (!clinicalForm || !item) return;
  ["case_id", "patient_id", "name", "gender", "age", "department", "visit_type", "visit_time", "chief_complaint", "present_illness", "tongue", "pulse", "exam_results", "past_history"].forEach((key) => {
    const node = clinicalForm.elements.namedItem(key);
    if (node) node.value = item[key] || "";
  });
  const symptomsNode = clinicalForm.elements.namedItem("symptoms");
  if (symptomsNode) symptomsNode.value = (item.symptoms || []).join(", ");
}

function collectAnalyzePayload() {
  const formData = new FormData(clinicalForm);
  return {
    case_id: formData.get("case_id") || "",
    patient_id: formData.get("patient_id") || "",
    name: formData.get("name") || "",
    gender: formData.get("gender") || "",
    age: Number.parseInt(formData.get("age") || "", 10) || null,
    department: formData.get("department") || "中医内科",
    visit_type: formData.get("visit_type") || "初诊",
    visit_time: formData.get("visit_time") || "",
    chief_complaint: String(formData.get("chief_complaint") || "").trim(),
    present_illness: String(formData.get("present_illness") || "").trim(),
    tongue: String(formData.get("tongue") || "").trim(),
    pulse: String(formData.get("pulse") || "").trim(),
    symptoms: window.tcmApi.parseCsv(String(formData.get("symptoms") || "").replace(/，/g, ",")),
    exam_results: String(formData.get("exam_results") || "").trim(),
    past_history: String(formData.get("past_history") || "").trim(),
  };
}

function renderStructuredPanel(result) {
  if (!structuredPanel) return;
  const data = result.structured_features || {};
  const cards = [
    { label: "主症", value: (data.main_symptoms || []).join("、") || "未提取" },
    { label: "舌象", value: (data.tongue_features || []).join("、") || "未提取" },
    { label: "脉象", value: (data.pulse_features || []).join("、") || "未提取" },
    { label: "病位", value: (data.disease_location || []).join("、") || "待判断" },
    { label: "病性", value: (data.disease_nature || []).join("、") || "待判断" },
    { label: "热象 / 痰象", value: `${data.heat_sign ? "有热象" : "热象不显"} · ${data.phlegm_sign ? "有痰象" : "痰象不显"}` },
  ];
  structuredPanel.classList.remove("empty-panel");
  structuredPanel.innerHTML = cards
    .map(
      (item) => `
      <div class="clinical-metric-card">
        <span>${window.tcmApi.escapeHtml(item.label)}</span>
        <strong>${window.tcmApi.escapeHtml(item.value)}</strong>
      </div>
    `
    )
    .join("");
}

function renderTopnPanel(result) {
  if (!topnPanel || !topSyndromeChip) return;
  const items = result.top_syndromes || [];
  if (!items.length) {
    topnPanel.classList.add("empty-panel");
    topnPanel.innerHTML = "<div class='empty-state-text'>未获得证候候选。</div>";
    topSyndromeChip.textContent = "未获得候选";
    topSyndromeChip.className = "status-chip risk";
    return;
  }

  topnPanel.classList.remove("empty-panel");
  topnPanel.innerHTML = items
    .map(
      (item, index) => `
      <div class="clinical-topn-card ${index === 0 ? "is-top" : ""}">
        <div class="clinical-topn-head">
          <span>Top ${index + 1} · ${window.tcmApi.escapeHtml(item.name)}</span>
          <span class="badge ${index === 0 ? "ok" : "watch"}">${window.tcmApi.escapeHtml(String(item.score))}</span>
        </div>
        <p>支持证据：${window.tcmApi.escapeHtml((item.support_evidence || []).join("；") || "待补证")}</p>
        <p>反证提示：${window.tcmApi.escapeHtml((item.counter_evidence || []).join("；") || "无")}</p>
      </div>
    `
    )
    .join("");

  topSyndromeChip.textContent = `首位候选：${items[0].name}`;
  topSyndromeChip.className = "status-chip";
}

function renderRulesPanel(result) {
  if (!rulesPanel) return;
  const items = result.rule_hits || [];
  if (!items.length) {
    rulesPanel.classList.add("empty-panel");
    rulesPanel.innerHTML = "<div class='empty-state-text'>暂无规则命中。</div>";
    return;
  }
  rulesPanel.classList.remove("empty-panel");
  rulesPanel.innerHTML = items
    .map(
      (item) => `
      <div class="stack-item">
        <div class="stack-title"><span>${window.tcmApi.escapeHtml(item.rule_name)}</span><span class="badge ok">${window.tcmApi.escapeHtml(item.rule_id)}</span></div>
        <div class="stack-desc">${window.tcmApi.escapeHtml((item.matched_evidence || []).join("、") || "无")}</div>
      </div>
    `
    )
    .join("");
}

function renderEvidencePanel(result) {
  if (!evidencePanel) return;
  const items = result.evidence_refs || [];
  if (!items.length) {
    evidencePanel.classList.add("empty-panel");
    evidencePanel.innerHTML = "<div class='empty-state-text'>暂无证据引用。</div>";
    return;
  }
  evidencePanel.classList.remove("empty-panel");
  evidencePanel.innerHTML = items
    .map(
      (item, index) => `
      <div class="stack-item">
        <div class="stack-title"><span>证据 ${index + 1}</span><span class="badge watch">来源</span></div>
        <div class="stack-desc"><strong>${window.tcmApi.escapeHtml(item.source || "")}</strong></div>
        <div class="stack-desc">${window.tcmApi.escapeHtml(item.support_point || "")}</div>
        <div class="stack-desc">${window.tcmApi.escapeHtml(item.quote || "")}</div>
      </div>
    `
    )
    .join("");
}

function renderFormulaPanel(result) {
  if (!formulaPanel) return;
  const item = result.formula_draft || {};
  formulaPanel.innerHTML = `
    <strong>治法</strong>：${window.tcmApi.escapeHtml(item.principle || "待生成")}<br><br>
    <strong>参考方</strong>：${window.tcmApi.escapeHtml(item.formula || "待生成")}<br><br>
    <strong>加减建议</strong><br>${window.tcmApi.escapeHtml((item.modifications || []).join("\n") || "无").replace(/\n/g, "<br>")}<br><br>
    <strong>说明</strong>：${window.tcmApi.escapeHtml(item.note || "")}
  `;
}

function renderRiskPanel(result) {
  if (!riskPanel) return;
  const items = result.risk_alerts || [];
  riskPanel.innerHTML = items.length
    ? items.map((item) => `<div>• ${window.tcmApi.escapeHtml(item)}</div>`).join("")
    : "暂未触发风险提示。";
}

function renderTracePanel(result) {
  if (!tracePanel) return;
  const steps = result.trace_steps || [];
  if (!steps.length) {
    tracePanel.classList.add("empty-panel");
    tracePanel.innerHTML = "<div class='empty-state-text'>暂无推理链摘要。</div>";
    return;
  }
  tracePanel.classList.remove("empty-panel");
  tracePanel.innerHTML = steps
    .map((step) => {
      let summary = "";
      if (Array.isArray(step.detail)) {
        summary = `命中 ${step.detail.length} 项`; 
      } else if (step.detail && typeof step.detail === "object") {
        summary = Object.keys(step.detail).slice(0, 4).join("、") || "已完成";
      } else {
        summary = String(step.detail || "已完成");
      }
      return `
        <div class="stack-item">
          <div class="stack-title"><span>${window.tcmApi.escapeHtml(step.name || "")}</span><span class="badge ${step.status === "required" ? "risk" : "ok"}">${window.tcmApi.escapeHtml(step.status || "done")}</span></div>
          <div class="stack-desc">${window.tcmApi.escapeHtml(summary)}</div>
        </div>
      `;
    })
    .join("");
}

function syncCommitForm(result) {
  if (!commitForm) return;
  const patient = result.patient_card || {};
  const input = result.input_summary || {};
  const defaults = result.doctor_defaults || {};
  const topName = (result.top_syndromes || [])[0]?.name || "";

  [
    ["case_id", result.case_id],
    ["patient_id", result.patient_id],
    ["patient_name", patient.name],
    ["gender", patient.gender],
    ["age", patient.age],
    ["chief_complaint", input.chief_complaint],
    ["present_illness", input.present_illness],
    ["tongue", input.tongue],
    ["pulse", input.pulse],
    ["ai_top_syndrome", topName],
    ["final_syndrome", defaults.final_syndrome || topName],
    ["final_therapy", defaults.final_therapy || ""],
    ["final_formula", defaults.final_formula || ""],
    ["doctor_notes", ""],
  ].forEach(([name, value]) => {
    const node = commitForm.elements.namedItem(name);
    if (node) node.value = value == null ? "" : value;
  });

  const adoptNode = commitForm.elements.namedItem("adopt_ai");
  if (adoptNode) adoptNode.value = String(defaults.adopt_ai !== false);
  renderCompareBox();
}

function renderCompareBox() {
  if (!compareBox || !commitForm || !latestAnalysis) return;
  const aiTop = String(commitForm.elements.namedItem("ai_top_syndrome")?.value || "待生成");
  const finalSyndrome = String(commitForm.elements.namedItem("final_syndrome")?.value || "待确认");
  const finalTherapy = String(commitForm.elements.namedItem("final_therapy")?.value || "待确认");
  const finalFormula = String(commitForm.elements.namedItem("final_formula")?.value || "待确认");
  const adoptAi = String(commitForm.elements.namedItem("adopt_ai")?.value || "true") === "true";

  compareBox.innerHTML = `
    <div class="compare-grid">
      <div>
        <span>AI 推荐证候</span>
        <strong>${window.tcmApi.escapeHtml(aiTop)}</strong>
      </div>
      <div>
        <span>医生最终证候</span>
        <strong>${window.tcmApi.escapeHtml(finalSyndrome)}</strong>
      </div>
      <div>
        <span>最终治法</span>
        <strong>${window.tcmApi.escapeHtml(finalTherapy)}</strong>
      </div>
      <div>
        <span>最终方药</span>
        <strong>${window.tcmApi.escapeHtml(finalFormula)}</strong>
      </div>
    </div>
  `;

  adoptChip.textContent = adoptAi ? "当前：采纳 AI" : "当前：人工修订";
  adoptChip.className = `status-chip ${adoptAi ? "" : "warn"}`.trim();
}

function renderAnalysis(result) {
  latestAnalysis = result;
  renderStructuredPanel(result);
  renderTopnPanel(result);
  renderRulesPanel(result);
  renderEvidencePanel(result);
  renderFormulaPanel(result);
  renderRiskPanel(result);
  renderTracePanel(result);
  syncCommitForm(result);
  markStep("analysis");
  writebackResult.textContent = "分析完成，等待医生修订并回写。";
  draftResult.textContent = "确认回写后生成病历草稿。";
}

async function analyzeCase(event) {
  event.preventDefault();
  if (!clinicalForm) return;
  const payload = collectAnalyzePayload();
  if (!payload.chief_complaint) return;

  markStep("intake");
  topSyndromeChip.textContent = "分析中...";
  topSyndromeChip.className = "status-chip warn";
  formulaPanel.textContent = "分析中...";
  riskPanel.textContent = "分析中...";

  try {
    const result = await window.tcmApi.fetchJson("/clinical/demo-analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderAnalysis(result);
  } catch (error) {
    formulaPanel.textContent = `请求失败：${String(error)}`;
    riskPanel.textContent = "请检查后端 API 是否可用。";
    topSyndromeChip.textContent = "分析失败";
    topSyndromeChip.className = "status-chip risk";
  }
}

async function commitCase(event) {
  event.preventDefault();
  if (!commitForm || !latestAnalysis) return;
  const formData = new FormData(commitForm);
  const payload = {
    case_id: formData.get("case_id") || "",
    patient_id: formData.get("patient_id") || "",
    patient_name: formData.get("patient_name") || "",
    gender: formData.get("gender") || "",
    age: Number.parseInt(formData.get("age") || "", 10) || null,
    chief_complaint: formData.get("chief_complaint") || "",
    present_illness: formData.get("present_illness") || "",
    tongue: formData.get("tongue") || "",
    pulse: formData.get("pulse") || "",
    ai_top_syndrome: formData.get("ai_top_syndrome") || "",
    final_syndrome: formData.get("final_syndrome") || "",
    final_therapy: formData.get("final_therapy") || "",
    final_formula: formData.get("final_formula") || "",
    doctor_notes: formData.get("doctor_notes") || "",
    adopt_ai: String(formData.get("adopt_ai") || "true") === "true",
  };

  markStep("review");
  writebackResult.textContent = "回写中...";
  try {
    const result = await window.tcmApi.fetchJson("/clinical/demo-commit", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    draftResult.textContent = result.draft || "";
    writebackResult.innerHTML = `
      <strong>状态</strong>：${window.tcmApi.escapeHtml(result.status || "saved")}<br>
      <strong>反馈样本</strong>：${window.tcmApi.escapeHtml(result.feedback_id || "") }<br>
      <strong>审计记录</strong>：${window.tcmApi.escapeHtml(result.audit_id || "") }<br>
      <strong>动作</strong>：${window.tcmApi.escapeHtml(result.action || "") }<br><br>
      ${window.tcmApi.escapeHtml(result.writeback_message || "")}
    `;
    markStep("writeback");
  } catch (error) {
    writebackResult.textContent = `回写失败：${String(error)}`;
  }
}

function bindCommitInputs() {
  if (!commitForm) return;
  ["final_syndrome", "final_therapy", "final_formula", "adopt_ai"].forEach((name) => {
    const node = commitForm.elements.namedItem(name);
    node?.addEventListener("input", renderCompareBox);
    node?.addEventListener("change", renderCompareBox);
  });
}

function bootstrapClinicalDemo() {
  renderPatientList();
  if (selectedCase) {
    fillClinicalForm(selectedCase);
    renderPatientCard(selectedCase);
    markStep("patient");
  }
  clinicalForm?.addEventListener("submit", analyzeCase);
  commitForm?.addEventListener("submit", commitCase);
  bindCommitInputs();
}

bootstrapClinicalDemo();
