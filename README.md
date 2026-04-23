# 中医智能体平台 MVP

基于 `中医智能体平台MVP方案_平台版.docx` 搭建的可运行项目骨架，覆盖：

- 一底座：统一服务入口（FastAPI）
- 两中台：知识中台、智能推理中台
- 三场景：临床工作台、科研传承工作台、中药研发工作台
- 一治理：反馈回流 + 全流程审计

## 1. 项目结构

```text
tcm-agent-platform/
├── app/
│   ├── api/routes/           # 核心接口
│   ├── core/                 # 配置、存储、审计
│   ├── models/               # Pydantic 数据模型
│   ├── services/             # 中台服务实现
│   ├── main.py               # 入口
│   └── web/                  # 页面模板和静态资源
├── data/                     # 知识、反馈、审计数据（本地文件）
├── scripts/seed_demo_data.py # Demo 数据入库脚本
└── requirements.txt
```

## 2. 快速启动

```bash
cd tcm-agent-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 2.1 Vite 前端部署（Vercel 推荐）

仓库使用“Vite 静态前端 + 根目录 `api/*.py` FastAPI 函数”方式部署到 Vercel。
其中：

- 静态站点产物来自 `frontend/dist`
- `/api/*` 由根目录 `api/index.py`、`api/[...path].py` 暴露 FastAPI
- `api-static/*` 由 `scripts/export_static_api_snapshots.py` 在构建期导出

本地预览：

```bash
cd frontend
npm install
npm run dev
```

生产构建：

```bash
npm run build:frontend
```

如需对接后端 API，请在 `frontend/.env`（或 Vercel 环境变量）配置：

```bash
VITE_API_BASE=/api
```

Vercel 配置要求：

- Root Directory 必须是仓库根目录，不能设成 `frontend/`
- Build Command 应为 `npm run build:frontend`
- Output Directory 应为 `frontend/dist`
- 仓库根目录必须保留 `api/index.py` 作为单一 FastAPI 入口；`vercel.json` 会把 `/api/(.*)` rewrite 到它

> 说明：Vercel 会使用根目录 `vercel.json`，先导出 `api-static`，再构建 `frontend/dist`，同时自动识别根目录 `api/*.py` 为 Python Functions。

线上自检：

```bash
python3 scripts/check_vercel_deploy.py https://your-vercel-domain.vercel.app
```

你应至少看到：

- `/api/health` 返回 `200`
- `/api-static/knowledge/list.json` 返回 `200`
- `/api-static/knowledge/professional/stats.json` 返回 `200`

如果仍异常，优先检查：

- Vercel Dashboard -> Project Settings -> General -> Root Directory
- Vercel Dashboard -> Project Settings -> Build & Development Settings 是否覆盖了仓库里的 `vercel.json`
- Vercel Dashboard -> Deployments -> 当前部署 -> Build Logs / Function Logs

CloudBase / CNB 构建（根目录执行）：

```bash
npm install
npm run build
```

产物目录：`dist/`（根目录），可直接作为静态站点发布目录。

CloudBase 动态 API（Python HTTP 云函数）：

```bash
python3 scripts/build_cloudbase_http_function.py
bash scripts/deploy_cloudbase_api.sh lung-4g441e9m7f055d4e
```

说明：

- 前端生产环境默认走同域 `"/api"`，见 `frontend/.env.production`
- `scripts/deploy_cloudbase_api.sh` 会使用 `tcb fn deploy ... --httpFn --path /api`
- 静态站点继续通过 `tcb hosting deploy` 发布到 `/cn-medic`

如需指定专业中医数据库目录（默认读取项目同级目录下 `中医药`）：

```bash
export TCM_PRO_DATA_DIR="/Users/xuai/Desktop/cursor—file/cn_mdecine/中医药"
```

项目启动时会自动读取根目录下 `.env.local` / `.env`，可在其中配置模型与三方 API Key。

DeepSeek 接入示例（`.env.local`）：

```bash
PRIMARY_LLM_PROVIDER=deepseek
PRIMARY_LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-xxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

VPN / 代理网络场景（可选）：

```bash
# 例如 Clash / V2Ray 本地代理端口
DEEPSEEK_PROXY_URL=http://127.0.0.1:7890

# 保证本地前后端联调不走代理
NO_PROXY=127.0.0.1,localhost

# 若 VPN 注入自签名证书导致 SSL 失败，可临时开启
DEEPSEEK_DISABLE_SSL_VERIFY=1
```

启动后访问：

- 平台首页：`http://127.0.0.1:8000/`
- 临床工作台：`http://127.0.0.1:8000/workbench/clinical`
- 科研工作台：`http://127.0.0.1:8000/workbench/research`
- 智慧问答：`http://127.0.0.1:8000/workbench/smart-qa`
- 中药研发：`http://127.0.0.1:8000/workbench/rnd`
- 知识中台：`http://127.0.0.1:8000/middle/knowledge`
- 推理中台：`http://127.0.0.1:8000/middle/reasoning`
- 专家审核：`http://127.0.0.1:8000/review/expert`
- 运营治理：`http://127.0.0.1:8000/governance/operations`
- Swagger：`http://127.0.0.1:8000/docs`

兼容旧路径（避免 404）：`/clinical`、`/research`、`/rnd`、`/knowledge`、`/reasoning`、`/expert-review`、`/operations`、`/smart-qa`、`/qa-assistant`

## 3. 已实现接口（对应方案文档）

- `POST /knowledge/ingest` 知识入库
- `GET /knowledge/professional/stats` 专业中医数据库索引状态
- `POST /knowledge/professional/rebuild` 重建专业中医数据库（SQLite）
- `POST /intake/parse` 接诊结构化抽取
- `POST /perception/analyze` 多模态感知（MVP 规则模拟）
- `POST /reason/syndrome` 证候推理与排序
- `POST /reason/formula` 方药草案
- `POST /research/qa` 科研问答与证据回链
- `POST /document/draft` 文书草稿生成
- `POST /feedback/submit` 反馈回流
- `GET /governance/audit` 审计日志查询
- `GET /platform/overview` 平台指标概览
- `GET /platform/dashboard` 平台驾驶舱数据
- `GET /platform/global-search` 全局检索（知识/规则/审核/审计）
- `GET /review/tasks` 专家审核任务列表
- `POST /review/tasks/{task_id}/decision` 专家审核决策
- `POST /reason/trace` 推理链路可解释输出
- `POST /feedback/loop-action` 闭环动作（会诊/教学案例/规则库/再训练池）
- `GET /smart-qa/scenarios` 智慧问答场景模板
- `POST /smart-qa/ask` 智慧问答（含边界控制、场景步骤、数字人播报脚本）
- `POST /smart-qa/task-execute` 智慧问答任务执行（文书生成/专家复核/闭环动作）

## 4. 页面入口（9 页平台结构）

- 平台首页：平台控制塔、三场景入口、趋势与任务队列
- 临床辅助工作台：患者队列 + 四诊证据 + 神经符号推理 + 方药协作 + 闭环动作
- 科研传承工作台：证据问答 + 术语映射 + 图谱摘要 + 案例沉淀
- 智慧问答数字人：多模态咨询 + 场景化建议 + 语音播报 + 边界控制
- 中药研发工作台：多模态输入 + 关系检索 + 研发决策区
- 知识中台：对象运营、关系摘要、版本治理动作
- 推理中台：推理链调试、规则版本、发布控制
- 专家审核中心：审核任务、证据展开、仲裁动作
- 运营治理驾驶舱：跨场景指标、风险审计、规则与版本看板

## 5. MVP 说明

- 当前为规则+检索式可运行版本，重点验证“平台骨架与闭环流程”。
- `reason`、`research`、`smart-qa` 已接入专业中医数据库检索（SQLite 索引 + 证据引用分析）。
- 未实现真实模型推理与医疗级处方决策，所有输出均需医生确认。
- 数据存储为本地 JSON/JSONL，便于替换到数据库与消息队列。

## 6. 可选演示脚本

启动服务后运行：

```bash
python scripts/seed_demo_data.py
```

会向知识中台写入示例数据，并触发一次智慧问答与闭环任务执行。

全功能烟测（页面 + API + 闭环动作）：

```bash
python scripts/smoke_test_all.py
```

重建“中医药”目录数据库索引（首次建议执行）：

```bash
python scripts/build_professional_db.py
```

## 7. 设计交付文档

- 智慧问答单页面高保真交付说明：`docs/smart_qa_single_page_handoff.md`
