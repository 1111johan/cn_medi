const qaForm = document.getElementById("qa-form");
const modeSelect = document.getElementById("qa-mode");
const scenarioSelect = document.getElementById("qa-scenario-select");
const questionInput = document.getElementById("qa-question");
const filesInput = document.getElementById("qa-files");
const hintInput = document.getElementById("qa-attachment-hint");

const chatStream = document.getElementById("qa-chat-stream");

const conversationTitleNode = document.getElementById("conversation-title");
const conversationTagsNode = document.getElementById("conversation-tags");
const speechScriptNode = document.getElementById("qa-speech-script");
const uploadListNode = document.getElementById("qa-upload-list");

const panelResults = document.getElementById("panel-results");
const panelEvidence = document.getElementById("panel-evidence");
const panelGraph = document.getElementById("panel-graph");
const panelTasks = document.getElementById("panel-tasks");

const avatarNode = document.getElementById("dh-avatar");
const avatarFallbackNode = document.getElementById("dh-avatar-fallback");
const avatarStateBadge = document.getElementById("dh-state-badge");
const avatarStateMain = document.getElementById("avatar-state-main");
const avatarStateDesc = document.getElementById("avatar-state-desc");
const transcriptNode = document.getElementById("qa-transcript");
const transcriptTagsNode = document.getElementById("qa-transcript-tags");

const modelChipNode = document.getElementById("qa-model-chip");

const btnActionVoice = document.getElementById("action-voice");
const btnActionUploadTongue = document.getElementById("action-upload-tongue");
const btnActionUploadRecord = document.getElementById("action-upload-record");
const btnActionSwitchAvatar = document.getElementById("action-switch-avatar");
const btnActionPlay = document.getElementById("action-play");
const btnActionStop = document.getElementById("action-stop");

const btnToolImage = document.getElementById("tool-image");
const btnToolFile = document.getElementById("tool-file");
const btnToolMic = document.getElementById("tool-mic");
const btnNewSession = document.getElementById("new-session-btn");

const autoSpeakCheckbox = document.getElementById("qa-auto-speak");
const modePills = Array.from(document.querySelectorAll("#qa-mode-segment .mode-pill"));
const tabButtons = Array.from(document.querySelectorAll("#result-tabs .tab-btn"));
const tabPanels = Array.from(document.querySelectorAll(".tab-panel"));

let lastSpeechText = "";
let recognition = null;
let scenarioCatalog = [];
let altPersona = false;
let latestResult = null;
let latestQuestion = "";
let currentCaseId = "";
let activeModelName = "岐衡·太乙中医大模型";

function setAvatarFallbackText(text) {
  if (!avatarFallbackNode) return;
  const tipNode = avatarFallbackNode.querySelector(".fallback-tip");
  if (tipNode) {
    tipNode.textContent = text;
  }
}

async function initDigitalHumanViewer() {
  if (!avatarNode) return;
  avatarNode.classList.add("no-digital-human");
  setAvatarFallbackText("智能问答助手已就绪");
}

function setPageState(state, mainText, descText) {
  const map = {
    welcome: { badge: "待机", className: "calm" },
    listening: { badge: "倾听", className: "calm" },
    thinking: { badge: "思考", className: "calm" },
    answering: { badge: "回答", className: "calm" },
    caution: { badge: "风险提示", className: "serious" },
  };

  const hit = map[state] || map.welcome;

  if (avatarStateBadge) avatarStateBadge.textContent = hit.badge;
  if (avatarNode) {
    avatarNode.classList.remove("calm", "serious");
    avatarNode.classList.add(hit.className);
  }

  if (avatarStateMain && mainText) avatarStateMain.textContent = mainText;
  if (avatarStateDesc && descText) avatarStateDesc.textContent = descText;
}

function setModelChip(riskLevel, modelName) {
  if (!modelChipNode) return;
  if (modelName) {
    activeModelName = String(modelName);
  }
  if (riskLevel === "caution") {
    modelChipNode.textContent = `模型状态：${activeModelName}（边界控制中）`;
    modelChipNode.classList.add("risk");
  } else {
    modelChipNode.textContent = `模型状态：${activeModelName}（online）`;
    modelChipNode.classList.remove("risk");
  }
}

function appendMessage(role, content, meta = "") {
  if (!chatStream) return;
  const node = document.createElement("div");
  node.className = `chat-message ${role}`;

  const roleText = role === "user" ? "用户" : "智能助手";
  node.innerHTML = `
    <div class="chat-role">${window.tcmApi.escapeHtml(roleText)}${meta ? ` · ${window.tcmApi.escapeHtml(meta)}` : ""}</div>
    <div class="chat-content">${window.tcmApi.escapeHtml(content).replace(/\n/g, "<br>")}</div>
  `;

  chatStream.appendChild(node);
  chatStream.scrollTop = chatStream.scrollHeight;
}

function replaceLastAssistant(content) {
  if (!chatStream) return;
  const list = chatStream.querySelectorAll(".chat-message.assistant");
  const target = list[list.length - 1];
  if (!target) {
    appendMessage("assistant", content);
    return;
  }

  const contentNode = target.querySelector(".chat-content");
  if (contentNode) {
    contentNode.innerHTML = window.tcmApi.escapeHtml(content).replace(/\n/g, "<br>");
  }

  chatStream.scrollTop = chatStream.scrollHeight;
}

function renderConversationMeta(result) {
  if (conversationTitleNode) {
    conversationTitleNode.textContent = result.conversation_title || "智能问答会话";
  }

  if (!conversationTagsNode) return;
  const tags = (result.session_tags || []).slice(0, 3);
  conversationTagsNode.innerHTML = tags
    .map((item) => `<span class="tag-chip">${window.tcmApi.escapeHtml(item)}</span>`)
    .join("");
}

function renderResultsPanel(result) {
  if (!panelResults) return;
  const card = result.result_cards || {};
  const syndromeRows = (card.syndrome_candidates || [])
    .map((item) => `<div class="kv-row"><span>${window.tcmApi.escapeHtml(item.name)}</span><strong>${window.tcmApi.escapeHtml(String(item.score))}</strong></div>`)
    .join("");

  const therapyRows = (card.therapy_suggestions || [])
    .map((item) => `<li>${window.tcmApi.escapeHtml(item)}</li>`)
    .join("");

  const riskRows = (card.risk_prompts || [])
    .map((item) => `<li>${window.tcmApi.escapeHtml(item)}</li>`)
    .join("");

  const symptoms = (card.recognized_symptoms || []).join("、") || "无";
  const tongue = (card.tongue_pulse?.tongue || []).join("、") || "未识别";
  const pulse = (card.tongue_pulse?.pulse || []).join("、") || "未识别";
  const missing = (result.missing_items || []).join("、") || "无";

  panelResults.innerHTML = `
    <div class="panel-card"><h4>主诉摘要</h4><p>${window.tcmApi.escapeHtml(card.chief_complaint_summary || "未生成")}</p></div>
    <div class="panel-card"><h4>已识别症状</h4><p>${window.tcmApi.escapeHtml(symptoms)}</p></div>
    <div class="panel-card"><h4>舌象/脉象</h4><p>舌象：${window.tcmApi.escapeHtml(tongue)}<br>脉象：${window.tcmApi.escapeHtml(pulse)}</p></div>
    <div class="panel-card"><h4>证候候选排序</h4>${syndromeRows || "<p>暂无候选</p>"}</div>
    <div class="panel-card"><h4>治法建议</h4><ul>${therapyRows || "<li>待生成</li>"}</ul></div>
    <div class="panel-card"><h4>方药草案</h4><p>${window.tcmApi.escapeHtml(card.formula_draft?.name || "待生成")}</p><p class="tiny-note">${window.tcmApi.escapeHtml(card.formula_draft?.note || "")}</p></div>
    <div class="panel-card"><h4>风险提示</h4><ul>${riskRows || "<li>暂无</li>"}</ul></div>
    <div class="panel-card"><h4>当前缺失项</h4><p>${window.tcmApi.escapeHtml(missing)}</p></div>
  `;
}

function renderEvidencePanel(result) {
  if (!panelEvidence) return;
  const evidences = result.evidences || [];
  if (!evidences.length) {
    panelEvidence.innerHTML = "<div class='panel-card'><p>暂无证据命中。</p></div>";
    return;
  }

  panelEvidence.innerHTML = evidences
    .map(
      (item, idx) => `
      <div class="panel-card">
        <h4>#${idx + 1} ${window.tcmApi.escapeHtml(item.title || "")}</h4>
        <p>${window.tcmApi.escapeHtml(item.snippet || "")}</p>
        <div class="tiny-note">来源：${window.tcmApi.escapeHtml(item.source_type || "")}</div>
      </div>
    `
    )
    .join("");
}

function renderGraphPanel(result) {
  if (!panelGraph) return;
  const links = result.graph_links || [];
  if (!links.length) {
    panelGraph.innerHTML = "<div class='panel-card'><p>暂无图谱关系。</p></div>";
    return;
  }

  panelGraph.innerHTML = links
    .map(
      (item) => `
      <div class="panel-card graph-line">
        <span class="node">${window.tcmApi.escapeHtml(item.source || "")}</span>
        <span class="edge">${window.tcmApi.escapeHtml(item.relation || "关联")}</span>
        <span class="node">${window.tcmApi.escapeHtml(item.target || "")}</span>
      </div>
    `
    )
    .join("");
}

function markTaskDone(button, status = "done") {
  const card = button?.closest(".task-card");
  if (!card) return;
  card.classList.remove("ready", "pending", "urgent");
  card.classList.add(status);
}

async function executeTask(action, buttonNode) {
  if (!latestResult) return;

  const payload = {
    action,
    question: latestQuestion,
    scenario: latestResult.scenario || scenarioSelect.value || "",
    case_id: currentCaseId,
    extracted_fields: latestResult.extracted_fields || {},
    result_cards: latestResult.result_cards || {},
    evidences: latestResult.evidences || [],
  };

  buttonNode.disabled = true;
  buttonNode.textContent = "执行中...";

  try {
    const result = await window.tcmApi.fetchJson("/smart-qa/task-execute", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (result.draft && speechScriptNode) {
      speechScriptNode.textContent = result.draft;
    } else if (speechScriptNode && result.message) {
      speechScriptNode.textContent = result.message;
    }

    markTaskDone(buttonNode, result.task_status === "pending" ? "pending" : "done");
    buttonNode.textContent = result.task_status === "pending" ? "待补齐" : "已完成";
  } catch (error) {
    buttonNode.disabled = false;
    buttonNode.textContent = `执行：${action}`;
  }
}

function bindTaskButtons() {
  if (!panelTasks) return;
  panelTasks.querySelectorAll(".execute-task-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action || "";
      if (!action) return;
      executeTask(action, btn);
    });
  });
}

function renderTasksPanel(result) {
  if (!panelTasks) return;
  const tasks = result.workflow_tasks || [];
  if (!tasks.length) {
    panelTasks.innerHTML = "<div class='panel-card'><p>暂无任务建议。</p></div>";
    return;
  }

  panelTasks.innerHTML = tasks
    .map(
      (item, idx) => `
      <div class="panel-card task-card ${window.tcmApi.escapeHtml(String(item.status || "ready"))}" data-task-index="${idx}">
        <div class="task-head">
          <span>${window.tcmApi.escapeHtml(item.title || "")}</span>
          <span class="badge ${item.status === "urgent" ? "risk" : item.status === "pending" ? "watch" : "ok"}">${window.tcmApi.escapeHtml(item.priority || "P1")}</span>
        </div>
        <p>${window.tcmApi.escapeHtml(item.detail || "")}</p>
        <button type="button" class="mini-icon-btn execute-task-btn" data-action="${window.tcmApi.escapeHtml(item.action || "open")}">执行：${window.tcmApi.escapeHtml(item.action || "open")}</button>
      </div>
    `
    )
    .join("");

  bindTaskButtons();
}

function renderUploadList() {
  if (!uploadListNode) return;
  const files = Array.from(filesInput.files || []);
  if (!files.length) {
    uploadListNode.innerHTML = "<div class='result-box'>尚未选择文件。</div>";
    return;
  }

  uploadListNode.innerHTML = files
    .map((file) => {
      const type = resolveFileType(file);
      return `
      <div class="stack-item">
        <div class="stack-title">
          <span>${window.tcmApi.escapeHtml(file.name)}</span>
          <span class="badge watch">${window.tcmApi.escapeHtml(type)}</span>
        </div>
        <div class="stack-desc">${Math.round(file.size / 1024)} KB</div>
      </div>
    `;
    })
    .join("");
}

function resolveFileType(file) {
  const mime = String(file.type || "").toLowerCase();
  const name = String(file.name || "").toLowerCase();
  if (mime.startsWith("image/") || /\.(jpg|jpeg|png|bmp|gif|webp)$/.test(name)) return "image";
  if (mime.startsWith("audio/") || /\.(wav|mp3|m4a|aac)$/.test(name)) return "audio";
  if (/\.(pdf|doc|docx|txt|md)$/.test(name)) return "document";
  return "other";
}

function buildAttachments() {
  const hint = (hintInput?.value || "").trim() || null;
  return Array.from(filesInput.files || []).map((file) => ({
    name: file.name,
    file_type: resolveFileType(file),
    text_hint: hint,
  }));
}

function updateTranscript(extracted) {
  if (!transcriptNode || !transcriptTagsNode) return;

  const symptoms = extracted?.symptoms || [];
  const tongue = extracted?.tongue_tags || [];
  const pulse = extracted?.pulse_tags || [];
  const missing = extracted?.missing_items || [];

  const text = [];
  if (symptoms.length) text.push(`已识别症状：${symptoms.join("、")}`);
  if (tongue.length) text.push(`舌象：${tongue.join("、")}`);
  if (pulse.length) text.push(`脉象：${pulse.join("、")}`);

  transcriptNode.textContent = text.length ? text.join("；") : "暂无可用转写内容";

  const tagList = [];
  if (symptoms.length) tagList.push(...symptoms.slice(0, 3));
  if (missing.length) tagList.push(`待确认:${missing.slice(0, 2).join("/")}`);

  transcriptTagsNode.innerHTML = tagList
    .map((item) => `<span class="tag-chip">${window.tcmApi.escapeHtml(item)}</span>`)
    .join("");
}

function switchTab(tabName) {
  tabButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });
  tabPanels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === tabName);
  });
}

function startVoiceRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    setPageState("welcome", "浏览器不支持语音识别", "请改用文字输入。");
    return;
  }

  if (!recognition) {
    recognition = new SR();
    recognition.lang = "zh-CN";
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setPageState("listening", "正在倾听", "请继续描述主要症状与病史。");
      modeSelect.value = "voice";
    };

    recognition.onresult = (event) => {
      const chunks = [];
      for (let i = 0; i < event.results.length; i += 1) {
        chunks.push(event.results[i][0].transcript);
      }
      const transcript = chunks.join("").trim();
      if (transcript) {
        questionInput.value = transcript;
      }
    };

    recognition.onend = () => {
      setPageState("welcome", "待机中，随时可咨询", "可继续语音输入或直接发送问题。");
    };

    recognition.onerror = () => {
      setPageState("welcome", "语音识别失败", "请重试或改用文字输入。");
    };
  }

  recognition.start();
}

function stopSpeaking() {
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  if (avatarNode) avatarNode.classList.remove("speaking");
}

function speak(text) {
  if (!window.speechSynthesis || !text) return;
  stopSpeaking();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  const voices = window.speechSynthesis.getVoices();
  const zhVoice = voices.find((v) => String(v.lang || "").toLowerCase().includes("zh"));
  if (zhVoice) utterance.voice = zhVoice;

  utterance.onstart = () => avatarNode?.classList.add("speaking");
  utterance.onend = () => avatarNode?.classList.remove("speaking");
  utterance.onerror = () => avatarNode?.classList.remove("speaking");

  window.speechSynthesis.speak(utterance);
}

function resetSession() {
  if (chatStream) {
    chatStream.innerHTML = `
      <div class="chat-message assistant">
        <div class="chat-role">智能助手</div>
        <div class="chat-content">会话已重置，请直接输入问题。</div>
      </div>
    `;
  }

  questionInput.value = "";
  filesInput.value = "";
  if (hintInput) hintInput.value = "";

  renderUploadList();
  panelResults.innerHTML = "";
  panelEvidence.innerHTML = "";
  panelGraph.innerHTML = "";
  panelTasks.innerHTML = "";
  latestResult = null;
  latestQuestion = "";
  currentCaseId = "";

  if (speechScriptNode) {
    speechScriptNode.textContent = "提交问题后自动生成回答摘要。";
  }

  updateTranscript({});
  switchTab("results");
  setPageState("welcome", "待机中，随时可咨询", "请输入问题。可以在输入框旁上传图片或文件。");
  setModelChip("safe");
  stopSpeaking();
}

async function loadScenarios() {
  try {
    const data = await window.tcmApi.fetchJson("/smart-qa/scenarios");
    scenarioCatalog = data.scenarios || [];

    scenarioSelect.innerHTML = "<option value=''>自动识别场景</option>" + scenarioCatalog
      .map((item) => `<option value="${window.tcmApi.escapeHtml(item.name)}">${window.tcmApi.escapeHtml(item.name)}</option>`)
      .join("");
  } catch (error) {
    scenarioSelect.innerHTML = "<option value=''>自动识别场景（加载失败）</option>";
    scenarioCatalog = [];
  }
}

function bindEvents() {
  modePills.forEach((pill) => {
    pill.addEventListener("click", () => {
      modePills.forEach((x) => x.classList.remove("active"));
      pill.classList.add("active");
      modeSelect.value = pill.dataset.mode || "text";
    });
  });

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab || "results"));
  });

  scenarioSelect.addEventListener("change", () => {
    // keep selected scenario for payload
  });

  filesInput.addEventListener("change", renderUploadList);

  qaForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const question = (questionInput.value || "").trim();
    if (!question) return;

    const payload = {
      question,
      mode: modeSelect.value,
      scenario: scenarioSelect.value || null,
      attachments: buildAttachments(),
    };

    latestQuestion = question;
    currentCaseId = `qa-${Date.now()}`;

    appendMessage("user", question);
    appendMessage("assistant", "正在思考，请稍候...");
    setPageState("thinking", "正在分析", "正在生成回答。");

    try {
      const result = await window.tcmApi.fetchJson("/smart-qa/ask", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      latestResult = result;

      replaceLastAssistant(result.answer || "");
      renderConversationMeta(result);
      updateTranscript(result.extracted_fields || {});

      renderResultsPanel(result);
      renderEvidencePanel(result);
      renderGraphPanel(result);
      renderTasksPanel(result);

      if (speechScriptNode) {
        speechScriptNode.textContent = result.speech_text || result.answer || "无可播报内容";
      }
      lastSpeechText = result.speech_text || result.answer || "";

      if (result.risk_level === "caution") {
        setPageState("caution", "风险提示模式", result.boundary_notice || "请尽快线下就医");
      } else {
        setPageState("answering", "回答完成", "中间区域仅显示问题与答案。");
      }

      avatarNode?.classList.remove("calm", "serious");
      avatarNode?.classList.add(result.digital_human?.emotion === "serious" ? "serious" : "calm");
      setModelChip(result.risk_level || "safe", result.model_name);

      if (autoSpeakCheckbox?.checked && lastSpeechText) {
        speak(lastSpeechText);
      }
    } catch (error) {
      replaceLastAssistant(`请求失败：${String(error)}`);
      setPageState("welcome", "请求失败", "请稍后重试或换一种问法。");
      setModelChip("caution");
    }
  });

  btnNewSession?.addEventListener("click", resetSession);

  btnActionPlay?.addEventListener("click", () => {
    if (lastSpeechText) speak(lastSpeechText);
  });

  btnActionStop?.addEventListener("click", stopSpeaking);

  btnToolMic?.addEventListener("click", startVoiceRecognition);
  btnActionVoice?.addEventListener("click", startVoiceRecognition);

  btnToolImage?.addEventListener("click", () => {
    filesInput.accept = "image/*";
    filesInput.click();
  });

  btnToolFile?.addEventListener("click", () => {
    filesInput.accept = ".pdf,.doc,.docx,.txt,image/*";
    filesInput.click();
  });

  btnActionUploadTongue?.addEventListener("click", () => {
    filesInput.accept = "image/*";
    filesInput.click();
  });

  btnActionUploadRecord?.addEventListener("click", () => {
    filesInput.accept = ".pdf,.doc,.docx,.txt,image/*";
    filesInput.click();
  });

  btnActionSwitchAvatar?.addEventListener("click", () => {
    altPersona = !altPersona;
    if (altPersona) {
      if (avatarStateDesc) avatarStateDesc.textContent = "当前为专家问答风格：偏临床审核语气。";
      if (avatarStateBadge) avatarStateBadge.textContent = "专家风格";
    } else {
      if (avatarStateDesc) avatarStateDesc.textContent = "当前为标准问答风格：偏患者沟通语气。";
      if (avatarStateBadge) avatarStateBadge.textContent = "待机";
    }
  });
}

async function bootstrap() {
  renderUploadList();
  switchTab("results");
  setPageState("welcome", "待机中，随时可咨询", "请输入问题。可以在输入框旁上传图片或文件。");
  setModelChip("safe");
  await initDigitalHumanViewer();
  await loadScenarios();
  bindEvents();
}

bootstrap();
