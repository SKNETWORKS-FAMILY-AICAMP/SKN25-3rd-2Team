"""MongoDB raw는 유지한 채 PostgreSQL 정제·파생 테이블만 초기화한다."""

from __future__ import annotations

import argparse
from contextlib import closing
from typing import Any

import psycopg2

from src.shared import get_settings, resolve_host_and_port


TARGET_TABLES = (
    "paper_embeddings",
    "paper_chunks",
    "paper_fulltexts",
    "topic_papers",
    "topic_documents",
    "topics",
    "papers",
)


def _build_connection_params() -> dict[str, Any]:
    settings = get_settings()
    host = settings.postgres_host
    db_name = settings.app_postgres_db or settings.postgres_db
    user = settings.postgres_user
    password = settings.postgres_password

    if not host:
        raise ValueError("POSTGRES_HOST가 설정되지 않았습니다.")
    if not db_name:
        raise ValueError("APP_POSTGRES_DB 또는 POSTGRES_DB가 설정되지 않았습니다.")
    if not user or not password:
        raise ValueError("POSTGRES_USER 또는 POSTGRES_PASSWORD가 설정되지 않았습니다.")

    resolved_host, resolved_port = resolve_host_and_port(host, settings.server_postgres_port)
    return {
        "host": resolved_host,
        "port": resolved_port,
        "dbname": db_name,
        "user": user,
        "password": password,
    }


def _fetch_counts(connection: psycopg2.extensions.connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        for table in TARGET_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = int(cursor.fetchone()[0] or 0)
    return counts


def _print_counts(label: str, counts: dict[str, int]) -> None:
    print(label)
    for table in TARGET_TABLES:
        print(f"  - {table}: {counts.get(table, 0)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset refined PostgreSQL tables derived from MongoDB raw paper payloads."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually truncate the tables. Without this flag the script only prints counts.",
    )
    args = parser.parse_args()

    connection_params = _build_connection_params()
    with closing(psycopg2.connect(**connection_params)) as connection:
        connection.autocommit = False
        before_counts = _fetch_counts(connection)
        _print_counts("[before]", before_counts)

        if not args.execute:
            print()
            print("No changes applied. Re-run with --execute to truncate the refined layer.")
            return 0

        with connection.cursor() as cursor:
            cursor.execute(
                """
                TRUNCATE TABLE
                    paper_embeddings,
                    paper_chunks,
                    paper_fulltexts,
                    topic_papers,
                    topic_documents,
                    topics,
                    papers
                RESTART IDENTITY
                """
            )
        connection.commit()

        after_counts = _fetch_counts(connection)
        print()
        _print_counts("[after]", after_counts)
        print()
        print("PostgreSQL refined layer reset complete. MongoDB raw data was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
