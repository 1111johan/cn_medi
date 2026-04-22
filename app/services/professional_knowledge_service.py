from __future__ import annotations

import csv
import hashlib
import html as html_lib
import os
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from app.core.config import DATA_DIR, PROFESSIONAL_DATA_DIR


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
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | SUPPORTED_STRUCTURED_EXTENSIONS | SUPPORTED_HTML_EXTENSIONS

DEFAULT_DB_PATH = DATA_DIR / "professional_knowledge.db"


class ProfessionalKnowledgeService:
    """Build a searchable SQLite database from professional TCM files and query it."""

    def __init__(self, root_dir: Path, db_path: Path | None = None):
        self.root_dir = root_dir
        self.db_path = db_path or Path(os.getenv("TCM_PRO_DB_PATH", str(DEFAULT_DB_PATH)))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._ready = False
        self._last_check_at = 0.0
        self._check_interval_seconds = float(os.getenv("TCM_PRO_REBUILD_CHECK_SECONDS", "30"))

    def stats(self) -> Dict[str, Any]:
        self._ensure_index_ready()
        with self._connect() as conn:
            record_count = conn.execute("SELECT COUNT(*) FROM professional_documents").fetchone()[0]
            signature = self._meta_get(conn, "dataset_signature")
            indexed_at = self._meta_get(conn, "indexed_at")
            indexed_files = int(self._meta_get(conn, "indexed_files") or "0")

        return {
            "root_dir": str(self.root_dir),
            "db_path": str(self.db_path),
            "available": bool(self.root_dir.exists() or int(record_count) > 0),
            "record_count": int(record_count),
            "indexed_files": indexed_files,
            "indexed_at": indexed_at,
            "dataset_signature": signature,
        }

    def rebuild(self) -> Dict[str, Any]:
        self._ensure_index_ready(force=True)
        return self.stats()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        self._ensure_index_ready()
        q = query.strip()
        if not q:
            return []

        terms = self._extract_terms(q)
        like_terms = [q] + terms[:8]

        where_clauses: List[str] = []
        params: List[Any] = []
        for term in like_terms:
            where_clauses.append("(title LIKE ? OR content LIKE ?)")
            kw = f"%{term}%"
            params.extend([kw, kw])

        sql = (
            "SELECT object_id, title, content, source_type, source_path "
            "FROM professional_documents "
            f"WHERE {' OR '.join(where_clauses)} "
            "LIMIT ?"
        )
        params.append(max(top_k * 60, 180))

        results: List[Dict[str, Any]] = []
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        for row in rows:
            title = str(row["title"])
            content = str(row["content"])
            score = self._score(q, terms, {"title": title, "content": content})
            if score <= 0:
                continue
            results.append(
                {
                    "object_id": str(row["object_id"]),
                    "title": title,
                    "source_type": str(row["source_type"]),
                    "source_path": str(row["source_path"]),
                    "score": round(score, 3),
                    "snippet": self._build_snippet(content, terms or [q]),
                }
            )

        if not results and q:
            results = self._fallback_search(q, top_k=top_k, terms=terms)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _fallback_search(self, query: str, top_k: int, terms: List[str]) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT object_id, title, content, source_type, source_path "
                "FROM professional_documents ORDER BY rowid DESC LIMIT ?",
                (max(top_k * 25, 120),),
            ).fetchall()

        results: List[Dict[str, Any]] = []
        for row in rows:
            title = str(row["title"])
            content = str(row["content"])
            score = self._score(query, terms, {"title": title, "content": content})
            if score <= 0:
                continue
            results.append(
                {
                    "object_id": str(row["object_id"]),
                    "title": title,
                    "source_type": str(row["source_type"]),
                    "source_path": str(row["source_path"]),
                    "score": round(score, 3),
                    "snippet": self._build_snippet(content, terms or [query]),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _ensure_index_ready(self, force: bool = False) -> None:
        now = time.time()
        if not force and self._ready and (now - self._last_check_at) < self._check_interval_seconds:
            return

        with self._lock:
            now = time.time()
            if not force and self._ready and (now - self._last_check_at) < self._check_interval_seconds:
                return

            files = self._collect_supported_files()
            signature = self._calculate_signature(files)

            with self._connect() as conn:
                self._init_schema(conn)
                stored_signature = self._meta_get(conn, "dataset_signature")
                existing_count = conn.execute("SELECT COUNT(*) FROM professional_documents").fetchone()[0]

            if (
                not force
                and not self.root_dir.exists()
                and self.db_path.exists()
                and int(existing_count) > 0
            ):
                self._ready = True
                self._last_check_at = time.time()
                return

            if force or (not self.db_path.exists()) or (stored_signature != signature):
                self._rebuild_index(files=files, signature=signature)

            self._ready = True
            self._last_check_at = time.time()

    def _rebuild_index(self, files: List[Path], signature: str) -> None:
        max_records = int(os.getenv("TCM_PRO_MAX_RECORDS", "15000"))

        docs_to_insert: List[Tuple[str, str, str, str, str, str, int]] = []
        for file_path in files:
            if len(docs_to_insert) >= max_records:
                break

            try:
                docs = self._load_docs_from_file(file_path)
            except Exception:
                continue

            rel_path = str(file_path.relative_to(self.root_dir))
            for doc in docs:
                docs_to_insert.append(
                    (
                        str(doc["object_id"]),
                        str(doc["title"]),
                        str(doc["content"]),
                        str(doc["source_type"]),
                        str(doc["source_path"]),
                        rel_path,
                        int(doc.get("row_index", 0)),
                    )
                )
                if len(docs_to_insert) >= max_records:
                    break

        with self._connect() as conn:
            self._init_schema(conn)
            conn.execute("DELETE FROM professional_documents")
            conn.executemany(
                "INSERT OR REPLACE INTO professional_documents "
                "(object_id, title, content, source_type, source_path, source_file, row_index) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                docs_to_insert,
            )
            self._meta_set(conn, "dataset_signature", signature)
            self._meta_set(conn, "indexed_at", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            self._meta_set(conn, "indexed_files", str(len(files)))
            self._meta_set(conn, "root_dir", str(self.root_dir))
            conn.commit()

    def _collect_supported_files(self) -> List[Path]:
        if not self.root_dir.exists():
            return []

        max_files = int(os.getenv("TCM_PRO_MAX_FILES", "5000"))
        files = [
            p
            for p in self.root_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        files.sort()
        return files[:max_files]

    def _calculate_signature(self, files: List[Path]) -> str:
        h = hashlib.sha1()
        h.update(str(self.root_dir).encode("utf-8"))
        for p in files:
            try:
                st = p.stat()
            except OSError:
                continue
            rel = str(p.relative_to(self.root_dir))
            h.update(rel.encode("utf-8", errors="ignore"))
            h.update(str(st.st_size).encode("utf-8"))
            h.update(str(st.st_mtime_ns).encode("utf-8"))
        return h.hexdigest()

    def _load_docs_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        ext = file_path.suffix.lower()
        if ext in SUPPORTED_STRUCTURED_EXTENSIONS:
            return self._load_csv_records(file_path)
        if ext in SUPPORTED_HTML_EXTENSIONS:
            return self._load_html_record(file_path)
        if ext in SUPPORTED_TEXT_EXTENSIONS:
            return self._load_text_record(file_path)
        return []

    def _load_csv_records(self, file_path: Path) -> List[Dict[str, Any]]:
        text = self._read_text(file_path)
        if not text:
            return []

        lines = text.splitlines()
        if len(lines) <= 1:
            return []

        reader = csv.DictReader(lines)
        docs: List[Dict[str, Any]] = []

        max_rows = int(os.getenv("TCM_PRO_MAX_CSV_ROWS", "1200"))
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
                    "row_index": idx,
                }
            )

        return docs

    def _load_html_record(self, file_path: Path) -> List[Dict[str, Any]]:
        html_text = self._read_text(file_path)
        if not html_text:
            return []

        html_text = re.sub(r"<script[\\s\\S]*?</script>", " ", html_text, flags=re.IGNORECASE)
        html_text = re.sub(r"<style[\\s\\S]*?</style>", " ", html_text, flags=re.IGNORECASE)

        title_match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match and title_match.group(1).strip() else file_path.stem

        plain = re.sub(r"<[^>]+>", " ", html_text)
        plain = html_lib.unescape(plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        if not plain:
            return []

        max_chars = int(os.getenv("TCM_PRO_MAX_HTML_CHARS", "36000"))
        plain = plain[:max_chars]

        return [
            {
                "object_id": self._make_object_id(file_path, 0),
                "title": title,
                "content": plain,
                "source_type": "professional_html",
                "source_path": str(file_path.relative_to(self.root_dir)),
                "row_index": 0,
            }
        ]

    def _load_text_record(self, file_path: Path) -> List[Dict[str, Any]]:
        text = self._read_text(file_path)
        if not text:
            return []

        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        max_chars = int(os.getenv("TCM_PRO_MAX_TEXT_CHARS", "24000"))
        text = text[:max_chars]

        return [
            {
                "object_id": self._make_object_id(file_path, 0),
                "title": file_path.stem,
                "content": text,
                "source_type": "professional_text",
                "source_path": str(file_path.relative_to(self.root_dir)),
                "row_index": 0,
            }
        ]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS professional_documents (
                object_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_file TEXT NOT NULL,
                row_index INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS professional_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prof_title ON professional_documents(title)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prof_source_type ON professional_documents(source_type)")

    def _meta_get(self, conn: sqlite3.Connection, key: str) -> str:
        row = conn.execute("SELECT value FROM professional_meta WHERE key = ?", (key,)).fetchone()
        return "" if not row else str(row[0])

    def _meta_set(self, conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            "INSERT INTO professional_meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

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

        for key in preferred_keys:
            value = row.get(key)
            if value and self._is_meaningful_text(value):
                fields.append((key, self._normalize(value)))

        for key, value in row.items():
            if len(fields) >= 18:
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

        # 对连续中文输入做轻量切片，避免“失眠口苦舌红”这类无空格问句漏检
        cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        for chunk in cjk_chunks:
            if len(chunk) <= 4:
                terms.append(chunk)
                continue
            for size in (2, 3, 4):
                for idx in range(0, len(chunk) - size + 1):
                    terms.append(chunk[idx : idx + size])

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
            score += 4.2
        if query in content:
            score += 2.7

        for term in terms:
            if term in title:
                score += 1.8
            if term in content:
                score += 0.85

        # prioritize medically dense sources
        source_type = str(record.get("source_type", ""))
        if source_type == "professional_csv":
            score += 0.2
        if "医案" in title:
            score += 0.3

        return score

    def _build_snippet(self, content: str, terms: Iterable[str], window: int = 140) -> str:
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
