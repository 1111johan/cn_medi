const perceptionForm = document.getElementById("perception-form");
const searchForm = document.getElementById("search-form");
const professionalSearchForm = document.getElementById("professional-search-form");
const rndIngestForm = document.getElementById("rnd-ingest-form");
const loadProfStatsBtn = document.getElementById("load-prof-stats");

const perceptionResultBox = document.getElementById("perception-result-box");
const relationEvidenceList = document.getElementById("relation-evidence-list");
const rndIngestResult = document.getElementById("rnd-ingest-result");
const profStatsResult = document.getElementById("prof-stats-result");
const rndDecisionList = document.getElementById("rnd-decision-list");

if (perceptionForm) {
  perceptionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    perceptionResultBox.textContent = "处理中...";

    const formData = new FormData(perceptionForm);
    const payload = {
      image_type: formData.get("image_type"),
      observations: window.tcmApi.parseCsv(formData.get("observations")),
      notes: formData.get("notes") || null,
    };

    try {
      const result = await window.tcmApi.fetchJson("/perception/analyze", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      perceptionResultBox.innerHTML = `
        <strong>识别标签</strong>：${window.tcmApi.escapeHtml((result.labels || []).join("、") || "无")}<br>
        <strong>置信度</strong>：${window.tcmApi.escapeHtml(result.confidence || 0)}<br>
        <strong>异常提示</strong>：${window.tcmApi.escapeHtml((result.alerts || []).join("、") || "无")}
      `;
    } catch (error) {
      window.tcmApi.renderError(perceptionResultBox, error);
    }
  });
}

if (searchForm) {
  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    relationEvidenceList.innerHTML = "<div class='result-box'>处理中...</div>";

    const formData = new FormData(searchForm);
    const q = encodeURIComponent(formData.get("q") || "");

    try {
      const result = await window.tcmApi.fetchJson(`/knowledge/search?q=${q}&top_k=10`);
      renderEvidenceCards(result || [], "local");
      renderDecisionPanel(result || []);
    } catch (error) {
      relationEvidenceList.innerHTML = `<div class='result-box'>请求失败: ${String(error)}</div>`;
    }
  });
}

if (professionalSearchForm) {
  professionalSearchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    relationEvidenceList.innerHTML = "<div class='result-box'>处理中...</div>";

    const formData = new FormData(professionalSearchForm);
    const q = encodeURIComponent(formData.get("q") || "");

    try {
      const result = await window.tcmApi.fetchJson(`/knowledge/professional/search?q=${q}&top_k=10`);
      renderEvidenceCards(result.results || [], "professional");
      renderDecisionPanel(result.results || []);
    } catch (error) {
      relationEvidenceList.innerHTML = `<div class='result-box'>请求失败: ${String(error)}</div>`;
    }
  });
}

if (rndIngestForm) {
  rndIngestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    rndIngestResult.textContent = "处理中...";

    const formData = new FormData(rndIngestForm);
    const payload = {
      source_type: "case",
      title: formData.get("title"),
      content: formData.get("content"),
      tags: window.tcmApi.parseCsv(formData.get("tags")),
      metadata: {
        module: "rnd_workbench",
      },
    };

    try {
      const result = await window.tcmApi.fetchJson("/knowledge/ingest", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(rndIngestResult, result);
      rndIngestForm.reset();
    } catch (error) {
      window.tcmApi.renderError(rndIngestResult, error);
    }
  });
}

if (loadProfStatsBtn) {
  loadProfStatsBtn.addEventListener("click", async () => {
    profStatsResult.textContent = "处理中...";
    try {
      const result = await window.tcmApi.fetchJson("/knowledge/professional/stats");
      window.tcmApi.renderJson(profStatsResult, result);
    } catch (error) {
      window.tcmApi.renderError(profStatsResult, error);
    }
  });
}

function renderEvidenceCards(items, mode) {
  if (!items.length) {
    relationEvidenceList.innerHTML = "<div class='result-box'>暂无匹配结果。</div>";
    return;
  }

  relationEvidenceList.innerHTML = items
    .map((item, idx) => {
      const title = item.title || item.source_path || "untitled";
      const sourceType = item.source_type || mode;
      const snippet = item.snippet || item.content || "";
      const score = typeof item.score === "number" ? item.score : "-";

      return `
      <div class="evidence-item">
        <div class="evidence-head">
          <span>#${idx + 1} ${window.tcmApi.escapeHtml(title)}</span>
          <span class="badge ok">${window.tcmApi.escapeHtml(sourceType)} · ${window.tcmApi.escapeHtml(score)}</span>
        </div>
        <p>${window.tcmApi.escapeHtml(snippet)}</p>
      </div>
    `;
    })
    .join("");
}

function renderDecisionPanel(items) {
  if (!rndDecisionList) return;

  if (!items.length) {
    rndDecisionList.innerHTML = "<div class='result-box'>暂无可用决策建议。</div>";
    return;
  }

  const text = items.map((x) => `${x.title || ""} ${x.snippet || ""}`).join(" ");
  const hasPhlegm = text.includes("痰") || text.includes("湿");
  const hasStasis = text.includes("瘀") || text.includes("血府逐瘀汤");
  const hasQiDef = text.includes("脾虚") || text.includes("气血两虚");

  const rows = [
    {
      title: "配伍建议",
      level: "ok",
      desc: hasPhlegm && hasStasis
        ? "建议优先评估“化痰祛湿 + 活血通络”双通路配伍。"
        : "建议先以单通路配伍验证，再组合扩展。",
    },
    {
      title: "风险禁忌",
      level: "risk",
      desc: hasStasis
        ? "涉及活血方向时，需增加孕期与出血倾向风险校验。"
        : "目前未识别强禁忌，仍需执行人工复核流程。",
    },
    {
      title: "潜在适应证",
      level: "watch",
      desc: hasQiDef
        ? "可关注“痰湿与虚证并见”亚型并分层验证。"
        : "建议围绕胸闷痰多、纳差困重等症群做分层实验。",
    },
  ];

  rndDecisionList.innerHTML = rows
    .map(
      (item) => `
      <div class="stack-item">
        <div class="stack-title"><span>${window.tcmApi.escapeHtml(item.title)}</span><span class="badge ${item.level}">${item.level}</span></div>
        <div class="stack-desc">${window.tcmApi.escapeHtml(item.desc)}</div>
      </div>
    `
    )
    .join("");
}
