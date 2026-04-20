from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import (
    DIGITAL_HUMAN_MODEL_DIR,
    DIGITAL_HUMAN_MODEL_FILE,
    DIGITAL_HUMAN_TEX_DIFFUSE,
    DIGITAL_HUMAN_TEX_METALLIC,
    DIGITAL_HUMAN_TEX_NORMAL,
    DIGITAL_HUMAN_TEX_ROUGHNESS,
)
from app.services.overview_service import overview_service

router = APIRouter(include_in_schema=False)


templates = Jinja2Templates(directory="app/web/templates")


def _resolve_digital_human_asset(asset_name: str) -> Path:
    base_dir = DIGITAL_HUMAN_MODEL_DIR.resolve()
    target = (base_dir / asset_name).resolve()
    if target.parent != base_dir or not target.is_file():
        raise HTTPException(status_code=404, detail="数字人资产不存在")
    return target


@router.get("/", response_class=HTMLResponse)
def platform_home(request: Request) -> HTMLResponse:
    metrics = overview_service.metrics()
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "title": "平台首页",
            "active": "home",
            "metrics": metrics,
        },
    )


@router.get("/workbench/clinical", response_class=HTMLResponse)
def clinical_workbench(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "clinical.html",
        {
            "title": "临床工作台",
            "active": "clinical",
        },
    )


@router.get("/clinical", response_class=HTMLResponse)
def clinical_workbench_alias(request: Request) -> HTMLResponse:
    return clinical_workbench(request)


@router.get("/workbench/research", response_class=HTMLResponse)
def research_workbench(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "research.html",
        {
            "title": "科研传承工作台",
            "active": "research",
        },
    )


@router.get("/research", response_class=HTMLResponse)
def research_workbench_alias(request: Request) -> HTMLResponse:
    return research_workbench(request)


@router.get("/workbench/smart-qa", response_class=HTMLResponse)
def smart_qa_workbench(request: Request) -> HTMLResponse:
    model_ready = (DIGITAL_HUMAN_MODEL_DIR / DIGITAL_HUMAN_MODEL_FILE).is_file()
    return templates.TemplateResponse(
        request,
        "smart_qa.html",
        {
            "title": "智慧问答助手",
            "active": "smart_qa",
            "page_class": "page-smart-qa",
            "digital_human_assets": {
                "base_url": "/assets/digital-human",
                "model_file": DIGITAL_HUMAN_MODEL_FILE,
                "tex_diffuse": DIGITAL_HUMAN_TEX_DIFFUSE,
                "tex_normal": DIGITAL_HUMAN_TEX_NORMAL,
                "tex_roughness": DIGITAL_HUMAN_TEX_ROUGHNESS,
                "tex_metallic": DIGITAL_HUMAN_TEX_METALLIC,
                "ready": model_ready,
            },
        },
    )


@router.get("/smart-qa", response_class=HTMLResponse)
def smart_qa_workbench_alias(request: Request) -> HTMLResponse:
    return smart_qa_workbench(request)


@router.get("/qa-assistant", response_class=HTMLResponse)
def smart_qa_workbench_alias_2(request: Request) -> HTMLResponse:
    return smart_qa_workbench(request)


@router.get("/assets/digital-human/{asset_name}", include_in_schema=False)
def digital_human_asset(asset_name: str) -> FileResponse:
    target = _resolve_digital_human_asset(asset_name)
    return FileResponse(path=target)


@router.get("/workbench/rnd", response_class=HTMLResponse)
def rnd_workbench(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "rnd.html",
        {
            "title": "中药研发工作台",
            "active": "rnd",
        },
    )


@router.get("/rnd", response_class=HTMLResponse)
def rnd_workbench_alias(request: Request) -> HTMLResponse:
    return rnd_workbench(request)


@router.get("/admin", response_class=HTMLResponse)
def admin_console(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "operations.html",
        {
            "title": "运营治理驾驶舱",
            "active": "operations",
        },
    )


@router.get("/middle/knowledge", response_class=HTMLResponse)
def knowledge_center(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "knowledge_center.html",
        {
            "title": "知识中台",
            "active": "knowledge_center",
        },
    )


@router.get("/knowledge", response_class=HTMLResponse)
def knowledge_center_alias(request: Request) -> HTMLResponse:
    return knowledge_center(request)


@router.get("/middle/reasoning", response_class=HTMLResponse)
def reasoning_center(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "reasoning_center.html",
        {
            "title": "推理中台",
            "active": "reasoning_center",
        },
    )


@router.get("/reasoning", response_class=HTMLResponse)
def reasoning_center_alias(request: Request) -> HTMLResponse:
    return reasoning_center(request)


@router.get("/review/expert", response_class=HTMLResponse)
def expert_review_center(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "expert_review.html",
        {
            "title": "专家审核中心",
            "active": "expert_review",
        },
    )


@router.get("/expert-review", response_class=HTMLResponse)
def expert_review_center_alias(request: Request) -> HTMLResponse:
    return expert_review_center(request)


@router.get("/governance/operations", response_class=HTMLResponse)
def operations_console(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "operations.html",
        {
            "title": "运营治理驾驶舱",
            "active": "operations",
        },
    )


@router.get("/operations", response_class=HTMLResponse)
def operations_console_alias(request: Request) -> HTMLResponse:
    return operations_console(request)
