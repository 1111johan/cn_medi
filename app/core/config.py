from __future__ import annotations

import os
from pathlib import Path


def _load_local_env() -> None:
    """Load key=value pairs from .env.local / .env if present."""
    root = Path(__file__).resolve().parents[2]
    for filename in (".env.local", ".env"):
        path = root / filename
        if not path.exists() or not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


_load_local_env()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 默认读取项目外层目录下的“中医药”数据库，可用 TCM_PRO_DATA_DIR 覆盖。
PROFESSIONAL_DATA_DIR = Path(
    os.getenv("TCM_PRO_DATA_DIR", str(BASE_DIR.parent / "中医药"))
).resolve()

DEFAULT_DIGITAL_HUMAN_DIR = BASE_DIR.parent / "34f07a1c-f5e2-4f65-8325-5137df12fd53"
DIGITAL_HUMAN_MODEL_DIR = Path(
    os.getenv("DIGITAL_HUMAN_MODEL_DIR", str(DEFAULT_DIGITAL_HUMAN_DIR))
).resolve()
DIGITAL_HUMAN_MODEL_FILE = os.getenv("DIGITAL_HUMAN_MODEL_FILE", "base.obj")
DIGITAL_HUMAN_TEX_DIFFUSE = os.getenv("DIGITAL_HUMAN_TEX_DIFFUSE", "texture_diffuse.png")
DIGITAL_HUMAN_TEX_NORMAL = os.getenv("DIGITAL_HUMAN_TEX_NORMAL", "texture_normal.png")
DIGITAL_HUMAN_TEX_ROUGHNESS = os.getenv("DIGITAL_HUMAN_TEX_ROUGHNESS", "texture_roughness.png")
DIGITAL_HUMAN_TEX_METALLIC = os.getenv("DIGITAL_HUMAN_TEX_METALLIC", "texture_metallic.png")

PRIMARY_LLM_PROVIDER = os.getenv("PRIMARY_LLM_PROVIDER", "openrouter")
PRIMARY_LLM_MODEL = os.getenv("PRIMARY_LLM_MODEL", "openrouter/openai/gpt-4.1-mini")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "25"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_CHAT_MODEL = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SHUCHONG_API_KEY = os.getenv("SHUCHONG_API_KEY", "")
FAL_API_KEY = os.getenv("FAL_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_APP_ID = os.getenv("DASHSCOPE_APP_ID", "")

KNOWLEDGE_FILE = DATA_DIR / "knowledge_objects.json"
FEEDBACK_FILE = DATA_DIR / "feedback_records.json"
AUDIT_FILE = DATA_DIR / "audit_records.jsonl"
REVIEW_TASK_FILE = DATA_DIR / "review_tasks.json"

SYNDROME_RULES = {
    "气血两虚": {
        "symptoms": ["乏力", "心悸", "失眠", "面色萎黄", "头晕", "食少", "自汗"],
        "tongue_tags": ["舌淡", "苔薄"],
        "pulse_tags": ["脉细弱", "脉弱"],
        "therapy": "益气养血，健脾安神",
        "formula": "归脾汤",
        "mods": ["心悸明显可酌加炙甘草", "失眠明显可加酸枣仁、夜交藤"],
    },
    "痰湿瘀阻": {
        "symptoms": ["胸闷", "痰多", "体胖", "纳呆", "肢体困重", "舌体胖大"],
        "tongue_tags": ["苔腻", "舌胖", "舌暗"],
        "pulse_tags": ["脉滑", "脉涩"],
        "therapy": "化痰祛湿，活血通络",
        "formula": "二陈汤合血府逐瘀汤",
        "mods": ["痰多可加瓜蒌、胆南星", "瘀象明显可加丹参、赤芍"],
    },
    "脾虚痰瘀": {
        "symptoms": ["倦怠", "食后腹胀", "大便溏", "痰多", "肢困", "面色晦滞"],
        "tongue_tags": ["舌淡胖", "苔白腻"],
        "pulse_tags": ["脉濡", "脉涩"],
        "therapy": "健脾化痰，活血化瘀",
        "formula": "六君子汤合桃红四物汤加减",
        "mods": ["腹胀明显可加木香、砂仁", "便溏明显可加炒薏苡仁"],
    },
}

DEFAULT_KNOWLEDGE = [
    {
        "source_type": "classic",
        "title": "《黄帝内经》脾主运化",
        "content": "脾为后天之本，主运化水谷精微。脾虚则生痰湿，久则可兼瘀。",
        "tags": ["脾虚", "痰湿", "病机"],
        "metadata": {"book": "黄帝内经"},
    },
    {
        "source_type": "guideline",
        "title": "中医内科证候辨治通用原则",
        "content": "辨证需遵循证据链：症状体征、舌脉信息、病程演变、治法方药一致性。",
        "tags": ["辨证", "证据链", "治法"],
        "metadata": {"version": "MVP"},
    },
    {
        "source_type": "formula",
        "title": "归脾汤应用要点",
        "content": "归脾汤常用于气血不足、心脾两虚所致心悸失眠、乏力纳差等。",
        "tags": ["归脾汤", "气血两虚"],
        "metadata": {"category": "方剂"},
    },
    {
        "source_type": "formula",
        "title": "二陈汤合血府逐瘀汤应用要点",
        "content": "二陈汤偏于化痰祛湿，血府逐瘀汤偏于活血行气，合方可用于痰瘀互结。",
        "tags": ["痰湿瘀阻", "方药"],
        "metadata": {"category": "方剂"},
    },
    {
        "source_type": "paper",
        "title": "中医证候与现代研究映射示例",
        "content": "可将症状聚类与证候标签联动，用于科研探索和临床辅助决策。",
        "tags": ["科研", "证候", "映射"],
        "metadata": {"type": "review"},
    },
]
