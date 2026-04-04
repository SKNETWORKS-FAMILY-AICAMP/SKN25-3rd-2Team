"""prepare job queue의 저장과 소비를 담당하는 모듈"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import select
from typing import Any

import psycopg2
from psycopg2.extras import Json

from src.shared import AppSettings, get_settings, resolve_host_and_port


class PrepareJobRepository:
    """prepare job queue를 PostgreSQL에 저장하고 소비하는 진입점"""

    channel_name = "arxplore_prepare_jobs"

    def __init__(self, *, settings: AppSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self._ensure_schema()

    def enqueue_prepare_job(
        self,
        *,
        target_date: str,
        mode: str = "auto",
        source: str = "collect",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """날짜 단위 prepare 작업을 큐에 추가한다"""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO prepare_jobs (mode, target_date, source, payload, status, attempt_count, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'pending', 0, NOW(), NOW())
                ON CONFLICT (mode, target_date)
                DO UPDATE SET
                    source = EXCLUDED.source,
                    payload = EXCLUDED.payload,
                    status = CASE
                        WHEN prepare_jobs.status = 'processing' THEN prepare_jobs.status
                        WHEN prepare_jobs.status = 'done' THEN prepare_jobs.status
                        ELSE 'pending'
                    END,
                    worker_id = CASE
                        WHEN prepare_jobs.status = 'processing' THEN prepare_jobs.worker_id
                        ELSE NULL
                    END,
                    error = CASE
                        WHEN prepare_jobs.status = 'processing' THEN prepare_jobs.error
                        ELSE NULL
                    END,
                    claimed_at = CASE
                        WHEN prepare_jobs.status = 'processing' THEN prepare_jobs.claimed_at
                        ELSE NULL
                    END,
                    finished_at = CASE
                        WHEN prepare_jobs.status = 'processing' THEN prepare_jobs.finished_at
                        ELSE NULL
                    END,
                    updated_at = NOW()
                RETURNING id, status, created_at = updated_at AS inserted
                """,
                (mode, target_date, source, Json(payload or {})),
            )
            row = cursor.fetchone()
            cursor.execute("SELECT pg_notify(%s, %s)", (self.channel_name, f"{mode}:{target_date}"))

        return {
            "enqueued": bool(row[2]) if row is not None else False,
            "job_id": int(row[0]) if row is not None else None,
            "mode": mode,
            "date": target_date,
            "status": row[1] if row is not None else None,
        }

    def claim_prepare_job(
        self,
        *,
        mode: str = "auto",
        worker_id: str = "local_prepare_worker",
    ) -> dict[str, Any] | None:
        """대기 중인 prepare 작업 1건을 선점한다"""
        self.reset_stale_prepare_jobs(mode=mode)
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                WITH next_job AS (
                    SELECT id
                    FROM prepare_jobs
                    WHERE mode = %s
                      AND status = 'pending'
                    ORDER BY target_date ASC, id ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE prepare_jobs j
                SET
                    status = 'processing',
                    worker_id = %s,
                    claimed_at = NOW(),
                    updated_at = NOW(),
                    attempt_count = j.attempt_count + 1
                FROM next_job
                WHERE j.id = next_job.id
                RETURNING
                    j.id,
                    j.mode,
                    j.target_date,
                    j.source,
                    j.payload,
                    j.status,
                    j.attempt_count,
                    j.worker_id,
                    j.created_at,
                    j.claimed_at,
                    j.updated_at
                """,
                (mode, worker_id),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return {
            "job_id": row[0],
            "mode": row[1],
            "date": row[2],
            "source": row[3],
            "payload": row[4] or {},
            "status": row[5],
            "attempt_count": int(row[6] or 0),
            "worker_id": row[7],
            "created_at": row[8],
            "claimed_at": row[9],
            "updated_at": row[10],
        }

    def reset_stale_prepare_jobs(
        self,
        *,
        mode: str = "auto",
        stale_seconds: int | None = None,
    ) -> int:
        """오래 멈춘 processing 작업을 다시 pending으로 되돌린다"""
        normalized_stale_seconds = int(
            stale_seconds if stale_seconds is not None else self.settings.prepare_job_stale_seconds
        )
        if normalized_stale_seconds <= 0:
            return 0

        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE prepare_jobs
                SET
                    status = 'pending',
                    worker_id = NULL,
                    error = NULL,
                    claimed_at = NULL,
                    finished_at = NULL,
                    updated_at = NOW()
                WHERE mode = %s
                  AND status = 'processing'
                  AND claimed_at IS NOT NULL
                  AND claimed_at < NOW() - (%s * INTERVAL '1 second')
                RETURNING target_date
                """,
                (mode, normalized_stale_seconds),
            )
            reset_dates = [str(row[0]) for row in cursor.fetchall()]
            for target_date in reset_dates:
                cursor.execute("SELECT pg_notify(%s, %s)", (self.channel_name, f"{mode}:{target_date}"))

        return len(reset_dates)

    def complete_prepare_job(
        self,
        *,
        mode: str,
        target_date: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        """prepare 작업을 완료 상태로 갱신한다"""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE prepare_jobs
                SET
                    status = 'done',
                    result = %s,
                    error = NULL,
                    finished_at = NOW(),
                    updated_at = NOW()
                WHERE mode = %s AND target_date = %s
                """,
                (Json(result or {}), mode, target_date),
            )

    def fail_prepare_job(
        self,
        *,
        mode: str,
        target_date: str,
        error: str,
    ) -> None:
        """prepare 작업을 실패 상태로 갱신한다"""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE prepare_jobs
                SET
                    status = 'failed',
                    error = %s,
                    finished_at = NOW(),
                    updated_at = NOW()
                WHERE mode = %s AND target_date = %s
                """,
                (error, mode, target_date),
            )

    def wait_for_prepare_job(
        self,
        *,
        timeout_seconds: float = 120.0,
    ) -> bool:
        """새 prepare 작업 알림이 올 때까지 기다린다"""
        connection = psycopg2.connect(**self._build_postgres_connection_params())
        connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"LISTEN {self.channel_name};")
            ready, _, _ = select.select([connection], [], [], max(0.0, float(timeout_seconds)))
            if not ready:
                return False
            connection.poll()
            while connection.notifies:
                connection.notifies.pop(0)
            return True
        finally:
            connection.close()

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

    def _ensure_schema(self) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS prepare_jobs (
                    id BIGSERIAL PRIMARY KEY,
                    mode TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'collect',
                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    result JSONB NOT NULL DEFAULT '{}'::jsonb,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    worker_id TEXT,
                    error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    claimed_at TIMESTAMPTZ,
                    finished_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_prepare_jobs_mode_target_date UNIQUE (mode, target_date)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_prepare_jobs_mode_status_target_date
                ON prepare_jobs (mode, status, target_date)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_prepare_jobs_status_updated_at
                ON prepare_jobs (status, updated_at DESC)
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
