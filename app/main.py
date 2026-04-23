from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.document import router as document_router
from app.api.routes.clinical import router as clinical_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.governance import router as governance_router
from app.api.routes.health import router as health_router
from app.api.routes.intake import router as intake_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.perception import router as perception_router
from app.api.routes.platform import router as platform_router
from app.api.routes.reason import router as reason_router
from app.api.routes.research import router as research_router
from app.api.routes.review import router as review_router
from app.api.routes.smart_qa import router as smart_qa_router
from app.web.routes import router as web_router

app = FastAPI(
    title="中医智能体平台 MVP",
    description="平台化 MVP：知识中台 + 推理中台 + 临床/科研/研发工作台 + 治理闭环",
    version="0.1.0",
)

# Allow local frontend hosts (Vite/dev tools) to call backend APIs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_origin_regex=r"https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

API_ROUTERS = [
    health_router,
    platform_router,
    knowledge_router,
    intake_router,
    perception_router,
    reason_router,
    research_router,
    smart_qa_router,
    review_router,
    document_router,
    clinical_router,
    feedback_router,
    governance_router,
]

for router in API_ROUTERS:
    app.include_router(router)

# Mirror API routes under /api/* for static deployments (Vercel/Netlify).
api_prefixed_router = APIRouter(prefix="/api")
for router in API_ROUTERS:
    api_prefixed_router.include_router(router)
app.include_router(api_prefixed_router)

app.include_router(web_router)
