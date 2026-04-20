const qaForm = document.getElementById("qa-form");
const summaryForm = document.getElementById("summary-form");
const researchIngestForm = document.getElementById("research-ingest-form");

const qaAnswer = document.getElementById("qa-answer");
const evidenceList = document.getElementById("evidence-list");
const summaryResult = document.getElementById("summary-result");
const researchIngestResult = document.getElementById("research-ingest-result");
const termMapList = document.getElementById("term-map-list");
const relationGraphList = document.getElementById("relation-graph-list");

let lastQaResult = null;

if (qaForm) {
  qaForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    qaAnswer.textContent = "处理中...";
    evidenceList.innerHTML = "";

    const formData = new FormData(qaForm);
    const payload = {
      question: formData.get("question"),
      scope: formData.get("scope") || null,
      source_types: window.tcmApi.parseCsv(formData.get("source_types")),
    };

    try {
      const result = await window.tcmApi.fetchJson("/research/qa", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      lastQaResult = result;
      renderQaResult(result);
      renderTermMap(result);
      renderRelationGraph(result);
      autoFillResearchIngest(result);
    } catch (error) {
      window.tcmApi.renderError(qaAnswer, error);
    }
  });
}

if (summaryForm) {
  summaryForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    summaryResult.textContent = "处理中...";

    const formData = new FormData(summaryForm);
    const payload = {
      template_type: "research_summary",
      patient_info: {},
      visit_data: {
        question: formData.get("question"),
      },
      reasoning_result: {
        syndrome: formData.get("syndrome"),
        evidence: formData.get("evidence") || "待补充",
        hypothesis: "证候与研究标签存在相关性，建议扩大样本进行验证。",
      },
    };

    try {
      const result = await window.tcmApi.fetchJson("/document/draft", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(summaryResult, result);
    } catch (error) {
      window.tcmApi.renderError(summaryResult, error);
    }
  });
}

if (researchIngestForm) {
  researchIngestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    researchIngestResult.textContent = "处理中...";

    const formData = new FormData(researchIngestForm);
    const payload = {
      source_type: "case",
      title: formData.get("title"),
      content: formData.get("content"),
      tags: window.tcmApi.parseCsv(formData.get("tags")),
      metadata: {
        module: "research_workbench",
        created_by: "research_user",
      },
    };

    try {
      const result = await window.tcmApi.fetchJson("/knowledge/ingest", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(researchIngestResult, result);
    } catch (error) {
      window.tcmApi.renderError(researchIngestResult, error);
    }
  });
}

function renderQaResult(result) {
  qaAnswer.innerHTML = `
    <strong>回答摘要</strong><br>
    ${window.tcmApi.escapeHtml(result.answer || "").replace(/\n/g, "<br>")}
  `;

  const evidences = result.evidences || [];
  if (!evidences.length) {
    evidenceList.innerHTML = "<div class='result-box'>暂无证据链结果。</div>";
    return;
  }

  evidenceList.innerHTML = evidences
    .map(
      (item, idx) => `
      <div class="evidence-item">
        <div class="evidence-head">
          <span>#${idx + 1} ${window.tcmApi.escapeHtml(item.title)}</span>
          <span class="badge ok">${window.tcmApi.escapeHtml(item.source_type)} · ${item.score}</span>
        </div>
        <p>${window.tcmApi.escapeHtml(item.snippet || "")}</p>
      </div>
    `
    )
    .join("");
}

function autoFillResearchIngest(result) {
  if (!researchIngestForm || !result) return;

  const title = researchIngestForm.querySelector('input[name="title"]');
  const content = researchIngestForm.querySelector('textarea[name="content"]');

  if (title && lastQaResult?.evidences?.[0]?.title) {
    title.value = `科研案例：${lastQaResult.evidences[0].title}`;
  }

  if (content) {
    const lines = [];
    lines.push(`问题: ${(document.querySelector('#qa-form textarea[name="question"]')?.value || "").trim()}`);
    lines.push("回答:");
    lines.push(result.answer || "");
    lines.push("证据:");
    (result.evidences || []).slice(0, 5).forEach((ev, idx) => {
      lines.push(`${idx + 1}. [${ev.source_type}] ${ev.title} | ${ev.snippet}`);
    });
    content.value = lines.join("\n");
  }
}

function renderTermMap(result) {
  if (!termMapList) return;
  const answer = String(result.answer || "");
  const evidences = result.evidences || [];

  const mapRules = [
    { classical: "痰湿", modern: "代谢异常/炎症负荷" },
    { classical: "瘀阻", modern: "微循环异常倾向" },
    { classical: "脾虚", modern: "消化吸收功能低下倾向" },
    { classical: "气血两虚", modern: "疲劳综合征样表现" },
    { classical: "胸闷痰多", modern: "呼吸/消化共病相关症状群" },
  ];

  const hits = mapRules.filter((item) => answer.includes(item.classical) || evidences.some((ev) => String(ev.snippet || "").includes(item.classical)));
  if (!hits.length) {
    termMapList.innerHTML = "<div class='result-box'>未识别到稳定术语映射。</div>";
    return;
  }

  termMapList.innerHTML = hits
    .map(
      (item) => `
      <div class="stack-item">
        <div class="stack-title"><span>${window.tcmApi.escapeHtml(item.classical)}</span><span class="badge ok">映射</span></div>
        <div class="stack-desc">${window.tcmApi.escapeHtml(item.modern)}</div>
      </div>
    `
    )
    .join("");
}

function renderRelationGraph(result) {
  if (!relationGraphList) return;

  const evidences = result.evidences || [];
  if (!evidences.length) {
    relationGraphList.innerHTML = "<div class='result-box'>暂无关系摘要。</div>";
    return;
  }

  const nodes = [
    { name: "证候", desc: "基于问题语义和证据聚合输出候选主证。" },
    { name: "治法", desc: "由证候映射到治法原则，要求可解释。" },
    { name: "方药", desc: "由治法映射到方剂，并由证据做支持/反证。"},
    { name: "出处证据", desc: `当前回链证据 ${evidences.length} 条。` },
  ];

  relationGraphList.innerHTML = nodes
    .map(
      (item, idx) => `
      <div class="stack-item">
        <div class="stack-title">
          <span>${idx + 1}. ${window.tcmApi.escapeHtml(item.name)}</span>
          <span class="badge watch">node</span>
        </div>
        <div class="stack-desc">${window.tcmApi.escapeHtml(item.desc)}</div>
      </div>
    `
    )
    .join("");
}
