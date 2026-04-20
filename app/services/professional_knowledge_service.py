from __future__ import annotations

import csv
import hashlib
import html as html_lib
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from app.core.config import PROFESSIONAL_DATA_DIR


STOPWORDS = {
    "的",
    "和",
    "与",
    "及",
    "在",
    "是",
    "请",
    "问",
    "一个",
    "如何",
    "什么",
    "哪些",
    "吗",
    "了",
}

DOMAIN_TERMS = [
    "痰湿瘀阻",
    "脾虚痰瘀",
    "气血两虚",
    "痰湿",
    "瘀阻",
    "辨证",
    "病机",
    "治法",
    "方药",
    "方剂",
    "处方",
    "加减",
    "主诉",
    "现病史",
    "舌质",
    "舌苔",
    "脉象",
    "医案",
    "归脾汤",
    "二陈汤",
    "血府逐瘀汤",
]

SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".json", ".jsonl"}
SUPPORTED_STRUCTURED_EXTENSIONS = {".csv"}
SUPPORTED_HTML_EXTENSIONS = {".html", ".htm"}


class ProfessionalKnowledgeService:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self._records: List[Dict[str, Any]] = []
        self._loaded = False
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return
            self._records = self._load_records()
            self._loaded = True

    def stats(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return {
            "root_dir": str(self.root_dir),
            "available": self.root_dir.exists(),
            "record_count": len(self._records),
        }

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        if not query.strip():
            return []

        terms = self._extract_terms(query)
        results: List[Dict[str, Any]] = []

        for record in self._records:
            score = self._score(query, terms, record)
            if score <= 0:
                continue
            results.append(
                {
                    **record,
                    "score": round(score, 3),
                    "snippet": self._build_snippet(record["content"], terms),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _load_records(self) -> List[Dict[str, Any]]:
        if not self.root_dir.exists():
            return []

        records: List[Dict[str, Any]] = []
        file_paths = [p for p in self.root_dir.rglob("*") if p.is_file()]
        file_paths.sort()

        max_files = int(os.getenv("TCM_PRO_MAX_FILES", "500"))
        max_records = int(os.getenv("TCM_PRO_MAX_RECORDS", "5000"))

        for file_path in file_paths[:max_files]:
            if len(records) >= max_records:
                break

            ext = file_path.suffix.lower()
            try:
                if ext in SUPPORTED_STRUCTURED_EXTENSIONS:
                    docs = self._load_csv_records(file_path)
                elif ext in SUPPORTED_HTML_EXTENSIONS:
                    docs = self._load_html_record(file_path)
                elif ext in SUPPORTED_TEXT_EXTENSIONS:
                    docs = self._load_text_record(file_path)
                else:
                    docs = []
            except Exception:
                continue

            for doc in docs:
                records.append(doc)
                if len(records) >= max_records:
                    break

        return records

    def _load_csv_records(self, file_path: Path) -> List[Dict[str, Any]]:
        text = self._read_text(file_path)
        if not text:
            return []

        lines = text.splitlines()
        if len(lines) <= 1:
            return []

        reader = csv.DictReader(lines)
        docs: List[Dict[str, Any]] = []

        max_rows = int(os.getenv("TCM_PRO_MAX_CSV_ROWS", "400"))
        for idx, row in enumerate(reader, start=1):
            if idx > max_rows:
                break
            fields = self._extract_meaningful_fields(row)
            if not fields:
                continue

            title = row.get("标题") or row.get("title") or f"{file_path.stem}#row{idx}"
            content = "；".join([f"{k}:{v}" for k, v in fields])

            docs.append(
                {
                    "object_id": self._make_object_id(file_path, idx),
                    "title": title,
                    "content": content,
                    "source_type": "professional_csv",
                    "source_path": str(file_path.relative_to(self.root_dir)),
                }
            )

        return docs

    def _load_html_record(self, file_path: Path) -> List[Dict[str, Any]]:
        html_text = self._read_text(file_path)
        if not html_text:
            return []

        # 去除脚本样式
        html_text = re.sub(r"<script[\\s\\S]*?</script>", " ", html_text, flags=re.IGNORECASE)
        html_text = re.sub(r"<style[\\s\\S]*?</style>", " ", html_text, flags=re.IGNORECASE)

        title_match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match and title_match.group(1).strip() else file_path.stem

        plain = re.sub(r"<[^>]+>", " ", html_text)
        plain = html_lib.unescape(plain)
        plain = re.sub(r"\s+", " ", plain).strip()

        if not plain:
            return []

        max_chars = int(os.getenv("TCM_PRO_MAX_HTML_CHARS", "20000"))
        plain = plain[:max_chars]

        return [
            {
                "object_id": self._make_object_id(file_path, 0),
                "title": title,
                "content": plain,
                "source_type": "professional_html",
                "source_path": str(file_path.relative_to(self.root_dir)),
            }
        ]

    def _load_text_record(self, file_path: Path) -> List[Dict[str, Any]]:
        text = self._read_text(file_path)
        if not text:
            return []
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        max_chars = int(os.getenv("TCM_PRO_MAX_TEXT_CHARS", "16000"))
        text = text[:max_chars]

        return [
            {
                "object_id": self._make_object_id(file_path, 0),
                "title": file_path.stem,
                "content": text,
                "source_type": "professional_text",
                "source_path": str(file_path.relative_to(self.root_dir)),
            }
        ]

    def _read_text(self, file_path: Path) -> str:
        encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
        for enc in encodings:
            try:
                return file_path.read_text(encoding=enc)
            except Exception:
                continue
        return ""

    def _extract_meaningful_fields(self, row: Dict[str, Any]) -> List[Tuple[str, str]]:
        preferred_keys = [
            "标题",
            "主诉",
            "现病史",
            "辨证分析",
            "辨证",
            "治法",
            "处方",
            "方药",
            "舌质",
            "舌苔",
            "脉象",
            "摘要",
            "诊断",
            "中医诊断",
            "西医诊断",
            "刻下症",
            "专科检查",
        ]

        fields: List[Tuple[str, str]] = []

        # 优先抽取临床语义字段
        for key in preferred_keys:
            value = row.get(key)
            if value and self._is_meaningful_text(value):
                fields.append((key, self._normalize(value)))

        # 再补充英文特征字段（舌面相关）
        for key, value in row.items():
            if len(fields) >= 14:
                break
            if not value:
                continue
            key_lower = key.lower()
            if key in preferred_keys:
                continue
            if any(flag in key_lower for flag in ("tongue", "coating", "face", "lip", "complexion", "gender", "age")):
                norm_value = self._normalize(str(value))
                if self._is_meaningful_text(norm_value):
                    fields.append((key, norm_value))

        return fields

    def _is_meaningful_text(self, value: Any) -> bool:
        text = self._normalize(str(value))
        if not text:
            return False

        # 过滤纯数值和文件名字段
        if re.fullmatch(r"[+-]?\d+(\.\d+)?", text):
            return False
        if text.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif")):
            return False
        if text in {"absent", "present", "none"}:
            return True
        return len(text) >= 2

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _extract_terms(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
        terms = [w for w in cleaned.split() if len(w) >= 2 and w not in STOPWORDS]
        for term in DOMAIN_TERMS:
            if term in text:
                terms.append(term)

        dedup: List[str] = []
        seen = set()
        for t in terms:
            if t not in seen:
                seen.add(t)
                dedup.append(t)
        return dedup

    def _score(self, query: str, terms: Iterable[str], record: Dict[str, Any]) -> float:
        title = record["title"]
        content = record["content"]

        score = 0.0
        if query in title:
            score += 4.0
        if query in content:
            score += 2.5

        for term in terms:
            if term in title:
                score += 1.7
            if term in content:
                score += 0.8

        return score

    def _build_snippet(self, content: str, terms: Iterable[str], window: int = 96) -> str:
        hit = -1
        for term in terms:
            idx = content.find(term)
            if idx >= 0:
                hit = idx
                break

        if hit < 0:
            return content[:window]

        start = max(0, hit - window // 2)
        end = min(len(content), start + window)
        return content[start:end]

    def _make_object_id(self, path: Path, row_index: int) -> str:
        raw = f"{path.as_posix()}::{row_index}".encode("utf-8")
        return hashlib.md5(raw).hexdigest()


professional_knowledge_service = ProfessionalKnowledgeService(PROFESSIONAL_DATA_DIR)
