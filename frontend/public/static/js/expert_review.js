const filterForm = document.getElementById("er-filter-form");
const taskListNode = document.getElementById("er-task-list");
const detailNode = document.getElementById("er-task-detail");
const decisionForm = document.getElementById("er-decision-form");
const decisionResult = document.getElementById("er-decision-result");
const currentTaskInput = document.getElementById("er-current-task");

let currentTasks = [];

if (filterForm) {
  filterForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await loadTasks();
  });
}

if (decisionForm) {
  decisionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    decisionResult.textContent = "处理中...";

    const formData = new FormData(decisionForm);
    const taskId = formData.get("task_id");
    const payload = {
      action: formData.get("action"),
      comment: formData.get("comment") || null,
    };

    try {
      const result = await window.tcmApi.fetchJson(`/review/tasks/${encodeURIComponent(taskId)}/decision`, {
        method: "POST",
        headers: {
          "x-actor": "expert_reviewer",
        },
        body: JSON.stringify(payload),
      });
      window.tcmApi.renderJson(decisionResult, result);
      await loadTasks();
    } catch (error) {
      window.tcmApi.renderError(decisionResult, error);
    }
  });
}

async function loadTasks() {
  taskListNode.innerHTML = "<div class='result-box'>加载中...</div>";

  const formData = new FormData(filterForm);
  const query = new URLSearchParams();
  ["status", "task_type", "priority"].forEach((k) => {
    const v = String(formData.get(k) || "").trim();
    if (v) query.set(k, v);
  });

  try {
    const result = await window.tcmApi.fetchJson(`/review/tasks?${query.toString()}`);
    currentTasks = result.tasks || [];
    renderStats(result.stats || {});
    renderTaskList(currentTasks);
  } catch (error) {
    taskListNode.innerHTML = `<div class='result-box'>加载失败: ${String(error)}</div>`;
  }
}

function renderStats(stats) {
  document.getElementById("er-pending").textContent = stats.pending || 0;
  document.getElementById("er-escalated").textContent = stats.escalated || 0;
  document.getElementById("er-approved").textContent = stats.approved || 0;
}

function renderTaskList(tasks) {
  if (!tasks.length) {
    taskListNode.innerHTML = "<div class='result-box'>暂无匹配审核任务。</div>";
    detailNode.textContent = "请选择左侧任务查看 AI 初判和证据引用。";
    return;
  }

  taskListNode.innerHTML = tasks
    .map((task) => {
      const statusClass = window.tcmApi.badgeClassByStatus(
        task.status === "pending" ? "watch" : task.status === "approved" ? "healthy" : task.status === "escalated" ? "risk" : "watch"
      );
      return `
      <button class="queue-item" data-task-id="${task.task_id}">
        ${window.tcmApi.escapeHtml(task.title)}
        <br><small>${window.tcmApi.escapeHtml(task.task_type)} · ${window.tcmApi.escapeHtml(task.priority)} · <span class="badge ${statusClass}">${window.tcmApi.escapeHtml(task.status)}</span></small>
      </button>
    `;
    })
    .join("");

  taskListNode.querySelectorAll("button[data-task-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      taskListNode.querySelectorAll("button").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");

      const task = tasks.find((x) => x.task_id === btn.dataset.taskId);
      if (!task) return;

      currentTaskInput.value = task.task_id;
      renderTaskDetail(task);
    });
  });

  taskListNode.querySelector("button[data-task-id]")?.click();
}

function renderTaskDetail(task) {
  const refs = (task.evidence_refs || []).map((x) => `- ${x}`).join("\n");

  detailNode.innerHTML = `
    <strong>任务标题</strong>：${window.tcmApi.escapeHtml(task.title || "")}<br>
    <strong>任务类型</strong>：${window.tcmApi.escapeHtml(task.task_type || "")}<br>
    <strong>优先级</strong>：${window.tcmApi.escapeHtml(task.priority || "")}<br>
    <strong>状态</strong>：${window.tcmApi.escapeHtml(task.status || "")}<br>
    <hr>
    <strong>AI 初判</strong><br>
    ${window.tcmApi.escapeHtml(task.ai_prejudge || "无")}<br><br>
    <strong>争议摘要</strong><br>
    ${window.tcmApi.escapeHtml(task.summary || "无")}<br><br>
    <strong>证据引用</strong><br>
    ${window.tcmApi.escapeHtml(refs || "无").replace(/\n/g, "<br>")}
  `;
}

loadTasks();
