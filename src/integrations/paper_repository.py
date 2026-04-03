"""정제된 논문 데이터를 저장하고 조회하는 계층 구현 모듈."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any
import re

import psycopg2
from psycopg2.extras import Json

from src.shared import AppSettings, get_settings, resolve_host_and_port


class PaperRepository:
    """정제 논문과 논문 청크를 PostgreSQL에 저장하고 조회하는 진입점."""

    def __init__(self, *, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self._ensure_schema()

    def save_paper(self, paper: dict[str, Any]) -> str:
        """정제 논문 1건을 저장하고 arxiv_id를 반환한다."""
        arxiv_id = str(paper["arxiv_id"]).strip()
        if not arxiv_id:
            raise ValueError("paper['arxiv_id']는 비어 있을 수 없습니다.")

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO papers (
                    arxiv_id, title, authors, abstract, primary_category,
                    categories, pdf_url, published_at, updated_at,
                    upvotes, github_url, github_stars, citation_count, source, updated_at_utc
                ) VALUES (
                    %(arxiv_id)s, %(title)s, %(authors)s, %(abstract)s, %(primary_category)s,
                    %(categories)s, %(pdf_url)s, %(published_at)s, %(arxiv_updated_at)s,
                    %(upvotes)s, %(github_url)s, %(github_stars)s, %(citation_count)s, %(source)s, NOW()
                )
                ON CONFLICT (arxiv_id)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    authors = EXCLUDED.authors,
                    abstract = EXCLUDED.abstract,
                    primary_category = EXCLUDED.primary_category,
                    categories = EXCLUDED.categories,
                    pdf_url = EXCLUDED.pdf_url,
                    published_at = EXCLUDED.published_at,
                    updated_at = EXCLUDED.updated_at,
                    upvotes = EXCLUDED.upvotes,
                    github_url = EXCLUDED.github_url,
                    github_stars = EXCLUDED.github_stars,
                    citation_count = EXCLUDED.citation_count,
                    source = EXCLUDED.source,
                    updated_at_utc = NOW()
                """,
                {
                    "arxiv_id": arxiv_id,
                    "title": paper.get("title", ""),
                    "authors": Json(paper.get("authors", [])),
                    "abstract": paper.get("abstract", ""),
                    "primary_category": paper.get("primary_category"),
                    "categories": Json(paper.get("categories", [])),
                    "pdf_url": paper.get("pdf_url"),
                    "published_at": self._to_datetime(paper.get("published_at")),
                    "arxiv_updated_at": self._to_datetime(paper.get("updated_at")),
                    "upvotes": int(paper.get("upvotes") or 0),
                    "github_url": paper.get("github_url"),
                    "github_stars": self._to_int_or_none(paper.get("github_stars")),
                    "citation_count": self._to_int_or_none(paper.get("citation_count")),
                    "source": paper.get("source", "hf_daily_papers"),
                },
            )
        return arxiv_id

    def save_paper_fulltext(
        self,
        arxiv_id: str,
        *,
        text: str,
        sections: list[dict[str, Any]] | None = None,
        source: str = "pdf",
        quality_metrics: dict[str, Any] | None = None,
        artifacts: dict[str, Any] | None = None,
        parser_metadata: dict[str, Any] | None = None,
    ) -> None:
        """논문 본문 텍스트를 저장한다."""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO paper_fulltexts (
                    arxiv_id, text, sections, source, quality_metrics, artifacts, parser_metadata, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (arxiv_id)
                DO UPDATE SET
                    text = EXCLUDED.text,
                    sections = EXCLUDED.sections,
                    source = EXCLUDED.source,
                    quality_metrics = EXCLUDED.quality_metrics,
                    artifacts = EXCLUDED.artifacts,
                    parser_metadata = EXCLUDED.parser_metadata,
                    updated_at = NOW()
                """,
                (
                    arxiv_id,
                    text,
                    Json(sections or []),
                    source,
                    Json(quality_metrics or {}),
                    Json(artifacts or {}),
                    Json(parser_metadata or {}),
                ),
            )

    def save_paper_chunks(self, arxiv_id: str, chunks: list[dict[str, Any]]) -> None:
        """논문 청크 목록을 저장한다."""
        if not chunks:
            return

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM paper_chunks WHERE arxiv_id = %s", (arxiv_id,))
            for chunk in chunks:
                cursor.execute(
                    """
                    INSERT INTO paper_chunks (arxiv_id, chunk_index, chunk_text, section_title, token_count, metadata, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        arxiv_id,
                        int(chunk.get("chunk_index", 0)),
                        chunk.get("chunk_text", ""),
                        chunk.get("section_title"),
                        int(chunk.get("token_count", 0)),
                        Json(chunk.get("metadata", {})),
                    ),
                )

    def list_recent_papers(self, *, limit: int = 200) -> list[dict[str, Any]]:
        """최근 저장 논문을 조회한다."""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT arxiv_id, title, authors, abstract, primary_category, categories, pdf_url,
                       published_at, updated_at, upvotes, github_url, github_stars, citation_count
                FROM papers
                ORDER BY COALESCE(published_at, updated_at_utc) DESC
                LIMIT %s
                """,
                (max(1, limit),),
            )
            rows = cursor.fetchall()

        papers: list[dict[str, Any]] = []
        for row in rows:
            papers.append(
                {
                    "arxiv_id": row[0],
                    "title": row[1],
                    "authors": row[2] or [],
                    "abstract": row[3] or "",
                    "primary_category": row[4],
                    "categories": row[5] or [],
                    "pdf_url": row[6],
                    "published_at": row[7].isoformat() if row[7] else None,
                    "updated_at": row[8].isoformat() if row[8] else None,
                    "upvotes": row[9] or 0,
                    "github_url": row[10],
                    "github_stars": row[11],
                    "citation_count": row[12],
                }
            )
        return papers

    def list_papers_missing_arxiv_metadata(self, *, limit: int = 200) -> list[dict[str, Any]]:
        """arXiv 보강이 아직 충분히 적용되지 않은 논문 목록을 조회한다."""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT arxiv_id, title, authors, abstract, primary_category, categories, pdf_url,
                       published_at, updated_at, upvotes, github_url, github_stars, citation_count, source
                FROM papers
                WHERE
                    primary_category IS NULL
                    OR categories = '[]'::jsonb
                    OR source = 'hf_daily_papers_raw'
                ORDER BY COALESCE(published_at, updated_at_utc) DESC
                LIMIT %s
                """,
                (max(1, limit),),
            )
            rows = cursor.fetchall()

        return [
            {
                "arxiv_id": row[0],
                "title": row[1],
                "authors": row[2] or [],
                "abstract": row[3] or "",
                "primary_category": row[4],
                "categories": row[5] or [],
                "pdf_url": row[6],
                "published_at": row[7].isoformat() if row[7] else None,
                "updated_at": row[8].isoformat() if row[8] else None,
                "upvotes": row[9] or 0,
                "github_url": row[10],
                "github_stars": row[11],
                "citation_count": row[12],
                "source": row[13] or "hf_daily_papers",
            }
            for row in rows
        ]

    def get_paper(self, arxiv_id: str) -> dict[str, Any] | None:
        """단일 논문 메타데이터를 조회한다."""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT arxiv_id, title, authors, abstract, primary_category, categories, pdf_url,
                       published_at, updated_at, upvotes, github_url, github_stars, citation_count
                FROM papers
                WHERE arxiv_id = %s
                """,
                (arxiv_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return {
            "arxiv_id": row[0],
            "title": row[1],
            "authors": row[2] or [],
            "abstract": row[3] or "",
            "primary_category": row[4],
            "categories": row[5] or [],
            "pdf_url": row[6],
            "published_at": row[7].isoformat() if row[7] else None,
            "updated_at": row[8].isoformat() if row[8] else None,
            "upvotes": row[9] or 0,
            "github_url": row[10],
            "github_stars": row[11],
            "citation_count": row[12],
        }

    def get_paper_fulltext(self, arxiv_id: str) -> dict[str, Any] | None:
        """단일 논문의 fulltext와 섹션 정보를 조회한다."""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT arxiv_id, text, sections, source, quality_metrics, artifacts, parser_metadata, updated_at
                FROM paper_fulltexts
                WHERE arxiv_id = %s
                """,
                (arxiv_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return {
            "arxiv_id": row[0],
            "text": row[1] or "",
            "sections": row[2] or [],
            "source": row[3],
            "quality_metrics": row[4] or {},
            "artifacts": row[5] or {},
            "parser_metadata": row[6] or {},
            "updated_at": row[7].isoformat() if row[7] else None,
        }

    def list_paper_chunks(self, arxiv_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        """단일 논문의 청크 목록을 chunk_index 순으로 조회한다."""
        query = """
            SELECT id, arxiv_id, chunk_index, chunk_text, section_title, token_count, metadata, updated_at
            FROM paper_chunks
            WHERE arxiv_id = %s
            ORDER BY chunk_index ASC
        """
        params: tuple[Any, ...] = (arxiv_id,)
        if limit is not None:
            query += " LIMIT %s"
            params = (arxiv_id, max(1, limit))

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                "chunk_id": row[0],
                "arxiv_id": row[1],
                "chunk_index": row[2],
                "chunk_text": row[3] or "",
                "section_title": row[4],
                "token_count": row[5] or 0,
                "metadata": row[6] or {},
                "updated_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]

    def list_chunk_window(self, arxiv_id: str, center_chunk_index: int, *, window: int = 1) -> list[dict[str, Any]]:
        """중심 청크를 기준으로 앞뒤 문맥 청크를 함께 조회한다."""
        normalized_window = max(0, int(window))
        start_index = max(0, int(center_chunk_index) - normalized_window)
        end_index = int(center_chunk_index) + normalized_window

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, arxiv_id, chunk_index, chunk_text, section_title, token_count, metadata, updated_at
                FROM paper_chunks
                WHERE arxiv_id = %s
                  AND chunk_index BETWEEN %s AND %s
                ORDER BY chunk_index ASC
                """,
                (arxiv_id, start_index, end_index),
            )
            rows = cursor.fetchall()

        return [
            {
                "chunk_id": row[0],
                "arxiv_id": row[1],
                "chunk_index": row[2],
                "chunk_text": row[3] or "",
                "section_title": row[4],
                "token_count": row[5] or 0,
                "metadata": row[6] or {},
                "updated_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]

    def list_papers_for_topic(self, topic_id: int) -> list[dict[str, Any]]:
        """토픽 문서 생성에 사용할 논문 묶음을 반환한다."""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.arxiv_id, p.title, p.authors, p.abstract, p.pdf_url, p.published_at,
                       p.upvotes, p.github_url, p.github_stars, p.citation_count
                FROM topic_papers tp
                JOIN papers p ON p.arxiv_id = tp.arxiv_id
                WHERE tp.topic_id = %s
                ORDER BY p.published_at DESC NULLS LAST, p.updated_at_utc DESC
                """,
                (topic_id,),
            )
            rows = cursor.fetchall()

        return [
            {
                "arxiv_id": row[0],
                "title": row[1],
                "authors": row[2] or [],
                "abstract": row[3] or "",
                "pdf_url": row[4] or "",
                "published_at": row[5].isoformat() if row[5] else None,
                "upvotes": row[6] or 0,
                "github_url": row[7],
                "github_stars": row[8],
                "citation_count": row[9],
            }
            for row in rows
        ]

    def list_chunk_candidates_by_query(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        """최소 retrieval 용도로 FTS/ILIKE 기반 청크 후보를 조회한다."""
        normalized_query = " ".join(query.split())
        if not normalized_query:
            return []

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                WITH ranked AS (
                    SELECT
                        c.id AS chunk_id,
                        c.arxiv_id,
                        p.title AS paper_title,
                        p.abstract AS paper_abstract,
                        c.chunk_text,
                        c.chunk_index,
                        c.section_title,
                        ts_rank_cd(
                            setweight(to_tsvector('english', coalesce(p.title, '')), 'A') ||
                            setweight(to_tsvector('english', coalesce(p.abstract, '')), 'B') ||
                            setweight(to_tsvector('english', coalesce(c.chunk_text, '')), 'C'),
                            websearch_to_tsquery('english', %s)
                        ) AS fts_score,
                        CASE
                            WHEN p.title ILIKE ('%%' || %s || '%%') THEN 0.45
                            WHEN p.abstract ILIKE ('%%' || %s || '%%') THEN 0.2
                            WHEN c.chunk_text ILIKE ('%%' || %s || '%%') THEN 0.15
                            ELSE 0
                        END AS ilike_bonus
                        ,
                        CASE
                            WHEN c.section_title ILIKE '%%Table of Contents%%' THEN -0.12
                            WHEN c.section_title ILIKE '%%References%%' THEN -0.08
                            WHEN c.section_title = 'Front Matter' THEN -0.03
                            ELSE 0
                        END AS structural_adjustment
                    FROM paper_chunks c
                    JOIN papers p ON p.arxiv_id = c.arxiv_id
                    WHERE
                        (
                            setweight(to_tsvector('english', coalesce(p.title, '')), 'A') ||
                            setweight(to_tsvector('english', coalesce(p.abstract, '')), 'B') ||
                            setweight(to_tsvector('english', coalesce(c.chunk_text, '')), 'C')
                        ) @@ websearch_to_tsquery('english', %s)
                        OR p.title ILIKE ('%%' || %s || '%%')
                        OR p.abstract ILIKE ('%%' || %s || '%%')
                        OR c.chunk_text ILIKE ('%%' || %s || '%%')
                )
                SELECT
                    chunk_id,
                    arxiv_id,
                    paper_title,
                    paper_abstract,
                    chunk_text,
                    chunk_index,
                    section_title,
                    (fts_score + ilike_bonus + structural_adjustment) AS score
                FROM ranked
                WHERE (fts_score + ilike_bonus + structural_adjustment) > 0.02
                ORDER BY score DESC, chunk_id DESC
                LIMIT %s
                """,
                (
                    normalized_query,
                    normalized_query,
                    normalized_query,
                    normalized_query,
                    normalized_query,
                    normalized_query,
                    normalized_query,
                    normalized_query,
                    max(1, limit),
                ),
            )
            rows = cursor.fetchall()

        return [
            {
                "chunk_id": row[0],
                "arxiv_id": row[1],
                "paper_title": row[2],
                "chunk_text": row[4],
                "chunk_index": row[5],
                "section_title": row[6],
                "similarity_score": float(row[7]) if row[7] is not None else 0.0,
                "snippet": self._build_search_snippet(
                    normalized_query,
                    chunk_text=row[4] or "",
                    abstract=row[3] or "",
                    title=row[2] or "",
                ),
            }
            for row in rows
        ]

    @contextmanager
    def _connection(self):
        params = self._build_postgres_connection_params()
        connection = psycopg2.connect(**params)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _ensure_schema(self) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    arxiv_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authors JSONB NOT NULL DEFAULT '[]'::jsonb,
                    abstract TEXT NOT NULL DEFAULT '',
                    primary_category TEXT,
                    categories JSONB NOT NULL DEFAULT '[]'::jsonb,
                    pdf_url TEXT,
                    published_at TIMESTAMPTZ NULL,
                    updated_at TIMESTAMPTZ NULL,
                    upvotes INTEGER NOT NULL DEFAULT 0,
                    github_url TEXT,
                    github_stars INTEGER NULL,
                    citation_count INTEGER NULL,
                    source TEXT NOT NULL DEFAULT 'hf_daily_papers',
                    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_fulltexts (
                    arxiv_id TEXT PRIMARY KEY REFERENCES papers(arxiv_id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    sections JSONB NOT NULL DEFAULT '[]'::jsonb,
                    source TEXT NOT NULL DEFAULT 'pdf',
                    quality_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
                    artifacts JSONB NOT NULL DEFAULT '{}'::jsonb,
                    parser_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cursor.execute(
                """
                ALTER TABLE paper_fulltexts
                ADD COLUMN IF NOT EXISTS quality_metrics JSONB NOT NULL DEFAULT '{}'::jsonb;
                """
            )
            cursor.execute(
                """
                ALTER TABLE paper_fulltexts
                ADD COLUMN IF NOT EXISTS artifacts JSONB NOT NULL DEFAULT '{}'::jsonb;
                """
            )
            cursor.execute(
                """
                ALTER TABLE paper_fulltexts
                ADD COLUMN IF NOT EXISTS parser_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    arxiv_id TEXT NOT NULL REFERENCES papers(arxiv_id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    section_title TEXT NULL,
                    token_count INTEGER NOT NULL DEFAULT 0,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(arxiv_id, chunk_index)
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_embeddings (
                    chunk_id BIGINT PRIMARY KEY REFERENCES paper_chunks(id) ON DELETE CASCADE,
                    embedding VECTOR(1536) NOT NULL,
                    model_name TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS topics (
                    topic_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS topic_papers (
                    topic_id INTEGER NOT NULL,
                    arxiv_id TEXT NOT NULL REFERENCES papers(arxiv_id) ON DELETE CASCADE,
                    PRIMARY KEY (topic_id, arxiv_id)
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS topic_documents (
                    topic_id INTEGER PRIMARY KEY,
                    document JSONB NOT NULL,
                    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_paper_chunks_fts
                    ON paper_chunks USING GIN (to_tsvector('english', chunk_text));
                """
            )

    def _build_postgres_connection_params(self) -> dict[str, Any]:
        host = self.settings.postgres_host
        db_name = self.settings.app_postgres_db or self.settings.postgres_db
        user = self.settings.postgres_user
        password = self.settings.postgres_password

        if not host:
            raise ValueError("POSTGRES_HOST가 설정되지 않았습니다.")
        if not db_name:
            raise ValueError("APP_POSTGRES_DB 또는 POSTGRES_DB가 설정되지 않았습니다.")
        if not user or not password:
            raise ValueError("POSTGRES_USER 또는 POSTGRES_PASSWORD가 설정되지 않았습니다.")

        resolved_host, resolved_port = resolve_host_and_port(host, self.settings.server_postgres_port)
        return {
            "dbname": db_name,
            "user": user,
            "password": password,
            "host": resolved_host,
            "port": resolved_port,
        }

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            return datetime.fromisoformat(normalized)
        return None

    @staticmethod
    def _to_int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _build_search_snippet(query: str, *, chunk_text: str, abstract: str, title: str, max_chars: int = 280) -> str:
        terms = [term for term in re.split(r"\W+", query.lower()) if len(term) >= 3]
        candidates = [chunk_text, abstract, title]

        for candidate in candidates:
            if not candidate:
                continue
            lowered = candidate.lower()
            for term in terms:
                index = lowered.find(term)
                if index != -1:
                    start = max(0, index - max_chars // 3)
                    end = min(len(candidate), start + max_chars)
                    snippet = candidate[start:end].strip()
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(candidate):
                        snippet = snippet + "..."
                    return snippet

        fallback = next((candidate for candidate in candidates if candidate), "")
        compact = " ".join(fallback.split())
        return compact[:max_chars] + ("..." if len(compact) > max_chars else "")
