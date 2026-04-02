"""논문 원본 응답 저장 계층 구현."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

from src.shared import AppSettings, get_settings, resolve_host_and_port

try:
    from pymongo import MongoClient
except ModuleNotFoundError:  # pragma: no cover - depends on runtime environment
    MongoClient = None  # type: ignore[assignment]


class RawPaperStore:
    """HF Daily Papers 원본 응답을 MongoDB에 저장하는 진입점."""

    def __init__(
        self,
        *,
        settings: AppSettings | None = None,
        client: Any = None,
    ) -> None:
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
            return
        if MongoClient is None:
            raise ModuleNotFoundError("pymongo가 설치되어 있지 않아 RawPaperStore를 초기화할 수 없습니다.")
        self.client = MongoClient(self._build_mongo_uri())
        self._ensure_collection_indexes()

    def save_daily_papers_response(
        self,
        *,
        date: str,
        payload: list[dict[str, Any]] | dict[str, Any],
    ) -> str:
        """원본 응답과 수집 날짜를 저장하고 저장 식별자를 반환한다."""
        collection = self._collection()
        document = {
            "source": "hf_daily_papers",
            "date": date,
            "payload": payload,
            "fetched_count": len(payload) if isinstance(payload, list) else 1,
            "collected_at": datetime.now(timezone.utc),
        }
        collection.replace_one(
            {"source": "hf_daily_papers", "date": date},
            document,
            upsert=True,
        )
        stored = collection.find_one({"source": "hf_daily_papers", "date": date}, {"_id": 1})
        if stored is None:
            raise RuntimeError("MongoDB에 저장한 raw 문서를 다시 조회하지 못했습니다.")
        return str(stored["_id"])

    def load_daily_papers_response(self, *, date: str) -> list[dict[str, Any]]:
        """수집 날짜 기준 최신 원본 payload를 조회한다."""
        collection = self._collection()
        document = collection.find_one({"source": "hf_daily_papers", "date": date}, sort=[("collected_at", -1)])
        if document is None:
            return []
        payload = document.get("payload")
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return [payload]
        return []

    def _collection(self) -> Any:
        return self.client[self.settings.mongo_db][self.settings.mongo_daily_papers_collection]

    def _ensure_collection_indexes(self) -> None:
        collection = self._collection()

        duplicate_groups = list(
            collection.aggregate(
                [
                    {"$match": {"source": "hf_daily_papers"}},
                    {"$sort": {"source": 1, "date": 1, "collected_at": -1, "_id": -1}},
                    {
                        "$group": {
                            "_id": {"source": "$source", "date": "$date"},
                            "ids": {"$push": "$_id"},
                            "count": {"$sum": 1},
                        }
                    },
                    {"$match": {"count": {"$gt": 1}}},
                ]
            )
        )
        for group in duplicate_groups:
            duplicate_ids = group.get("ids", [])[1:]
            if duplicate_ids:
                collection.delete_many({"_id": {"$in": duplicate_ids}})

        collection.create_index(
            [("source", 1), ("date", 1)],
            unique=True,
            name="uq_source_date",
        )
        collection.create_index(
            [("source", 1), ("collected_at", -1)],
            name="idx_source_collected_at",
        )

    def _build_mongo_uri(self) -> str:
        if not self.settings.mongo_host:
            raise ValueError("MONGO_HOST가 설정되지 않았습니다.")
        if not self.settings.mongo_initdb_root_username or not self.settings.mongo_initdb_root_password:
            raise ValueError("MongoDB 인증 정보가 설정되지 않았습니다.")

        host, port = resolve_host_and_port(self.settings.mongo_host, self.settings.server_mongo_port)
        return (
            "mongodb://"
            f"{quote_plus(self.settings.mongo_initdb_root_username)}:{quote_plus(self.settings.mongo_initdb_root_password)}"
            f"@{host}:{port}/?authSource=admin"
        )
