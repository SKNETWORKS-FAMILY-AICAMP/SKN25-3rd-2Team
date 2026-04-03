"""HURIDOCS PDF 레이아웃 파서 연동 클라이언트."""

from __future__ import annotations

from typing import Any

import requests

from src.shared import AppSettings, get_settings


class LayoutParserClient:
    """HURIDOCS 레이아웃 분석 서비스와 통신하는 클라이언트."""

    REQUIRED_SEGMENT_FIELDS = {
        "left",
        "top",
        "width",
        "height",
        "page_number",
        "page_width",
        "page_height",
        "text",
        "type",
    }

    def __init__(
        self,
        *,
        settings: AppSettings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session = session or requests.Session()

    def is_configured(self) -> bool:
        return bool((self.settings.layout_parser_base_url or "").strip())

    def analyze_pdf_bytes(
        self,
        content: bytes,
        *,
        filename: str = "document.pdf",
        fast: bool | None = None,
        parse_tables_and_math: bool | None = None,
    ) -> list[dict[str, Any]]:
        """PDF를 HURIDOCS에 보내고 검증된 레이아웃 segment 목록을 반환한다."""
        if not content:
            raise ValueError("PDF content is empty.")

        base_url = (self.settings.layout_parser_base_url or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("LAYOUT_PARSER_BASE_URL is not configured.")

        fast = self.settings.layout_parser_fast if fast is None else bool(fast)
        parse_tables_and_math = (
            self.settings.layout_parser_parse_tables_and_math
            if parse_tables_and_math is None
            else bool(parse_tables_and_math)
        )

        response = self.session.post(
            f"{base_url}/",
            files={"file": (filename, content, "application/pdf")},
            data={
                "fast": str(fast).lower(),
                "parse_tables_and_math": str(parse_tables_and_math).lower(),
            },
            timeout=self.settings.layout_parser_timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Layout parser response must be a list of segments.")

        return [self._normalize_segment(segment) for segment in payload]

    @classmethod
    def _normalize_segment(cls, segment: Any) -> dict[str, Any]:
        if not isinstance(segment, dict):
            raise ValueError("Layout parser segment must be a JSON object.")

        missing = cls.REQUIRED_SEGMENT_FIELDS.difference(segment)
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"Layout parser segment is missing required fields: {missing_list}")

        return {
            "left": float(segment["left"]),
            "top": float(segment["top"]),
            "width": float(segment["width"]),
            "height": float(segment["height"]),
            "page_number": int(segment["page_number"]),
            "page_width": float(segment["page_width"]),
            "page_height": float(segment["page_height"]),
            "text": str(segment.get("text") or ""),
            "type": str(segment.get("type") or ""),
        }
