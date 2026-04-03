"""pgvector 기반 벡터 저장과 검색을 담당하는 모듈"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Sequence
from typing import Any

import psycopg2

from src.shared import AppSettings, get_settings, resolve_host_and_port


class VectorRepository:
    """논문 청크 임베딩 저장과 유사도 검색을 담당하는 진입점."""

    def __init__(self, *, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()

    def list_chunks_missing_embeddings(
        self,
        *,
        limit: int = 200,
        arxiv_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """아직 임베딩이 없는 청크를 조회한다."""
        query = """
            SELECT
                c.id,
                c.arxiv_id,
                c.chunk_index,
                c.chunk_text,
                c.section_title,
                c.metadata,
                p.title
            FROM paper_chunks c
            JOIN papers p ON p.arxiv_id = c.arxiv_id
            LEFT JOIN paper_embeddings e ON e.chunk_id = c.id
            WHERE
                e.chunk_id IS NULL
                AND COALESCE(c.metadata->>'content_role', '') <> 'references'
        """
        params: list[Any] = []
        if arxiv_id:
            query += " AND c.arxiv_id = %s"
            params.append(arxiv_id)
        query += " ORDER BY c.arxiv_id ASC, c.chunk_index ASC LIMIT %s"
        params.append(max(1, limit))

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        return [
            {
                "chunk_id": row[0],
                "arxiv_id": row[1],
                "chunk_index": row[2],
                "chunk_text": row[3] or "",
                "section_title": row[4],
                "metadata": row[5] or {},
                "paper_title": row[6] or "",
            }
            for row in rows
        ]

    def upsert_paper_embeddings(self, rows: list[dict[str, Any]]) -> None:
        """논문 청크와 임베딩 벡터를 저장하거나 갱신한다."""
        if not rows:
            return

        with self._connection() as connection, connection.cursor() as cursor:
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO paper_embeddings (chunk_id, embedding, model_name, updated_at)
                    VALUES (%s, %s::vector, %s, NOW())
                    ON CONFLICT (chunk_id)
                    DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        model_name = EXCLUDED.model_name,
                        updated_at = NOW()
                    """,
                    (
                        int(row["chunk_id"]),
                        self._vector_literal(row["embedding"]),
                        row["model_name"],
                    ),
                )

    def search_paper_chunks(
        self,
        query_embedding: Sequence[float],
        *,
        limit: int = 5,
        arxiv_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """질문 임베딩과 유사한 논문 청크 목록을 반환한다."""
        query = """
            SELECT
                c.id,
                c.arxiv_id,
                p.title,
                c.chunk_text,
                c.chunk_index,
                c.section_title,
                1 - (e.embedding <=> %s::vector) AS similarity_score
            FROM paper_embeddings e
            JOIN paper_chunks c ON c.id = e.chunk_id
            JOIN papers p ON p.arxiv_id = c.arxiv_id
        """
        params: list[Any] = [self._vector_literal(query_embedding)]
        if arxiv_id:
            query += " WHERE c.arxiv_id = %s"
            params.append(arxiv_id)
        query += " ORDER BY e.embedding <=> %s::vector ASC LIMIT %s"
        params.extend([self._vector_literal(query_embedding), max(1, limit)])

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        return [
            {
                "chunk_id": row[0],
                "arxiv_id": row[1],
                "paper_title": row[2],
                "chunk_text": row[3] or "",
                "chunk_index": row[4],
                "section_title": row[5],
                "similarity_score": float(row[6]) if row[6] is not None else 0.0,
            }
            for row in rows
        ]

    @contextmanager
    def _connection(self):
        connection = psycopg2.connect(**self._build_postgres_connection_params())
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

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
    def _vector_literal(values: Sequence[float]) -> str:
        return "[" + ",".join(f"{float(value):.12f}" for value in values) + "]"
