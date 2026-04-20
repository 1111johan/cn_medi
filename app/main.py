from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.document import router as document_router
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

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

app.include_router(health_router)
app.include_router(platform_router)
app.include_router(knowledge_router)
app.include_router(intake_router)
app.include_router(perception_router)
app.include_router(reason_router)
app.include_router(research_router)
app.include_router(smart_qa_router)
app.include_router(review_router)
app.include_router(document_router)
app.include_router(feedback_router)
app.include_router(governance_router)

app.include_router(web_router)
