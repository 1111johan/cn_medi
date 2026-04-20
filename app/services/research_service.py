from __future__ import annotations

from typing import Dict, List

from app.services.knowledge_service import knowledge_service
from app.services.professional_knowledge_service import professional_knowledge_service


class ResearchService:
    def qa(self, question: str, scope: str | None, source_types: List[str]) -> Dict[str, object]:
        query = question
        if scope:
            query = f"{scope} {question}"

        local_hits = knowledge_service.search(query=query, source_types=source_types, top_k=4)
        professional_hits = professional_knowledge_service.search(query=query, top_k=6)

        local_evidences = [
            {
                "object_id": hit["object_id"],
                "title": hit["title"],
                "source_type": hit["source_type"],
                "snippet": hit["snippet"],
                "score": hit["score"],
            }
            for hit in local_hits
        ]

        professional_evidences = [
            {
                "object_id": hit["object_id"],
                "title": f"{hit['title']} ({hit['source_path']})",
                "source_type": hit["source_type"],
                "snippet": hit["snippet"],
                "score": hit["score"],
            }
            for hit in professional_hits
        ]

        evidences = sorted(
            local_evidences + professional_evidences,
            key=lambda x: x["score"],
            reverse=True,
        )[:8]

        if not evidences:
            return {
                "answer": "未检索到足够证据，请扩大来源范围或补充更具体的问题描述。",
                "evidences": [],
            }

        key_points = []
        for i, hit in enumerate(evidences[:4], start=1):
            key_points.append(f"{i}. [{hit['source_type']}] {hit['title']}：{hit['snippet']}")

        answer = "基于平台知识库 + 专业中医数据库的证据回链结果：\n" + "\n".join(key_points)

        return {
            "answer": answer,
            "evidences": evidences,
        }


research_service = ResearchService()
