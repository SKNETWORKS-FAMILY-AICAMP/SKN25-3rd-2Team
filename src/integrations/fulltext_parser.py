"""PDF 본문 파싱과 청크 생성을 담당하는 모듈"""

from __future__ import annotations

import io
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import requests

from .layout_parser_client import LayoutParserClient

try:
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    PdfReader = None  # type: ignore[assignment]


@dataclass
class FulltextParseResult:
    """PDF 파싱 결과."""

    text: str
    sections: list[dict[str, Any]]
    source: str
    quality_metrics: dict[str, Any]
    artifacts: dict[str, Any] = field(default_factory=dict)
    parser_metadata: dict[str, Any] = field(default_factory=dict)


class FulltextParser:
    """PDF URL에서 텍스트를 추출하고 청크 후보를 생성한다."""

    _INLINE_BODY_STARTERS = (
        "To",
        "While",
        "We",
        "In",
        "Early",
        "This",
        "These",
        "Our",
        "For",
        "As",
        "However",
        "Specifically",
        "Unlike",
        "By",
        "After",
    )
    _KNOWN_SECTION_TITLES = {
        "abstract",
        "introduction",
        "background",
        "related work",
        "preliminaries",
        "method",
        "methods",
        "approach",
        "experiments",
        "experimental setup",
        "results",
        "discussion",
        "limitations",
        "conclusion",
        "conclusions",
        "references",
        "acknowledgements",
        "acknowledgments",
    }
    _KNOWN_UPPERCASE_TITLE_TOKENS = {
        "AI",
        "API",
        "ASR",
        "BERT",
        "BLEU",
        "BPE",
        "CNN",
        "CPU",
        "CTC",
        "GAN",
        "GPU",
        "GRU",
        "GPT",
        "LIDAR",
        "LLM",
        "LSTM",
        "MLP",
        "NLP",
        "NMT",
        "OCR",
        "PDF",
        "RAG",
        "RNN",
        "SOTA",
        "TTS",
        "VLM",
    }
    _NUMBERED_SECTION_PATTERN = re.compile(
        r"^(?P<prefix>(?:\d+(?:\.\d+)*|[A-Z](?:\.\d+)*))(?:[.)])?\s+(?P<title>[A-Z][A-Za-z0-9 ,:/()'&\-\u2013]{1,100})$"
    )
    _LAYOUT_TEXT_TYPES = {"Title", "Section header", "Text", "Table", "Caption", "Formula", "List item", "Footnote"}
    _LAYOUT_IGNORED_TYPES = {"Page header", "Page footer"}
    _LAYOUT_ARTIFACT_TYPES = {"Table", "Picture", "Caption"}

    def __init__(self, *, timeout_seconds: int = 30, layout_parser_client: LayoutParserClient | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.layout_parser_client = layout_parser_client

    def parse_from_pdf_url(self, pdf_url: str, *, fallback_text: str = "") -> FulltextParseResult:
        """PDF를 다운로드해 텍스트를 추출한다. 실패 시 fallback 텍스트를 사용한다."""
        normalized_url = (pdf_url or "").strip()
        if not normalized_url:
            return self._build_fallback_result(fallback_text)

        try:
            response = requests.get(normalized_url, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException:
            return self._build_fallback_result(fallback_text)

        layout_result = self._parse_with_layout_parser(response.content)
        if layout_result is not None:
            return layout_result

        parsed_text = self._extract_pdf_text(response.content)
        if parsed_text:
            sections = self._extract_sections(parsed_text)
            return FulltextParseResult(
                text=parsed_text,
                sections=sections or [{"title": "Full Text", "text": parsed_text}],
                source="pdf",
                quality_metrics=self._build_fulltext_quality_metrics(
                    text=parsed_text,
                    sections=sections or [{"title": "Full Text", "text": parsed_text}],
                    source="pdf",
                ),
            )

        return self._build_fallback_result(fallback_text)

    def _build_fallback_result(self, fallback_text: str) -> FulltextParseResult:
        cleaned = self._normalize_text(fallback_text)
        sections = [{"title": "Abstract", "text": cleaned}] if cleaned else []
        return FulltextParseResult(
            text=cleaned,
            sections=sections,
            source="fallback_abstract",
            quality_metrics=self._build_fulltext_quality_metrics(
                text=cleaned,
                sections=sections,
                source="fallback_abstract",
            ),
        )

    def _parse_with_layout_parser(self, content: bytes) -> FulltextParseResult | None:
        client = self.layout_parser_client or LayoutParserClient()
        if not client.is_configured():
            return None

        try:
            segments = client.analyze_pdf_bytes(content)
        except (requests.RequestException, ValueError):
            return None

        layout_text = self._build_layout_text(segments)
        if not layout_text:
            return None

        sections = self._extract_sections(layout_text)
        artifacts = self._extract_layout_artifacts(segments)
        quality_metrics = {
            **self._build_fulltext_quality_metrics(
                text=layout_text,
                sections=sections or [{"title": "Full Text", "text": layout_text}],
                source="layout_pdf",
            ),
            "layout_provider": "huridocs",
            "layout_parse_success": True,
            "artifact_count": sum(len(values) for values in artifacts.values()),
        }
        parser_metadata = {
            "provider": "huridocs",
            "segment_count": len(segments),
            "segment_type_counts": dict(Counter(str(segment.get("type") or "") for segment in segments)),
        }
        return FulltextParseResult(
            text=layout_text,
            sections=sections or [{"title": "Full Text", "text": layout_text}],
            source="layout_pdf",
            quality_metrics=quality_metrics,
            artifacts=artifacts,
            parser_metadata=parser_metadata,
        )

    @classmethod
    def _build_layout_text(cls, segments: list[dict[str, Any]]) -> str:
        ordered_segments = sorted(
            segments,
            key=lambda segment: (
                int(segment.get("page_number", 0) or 0),
                float(segment.get("top", 0.0) or 0.0),
                float(segment.get("left", 0.0) or 0.0),
            ),
        )
        parts: list[str] = []
        for segment in ordered_segments:
            segment_type = str(segment.get("type") or "")
            text = cls._normalize_text(str(segment.get("text") or ""))
            if not text or segment_type in cls._LAYOUT_IGNORED_TYPES:
                continue
            if segment_type not in cls._LAYOUT_TEXT_TYPES:
                continue
            if segment_type in {"Title", "Section header", "Caption"}:
                text = cls._normalize_layout_heading_like_text(text)

            parts.append(text)
            if segment_type in {"Title", "Section header", "Caption", "Table"}:
                parts.append("")
            elif not text.endswith((".", "?", "!", ":")):
                parts.append("")
        return cls._normalize_text("\n".join(parts))

    @classmethod
    def _extract_layout_artifacts(cls, segments: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        ordered_segments = sorted(
            segments,
            key=lambda segment: (
                int(segment.get("page_number", 0) or 0),
                float(segment.get("top", 0.0) or 0.0),
                float(segment.get("left", 0.0) or 0.0),
            ),
        )
        captions = [segment for segment in ordered_segments if str(segment.get("type") or "") == "Caption"]
        tables: list[dict[str, Any]] = []
        figures: list[dict[str, Any]] = []

        for segment in ordered_segments:
            segment_type = str(segment.get("type") or "")
            if segment_type not in cls._LAYOUT_ARTIFACT_TYPES:
                continue

            caption = cls._find_nearest_caption(segment, captions)
            if segment_type == "Table":
                tables.append(
                    {
                        "page": int(segment.get("page_number", 0) or 0),
                        "caption": caption,
                        "raw_text": str(segment.get("text") or ""),
                        "confidence": 1.0,
                    }
                )
            elif segment_type == "Picture":
                figures.append(
                    {
                        "page": int(segment.get("page_number", 0) or 0),
                        "caption": caption,
                        "confidence": 1.0 if caption else 0.5,
                    }
                )

        return {"tables": tables, "figures": figures}

    @staticmethod
    def _find_nearest_caption(segment: dict[str, Any], captions: list[dict[str, Any]]) -> str | None:
        page_number = int(segment.get("page_number", 0) or 0)
        top = float(segment.get("top", 0.0) or 0.0)
        same_page_captions = [
            caption for caption in captions if int(caption.get("page_number", 0) or 0) == page_number
        ]
        if not same_page_captions:
            return None

        nearest = min(
            same_page_captions,
            key=lambda caption: abs(float(caption.get("top", 0.0) or 0.0) - top),
        )
        text = str(nearest.get("text") or "").strip()
        if not text:
            return None
        return FulltextParser._normalize_layout_heading_like_text(text)

    @staticmethod
    def build_chunks(
        text: str,
        *,
        sections: list[dict[str, Any]] | None = None,
        max_chars: int = 1800,
        overlap_chars: int = 200,
    ) -> list[dict[str, Any]]:
        """문장/문단 경계를 우선 고려해 청크를 생성한다."""
        normalized = FulltextParser._normalize_text(text)
        if not normalized:
            return []

        max_chars = max(300, max_chars)
        overlap_chars = max(0, min(overlap_chars, max_chars // 2))

        chunk_index = 0
        chunks: list[dict[str, Any]] = []
        normalized_sections = sections or [{"title": "Full Text", "text": normalized}]

        for section_index, section in enumerate(normalized_sections):
            section_title = str(section.get("title") or "Full Text").strip() or "Full Text"
            section_text = FulltextParser._normalize_text(str(section.get("text") or ""))
            if not section_text:
                continue

            start = 0
            section_chunk_index = 0
            while start < len(section_text):
                end = FulltextParser._adjust_chunk_end(section_text, start, max_chars)
                candidate = section_text[start:end]

                clean_chunk = FulltextParser._strip_inline_heading_prefix(candidate.strip())
                clean_chunk = FulltextParser._normalize_chunk_opening(clean_chunk)
                if clean_chunk:
                    metadata = {
                        "section_index": section_index,
                        "section_chunk_index": section_chunk_index,
                        "section_char_length": len(section_text),
                        "char_start": start,
                        "char_end": end,
                        "char_length": len(clean_chunk),
                        "starts_mid_sentence": FulltextParser._starts_mid_sentence(section_text, start),
                        "ends_mid_sentence": FulltextParser._ends_mid_sentence(section_text, end),
                        "content_role": FulltextParser._infer_chunk_content_role(section_title, clean_chunk),
                    }
                    new_chunk = {
                        "chunk_index": chunk_index,
                        "chunk_text": clean_chunk,
                        "section_title": section_title,
                        "token_count": FulltextParser._rough_token_count(clean_chunk),
                        "metadata": metadata,
                    }
                    if FulltextParser._should_absorb_into_previous(chunks, new_chunk):
                        FulltextParser._merge_chunk_into_previous(chunks[-1], new_chunk)
                    else:
                        chunks.append(new_chunk)
                        chunk_index += 1
                        section_chunk_index += 1

                if end >= len(section_text):
                    break
                start = FulltextParser._adjust_next_chunk_start(section_text, end, overlap_chars)
        FulltextParser._annotate_chunk_links(chunks)
        return chunks

    @staticmethod
    def _extract_pdf_text(content: bytes) -> str:
        if PdfReader is None:
            return ""

        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception:
            return ""

        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            cleaned_page = FulltextParser._normalize_extracted_page_text(page_text)
            if cleaned_page:
                pages.append(cleaned_page)
        return FulltextParser._normalize_text("\n\n".join(pages))

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.replace("\x00", " ")
        normalized = re.sub(r"(?<=\w)-\n(?=\w)", "", normalized)
        normalized = re.sub(r"\n\d+•[A-Z][^\n]{0,100}\n", "\n", normalized)
        normalized = re.sub(r"\n[A-Z][^\n]{0,100}•\d+\n", "\n", normalized)
        normalized = re.sub(r"\n[A-Z][A-Za-z0-9][A-Za-z0-9 :,\-–'.]{3,80}\s+\d{1,3}\n", "\n", normalized)
        normalized = re.sub(r"(?<=[a-z])(?=[A-Z][A-Za-z-]{2,})", " ", normalized)
        normalized = re.sub(r"\bar Xiv\b", "arXiv", normalized)
        normalized = re.sub(r"\bLi DAR\b", "LiDAR", normalized)
        normalized = re.sub(r"\bGit Hub\b", "GitHub", normalized)
        normalized = re.sub(r"\bHugging Face\b", "HuggingFace", normalized)
        normalized = re.sub(r"\bModel Scope\b", "ModelScope", normalized)
        normalized = re.sub(r"\bDeep Seek\b", "DeepSeek", normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    @staticmethod
    def _normalize_layout_heading_like_text(text: str) -> str:
        normalized = " ".join(text.split())
        prefix = ""
        tokens = normalized.split()
        if (
            len(tokens) >= 3
            and re.fullmatch(r"[A-Z](?:\.\d+)*", tokens[0])
            and re.fullmatch(r"[A-Z]", tokens[1])
            and re.fullmatch(r"[A-Z]{2,}", tokens[2])
        ):
            prefix = tokens[0]
            normalized = " ".join(tokens[1:])
        previous = None
        while previous != normalized:
            previous = normalized
            normalized = re.sub(
                r"\b([A-Z])\s+([A-Z]{2,})\b",
                lambda match: f"{match.group(1)}{match.group(2)}",
                normalized,
            )
            normalized = re.sub(
                r"\b([A-Z])\s+([A-Z][a-z][A-Za-z-]*)\b",
                lambda match: f"{match.group(1)}{match.group(2)[0].lower()}{match.group(2)[1:]}",
                normalized,
            )
        normalized = re.sub(r"\s+([:;,.!?])", r"\1", normalized)
        if prefix:
            normalized = f"{prefix} {normalized}"
        return normalized.strip()

    @staticmethod
    def _rough_token_count(text: str) -> int:
        # 모델별 tokenizer 의존성을 피하기 위해 단순 근사치(영어 기준 1 token ~= 4 chars)를 사용
        return max(1, len(text) // 4)

    @staticmethod
    def summarize_chunks(chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if not chunks:
            return {
                "chunk_count": 0,
                "body_chunk_count": 0,
                "avg_chunk_chars": 0,
                "max_chunk_chars": 0,
                "avg_chunk_tokens": 0,
                "max_chunk_tokens": 0,
                "suspicious_start_count": 0,
                "body_suspicious_start_count": 0,
                "mid_sentence_start_count": 0,
                "mid_sentence_end_count": 0,
                "front_matter_chunk_count": 0,
                "non_body_chunk_count": 0,
                "reference_chunk_count": 0,
                "table_like_chunk_count": 0,
                "tiny_chunk_count": 0,
            }

        char_lengths = [len(str(chunk.get("chunk_text") or "")) for chunk in chunks]
        token_counts = [int(chunk.get("token_count", 0) or 0) for chunk in chunks]
        suspicious_start_count = 0
        body_suspicious_start_count = 0
        for chunk in chunks:
            text = str(chunk.get("chunk_text") or "")
            if text and re.match(r"^[a-z0-9,.;:)\]%-]", text):
                suspicious_start_count += 1
                if (chunk.get("metadata") or {}).get("content_role") == "body":
                    body_suspicious_start_count += 1
        return {
            "chunk_count": len(chunks),
            "body_chunk_count": sum(1 for chunk in chunks if (chunk.get("metadata") or {}).get("content_role") == "body"),
            "avg_chunk_chars": round(sum(char_lengths) / len(char_lengths), 2),
            "max_chunk_chars": max(char_lengths),
            "avg_chunk_tokens": round(sum(token_counts) / len(token_counts), 2),
            "max_chunk_tokens": max(token_counts),
            "suspicious_start_count": suspicious_start_count,
            "body_suspicious_start_count": body_suspicious_start_count,
            "mid_sentence_start_count": sum(
                1 for chunk in chunks if bool((chunk.get("metadata") or {}).get("starts_mid_sentence"))
            ),
            "mid_sentence_end_count": sum(
                1 for chunk in chunks if bool((chunk.get("metadata") or {}).get("ends_mid_sentence"))
            ),
            "front_matter_chunk_count": sum(1 for chunk in chunks if chunk.get("section_title") == "Front Matter"),
            "non_body_chunk_count": sum(
                1 for chunk in chunks if (chunk.get("metadata") or {}).get("content_role") != "body"
            ),
            "reference_chunk_count": sum(
                1 for chunk in chunks if (chunk.get("metadata") or {}).get("content_role") == "references"
            ),
            "table_like_chunk_count": sum(
                1 for chunk in chunks if (chunk.get("metadata") or {}).get("content_role") == "table_like"
            ),
            "tiny_chunk_count": sum(1 for chunk in chunks if len(str(chunk.get("chunk_text") or "")) < 160),
        }

    @classmethod
    def _extract_sections(cls, text: str) -> list[dict[str, Any]]:
        lines = [line.strip() for line in text.splitlines()]
        sections: list[dict[str, Any]] = []
        current_title = "Front Matter"
        current_lines: list[str] = []

        for line in lines:
            if not line:
                if current_lines and current_lines[-1] != "":
                    current_lines.append("")
                continue

            heading = cls._normalize_section_heading(line)
            if heading is not None:
                if current_lines:
                    section_text = cls._normalize_text("\n".join(current_lines))
                    section_text = cls._normalize_section_text(current_title, section_text)
                    if section_text and not cls._should_drop_section(current_title, section_text):
                        sections.append({"title": current_title, "text": section_text})
                current_title = heading
                current_lines = []
                continue

            current_lines.append(line)

        if current_lines:
            section_text = cls._normalize_text("\n".join(current_lines))
            section_text = cls._normalize_section_text(current_title, section_text)
            if section_text and not cls._should_drop_section(current_title, section_text):
                sections.append({"title": current_title, "text": section_text})

        if len(sections) == 1 and sections[0]["title"] == "Front Matter":
            sections[0]["title"] = "Full Text"
        return cls._reorder_sections(sections)

    @classmethod
    def _reorder_sections(cls, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(sections) < 3:
            return sections

        indexed_sections = list(enumerate(sections))
        numeric_sections = [
            (index, sort_key)
            for index, section in indexed_sections
            if (sort_key := cls._parse_numeric_section_sort_key(str(section.get("title") or ""))) is not None
        ]
        if len(numeric_sections) < 2:
            return sections

        numeric_order = [sort_key for _, sort_key in numeric_sections]
        if numeric_order == sorted(numeric_order):
            return sections

        def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, tuple[int, ...], int]:
            index, section = item
            title = str(section.get("title") or "")
            lowered = title.lower()
            if lowered == "front matter":
                return (0, (), index)
            if lowered == "abstract":
                return (1, (), index)
            numeric_key = cls._parse_numeric_section_sort_key(title)
            if numeric_key is not None:
                return (2, numeric_key, index)
            return (3, (), index)

        return [section for _, section in sorted(indexed_sections, key=sort_key)]

    @staticmethod
    def _parse_numeric_section_sort_key(title: str) -> tuple[int, ...] | None:
        match = re.match(r"^(?P<prefix>\d+(?:\.\d+)*)\b", title.strip())
        if match is None:
            return None
        return tuple(int(part) for part in match.group("prefix").split("."))

    @classmethod
    def _normalize_section_text(cls, title: str, text: str) -> str:
        compact = cls._normalize_text(text)
        if not compact:
            return compact

        if cls._infer_content_role(title) == "body":
            lead_fragment_match = re.match(
                r"^(?P<lead>[a-z][^.]{0,160}\.)\s+(?P<rest>(?:In this section|Here, we|We |This section|To )\b.+)$",
                compact,
            )
            if lead_fragment_match:
                return lead_fragment_match.group("rest").strip()
        return compact

    @classmethod
    def _normalize_section_heading(cls, line: str) -> str | None:
        candidate = cls._normalize_layout_heading_like_text(" ".join(line.split()))
        candidate = re.sub(r"\s*[–—]\s*", " - ", candidate)
        lowered = candidate.lower()

        if lowered in {"figure", "table", "listing"}:
            return None
        if lowered.startswith(("figure ", "table ", "listing ", "arxiv:")):
            return None
        if re.fullmatch(r"\d+", candidate):
            return None

        if lowered in cls._KNOWN_SECTION_TITLES:
            return cls._prettify_section_title(candidate)

        appendix_match = re.fullmatch(r"(appendix(?:\s+[A-Z])?)\s+([A-Z][A-Za-z0-9 ,:/()'&-]{1,100})", candidate, re.IGNORECASE)
        if appendix_match:
            prefix = appendix_match.group(1)
            title = appendix_match.group(2)
            if title.lower() in {"table of contents", "contents"}:
                return cls._prettify_section_title(prefix)
            return cls._prettify_section_title(f"{prefix} {title}")

        match = cls._NUMBERED_SECTION_PATTERN.fullmatch(candidate)
        if match is None:
            return None

        prefix = match.group("prefix")
        title = match.group("title")
        prefix_root = prefix.split(".")[0]
        if prefix_root.isdigit():
            major_prefix = int(prefix_root)
            if major_prefix >= 20:
                return None
            if prefix.isdigit() and int(prefix) >= 50:
                return None
        if re.search(r"(?:\. ?){2,}\d{1,3}$", candidate):
            return None
        if re.search(r"\s\d{1,3}$", title):
            return None
        if title.lower().startswith(("figure ", "table ", "listing ")):
            return None
        title_words = title.split()
        if len(title_words) > 9:
            return None
        if any(len(word) > 24 for word in title_words):
            return None
        if "," in title and len(title_words) > 6:
            return None
        if title.startswith(("We ", "Our ", "This ", "These ")):
            return None
        if not cls._looks_like_numbered_heading(title):
            return None
        return cls._prettify_section_title(f"{prefix} {title}")

    @staticmethod
    def _adjust_next_chunk_start(text: str, end: int, overlap_chars: int) -> int:
        start = max(0, end - overlap_chars)
        if start <= 0:
            return 0

        rewind_start = max(0, end - overlap_chars - 160)
        rewind_window = text[rewind_start:end]
        sentence_breaks = list(re.finditer(r"(?:\.\s+|\?\s+|!\s+|\n{2,})", rewind_window))
        if sentence_breaks:
            start = rewind_start + sentence_breaks[-1].end()
        else:
            sentence_window = text[start : min(len(text), start + 160)]
            sentence_break = re.search(r"(?:\.\s+|\?\s+|!\s+|\n{2,})", sentence_window)
            if sentence_break is not None:
                start += sentence_break.end()

        # If overlap lands in the middle of a token, snap to the next readable boundary.
        boundary_window_end = min(len(text), start + 80)
        while start < boundary_window_end and text[start - 1].isalnum() and text[start].isalnum():
            start += 1

        # Skip leading whitespace/newlines so chunks start cleanly.
        while start < len(text) and text[start].isspace():
            start += 1

        fragment_window = text[start : min(len(text), start + 260)]
        if FulltextParser._looks_like_fragmentary_chunk_start(fragment_window):
            sentence_break = re.search(r"(?:\.\s+|\?\s+|!\s+|\n{2,})", fragment_window)
            if sentence_break is not None:
                start += sentence_break.end()
                while start < len(text) and text[start].isspace():
                    start += 1
        elif re.match(r"^[a-z][a-z-]{2,}\b", fragment_window):
            # 중간 문장에서 잘린 소문자 시작 조각은 다음 문장 시작으로 넘긴다.
            sentence_break = re.search(r"(?:\.\s+|\?\s+|!\s+|\n{2,})", fragment_window[:220])
            if sentence_break is not None:
                start += sentence_break.end()
                while start < len(text) and text[start].isspace():
                    start += 1
        return start

    @staticmethod
    def _looks_like_numbered_heading(title: str) -> bool:
        words = re.findall(r"[A-Za-z0-9-]+", title)
        if not words:
            return False

        uppercase_like = 0
        for word in words:
            if word[0].isupper() or word[0].isdigit() or word.isupper():
                uppercase_like += 1

        ratio = uppercase_like / len(words)
        if len(words) <= 4:
            return ratio >= 0.5
        return ratio >= 0.6

    @staticmethod
    def _prettify_section_title(title: str) -> str:
        compact = " ".join(title.split())
        if compact.isupper():
            return re.sub(
                r"[A-Z]+",
                lambda match: (
                    match.group(0)
                    if match.group(0) in FulltextParser._KNOWN_UPPERCASE_TITLE_TOKENS or len(match.group(0)) == 1
                    else match.group(0).capitalize()
                ),
                compact,
            )
        return compact

    @staticmethod
    def _build_fulltext_quality_metrics(
        *,
        text: str,
        sections: list[dict[str, Any]],
        source: str,
    ) -> dict[str, Any]:
        section_lengths = [len(str(section.get("text") or "")) for section in sections]
        return {
            "parse_source": source,
            "fallback_used": source == "fallback_abstract",
            "text_length": len(text),
            "section_count": len(sections),
            "avg_section_chars": round(sum(section_lengths) / len(section_lengths), 2) if section_lengths else 0,
            "max_section_chars": max(section_lengths) if section_lengths else 0,
        }

    @staticmethod
    def _normalize_extracted_page_text(text: str) -> str:
        lines = [line.strip() for line in text.replace("\x00", " ").splitlines()]
        filtered_lines: list[str] = []
        for line in lines:
            if not line:
                filtered_lines.append("")
                continue
            if re.fullmatch(r"\d+", line):
                continue
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", line):
                continue
            if re.match(r"^arXiv:\d{4}\.\d{4,5}v?\d*", line):
                continue
            if re.match(r"^\*?Equal contribution", line, re.IGNORECASE):
                continue
            if re.match(r"^(?:/uni\d{8})+$", line):
                continue
            if len(re.findall(r"/uni\d{8}", line)) >= 3:
                continue
            if FulltextParser._looks_like_running_header_footer(line):
                continue
            if FulltextParser._looks_like_toc_line(line):
                continue
            filtered_lines.extend(FulltextParser._split_inline_heading_line(line))

        stitched_lines: list[str] = []
        for line in filtered_lines:
            if not line:
                if stitched_lines and stitched_lines[-1] != "":
                    stitched_lines.append("")
                continue

            if stitched_lines:
                previous = stitched_lines[-1]
                if previous and FulltextParser._should_merge_lines(previous, line):
                    stitched_lines[-1] = FulltextParser._merge_lines(previous, line)
                    continue
            stitched_lines.append(line)

        return "\n".join(stitched_lines).strip()

    @staticmethod
    def _should_merge_lines(previous: str, current: str) -> bool:
        if not previous or not current:
            return False
        if previous.endswith("-"):
            return True
        if previous.endswith((".", "?", "!", ":", ";")):
            return False
        if FulltextParser._normalize_section_heading(current) is not None:
            return False
        if current[0].islower() or current[0] in "([\"'":
            return True
        if previous[-1] in ",/":
            return True
        return len(previous) > 40 and current[:1].isupper() and len(current.split()) > 3

    @staticmethod
    def _merge_lines(previous: str, current: str) -> str:
        if previous.endswith("-"):
            return previous[:-1] + current.lstrip()
        return previous.rstrip() + " " + current.lstrip()

    @staticmethod
    def _adjust_chunk_end(text: str, start: int, max_chars: int) -> int:
        tentative_end = min(len(text), start + max_chars)
        if tentative_end >= len(text):
            return len(text)

        window_end = min(len(text), tentative_end + 220)
        candidate_window = text[start:window_end]
        minimum_break = max(max_chars // 2, 220)
        preferred_breaks = [
            match.end()
            for match in re.finditer(r"(?:\n{2,}|\.\s+|\?\s+|!\s+)", candidate_window)
            if match.end() >= minimum_break
        ]
        if preferred_breaks:
            return start + preferred_breaks[-1]

        line_breaks = [
            match.end()
            for match in re.finditer(r"\n+", candidate_window)
            if match.end() >= minimum_break
        ]
        if line_breaks:
            return start + line_breaks[-1]

        last_space = candidate_window.rfind(" ")
        if last_space >= minimum_break:
            return start + last_space + 1
        return tentative_end

    @staticmethod
    def _should_absorb_into_previous(chunks: list[dict[str, Any]], new_chunk: dict[str, Any]) -> bool:
        if not chunks:
            return False

        previous = chunks[-1]
        if previous.get("section_title") != new_chunk.get("section_title"):
            return False

        new_text = str(new_chunk.get("chunk_text") or "")
        if len(new_text) >= 160:
            if not (len(new_text) <= 360 and re.match(r"^[a-z0-9]", new_text)):
                return False

        metadata = new_chunk.get("metadata") or {}
        if metadata.get("starts_mid_sentence"):
            return True
        return (
            bool(re.fullmatch(r"[\d\s.,;:()[\]{}%-]{1,360}", new_text))
            or len(new_text.split()) <= 12
            or bool(re.match(r"^[a-z0-9]", new_text))
        )

    @staticmethod
    def _merge_chunk_into_previous(previous: dict[str, Any], new_chunk: dict[str, Any]) -> None:
        previous_text = str(previous.get("chunk_text") or "").rstrip()
        new_text = str(new_chunk.get("chunk_text") or "").lstrip()
        separator = "\n" if previous_text and not previous_text.endswith("\n") else ""
        merged_text = f"{previous_text}{separator}{new_text}".strip()
        previous["chunk_text"] = merged_text
        previous["token_count"] = FulltextParser._rough_token_count(merged_text)

        previous_metadata = previous.setdefault("metadata", {})
        new_metadata = new_chunk.get("metadata") or {}
        previous_metadata["char_end"] = new_metadata.get("char_end", previous_metadata.get("char_end"))
        previous_metadata["char_length"] = len(merged_text)
        previous_metadata["ends_mid_sentence"] = bool(new_metadata.get("ends_mid_sentence"))
        previous_metadata["continues_next"] = bool(new_metadata.get("ends_mid_sentence"))

    @staticmethod
    def _infer_content_role(section_title: str) -> str:
        lowered = section_title.lower()
        if lowered == "front matter":
            return "front_matter"
        if "reference" in lowered or lowered.startswith("bibliography"):
            return "references"
        if "appendix" in lowered:
            return "appendix"
        if "table of contents" in lowered:
            return "toc"
        return "body"

    @classmethod
    def _infer_chunk_content_role(cls, section_title: str, chunk_text: str) -> str:
        section_role = cls._infer_content_role(section_title)
        if section_role != "body":
            return section_role

        compact = " ".join(chunk_text.split())
        if cls._looks_like_toc_line(compact):
            return "toc"
        if cls._looks_like_figure_caption_chunk(compact):
            return "figure_caption"
        if re.match(
            r"^(?:Figure|Table)\s+\d+\s+(?:presents|shows|compares|illustrates|visualizes|reports|summarizes|demonstrates|plots)\b",
            compact,
            re.IGNORECASE,
        ):
            return "body"
        if cls._looks_like_reference_chunk(compact):
            return "references"
        if cls._looks_like_table_like_chunk(chunk_text, compact):
            return "table_like"
        return "body"

    @staticmethod
    def _looks_like_reference_chunk(compact: str) -> bool:
        compact_prefix = compact[:260]
        if not compact_prefix:
            return False

        if re.match(r"^(?:\[\d+\]|\d+\.)\s+[A-Z]", compact_prefix):
            return True
        if re.match(r"^\d+\s+\[\d+\]\s+[A-Z]", compact_prefix):
            return True
        if re.match(r"^(?:\d+\s*,?\s*)?\[\d+\]\s+[A-Z]", compact_prefix):
            return True
        if compact_prefix.startswith("In ") and re.search(
            r"\b(?:Conference|Proceedings|arXiv|Association for Computational Linguistics)\b",
            compact_prefix,
        ):
            return True
        if re.match(r"^\d", compact_prefix) and re.search(r"\[\d+\]", compact_prefix) and re.search(
            r"\b(?:19|20)\d{2}\b",
            compact_prefix,
        ):
            return True
        if compact_prefix.startswith(("doi:", "https://", "http://")) and re.search(r"\[\d+\]", compact_prefix):
            return True
        if re.match(r"^[A-Z][A-Za-z'`.-]+(?:,\s+[A-Z][A-Za-z'`.-]+){1,}", compact_prefix) and re.search(
            r"\b(?:19|20)\d{2}\b", compact_prefix
        ):
            return True
        return len(re.findall(r"(?:^|\s)\d+\s+\[\d+\]", compact[:220])) >= 1

    @staticmethod
    def _looks_like_figure_caption_chunk(compact: str) -> bool:
        if not compact:
            return False

        explicit_caption = re.match(r"^(?:Figure|Table)\s+\d+[:.]", compact)
        panel_caption = re.match(r"^\d+\.\s*[A-Z][^.]{0,140}\([a-z]\)", compact)
        multi_panel_caption = compact.startswith(("a, ", "b, ", "c, ", "d, ")) and re.search(
            r"\b[bcd],\s+[A-Z]",
            compact[:220],
        )
        if not (explicit_caption or panel_caption or multi_panel_caption):
            return False

        # "Table 1 presents/shows/compares..." 같은 본문 서술은 캡션으로 보지 않는다.
        if re.match(
            r"^(?:Figure|Table)\s+\d+\s+(?:presents|shows|compares|illustrates|visualizes|reports|summarizes|demonstrates|plots)\b",
            compact,
            re.IGNORECASE,
        ):
            return False
        return True

    @staticmethod
    def _looks_like_table_like_chunk(raw_text: str, compact: str) -> bool:
        if "/uni" in raw_text:
            return True
        if any(token in raw_text.lower() for token in ("<td", "</td", "<tr", "</tr", "<th", "</th")):
            return True

        digits = sum(character.isdigit() for character in compact)
        numeric_cells = len(re.findall(r"\b\d+(?:\.\d+)?\b", compact))
        line_break_count = raw_text.count("\n")
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        first_line = lines[0] if lines else compact[:160]
        numeric_heavy_lines = sum(
            1
            for line in lines
            if len(re.findall(r"\b\d+(?:\.\d+)?\b", line)) >= 2
            or bool(re.fullmatch(r"[\d\s.,:;()%+\-=/]+", line))
        )
        repeated_matrix_tokens = len(re.findall(r"\b[a-z]+-\d+-(?:combined|pre|post)\b", compact, re.IGNORECASE))
        first_line_numeric_cells = len(re.findall(r"\b\d+(?:\.\d+)?\b", first_line))
        explicit_tabular_opening = bool(
            re.match(r"^[\d.,;:()%-]", compact)
            or re.match(r"^(?:Table|Figure)\s+\d+[:.]", compact)
            or re.match(r"^\d+\.\s*[A-Z][^.]{0,140}\([a-z]\)", compact)
            or repeated_matrix_tokens >= 6
        )
        strong_numeric_block = (
            (compact and digits / len(compact) > 0.28 and line_break_count >= 5)
            or (re.match(r"^[\d.,;:()%-]", compact) and numeric_cells >= 10 and line_break_count >= 2)
            or (
                re.match(r"^(?:Table|Figure)\s+\d+\b", compact)
                and numeric_heavy_lines >= 3
                and line_break_count >= 2
            )
            or repeated_matrix_tokens >= 6
            or (len(lines) >= 8 and numeric_heavy_lines >= max(6, int(len(lines) * 0.7)) and digits / max(1, len(compact)) > 0.08)
        )

        if FulltextParser._starts_like_body_paragraph(first_line, compact) and not explicit_tabular_opening:
            return False

        if compact and digits / len(compact) > 0.28 and line_break_count >= 5:
            return True
        if re.match(r"^[\d.,;:()%-]", compact) and numeric_cells >= 10 and line_break_count >= 2:
            return True
        if (
            re.search(r"\b(?:Table|Figure)\s+\d+\b", compact[:160])
            and numeric_heavy_lines >= 3
            and line_break_count >= 2
        ):
            return True
        if repeated_matrix_tokens >= 6:
            return True
        if len(lines) >= 8 and numeric_heavy_lines >= max(6, int(len(lines) * 0.7)) and digits / max(1, len(compact)) > 0.08:
            return True
        return False

    @staticmethod
    def _starts_like_body_paragraph(first_line: str, compact: str) -> bool:
        normalized_first_line = " ".join(first_line.split())
        if not normalized_first_line:
            return False

        if re.match(
            r"^(?:As shown|Beyond|In this|In our|We |To address|To evaluate|To further|Notably|While|Since|Early|Figure \d+ (?:shows|illustrates|visualizes)|Table \d+ (?:presents|shows|compares|reports|summarizes))\b",
            normalized_first_line,
            re.IGNORECASE,
        ):
            return True

        word_count = len(re.findall(r"[A-Za-z]+", normalized_first_line))
        numeric_cells = len(re.findall(r"\b\d+(?:\.\d+)?\b", normalized_first_line))
        if word_count >= 12 and numeric_cells <= 3 and re.match(r"^[A-Z][a-z]", normalized_first_line):
            return True

        compact_prefix = compact[:220]
        if compact_prefix.count(". ") >= 1 and word_count >= 10 and numeric_cells <= 4:
            return True
        return False

    @staticmethod
    def _split_inline_heading_line(line: str) -> list[str]:
        line = line.strip()
        if not line:
            return [""]
        split = FulltextParser._find_inline_heading_split(line)
        if split is not None:
            head, rest = split
            return [head, rest]
        return [line]

    @staticmethod
    def _strip_inline_heading_prefix(text: str) -> str:
        split = FulltextParser._find_inline_heading_split(text)
        if split is not None:
            _, rest = split
            return rest
        return text

    @staticmethod
    def _find_inline_heading_split(text: str) -> tuple[str, str] | None:
        compact = " ".join(text.split())
        title_prefix = FulltextParser._find_short_title_prefix(compact)
        if title_prefix is not None:
            return title_prefix
        if not re.match(r"^\d+(?:\.\d+)+(?:[.)])?\s+", compact):
            return None

        for starter in FulltextParser._INLINE_BODY_STARTERS:
            marker = f" {starter} "
            index = compact.find(marker)
            if index == -1:
                continue
            head = compact[:index].strip()
            rest = compact[index + 1 :].strip()
            if len(head.split()) > 16 or len(head) < 8:
                continue
            if not rest:
                continue
            return head, rest
        return None

    @staticmethod
    def _find_short_title_prefix(text: str) -> tuple[str, str] | None:
        match = re.match(r"^(?P<head>[A-Z0-9][A-Za-z0-9/+&' -]{2,48}\.)\s*(?P<rest>[A-Z].+)$", text)
        if match is None:
            return None

        head = match.group("head").strip()
        rest = match.group("rest").strip()
        head_words = head[:-1].split()
        if not (1 <= len(head_words) <= 6):
            return None
        if head.startswith(("This ", "These ", "We ", "Our ", "In ", "To ", "As ", "However ")):
            return None
        if any(len(word) > 20 for word in head_words):
            return None
        return head, rest

    @staticmethod
    def _normalize_chunk_opening(text: str) -> str:
        compact = text.lstrip()
        if not compact:
            return compact

        bullet_index = compact.find("• ")
        if bullet_index != -1 and bullet_index <= 220:
            prefix = compact[:bullet_index]
            if re.fullmatch(r"[\s,.;:()\[\]0-9A-Za-z&'\-–/]+", prefix or " "):
                compact = compact[bullet_index + 2 :].lstrip()

        compact = re.sub(r"^[,;:)\]\}]+\s*", "", compact)
        return compact

    @staticmethod
    def _looks_like_fragmentary_chunk_start(text: str) -> bool:
        compact = text.lstrip()
        return bool(
            re.match(r"^\d{4}[a-z]?\](?:,)?\s+[a-z]", compact)
            or re.match(r"^\(\d+\)\s+[a-z]", compact)
            or re.match(r"^\d+[a-z]?\),\s+[a-z]", compact)
            or re.match(r"^\d+[a-z]\),", compact)
            or re.match(r"^\d+[a-z]?,\s+[a-z]", compact)
            or re.match(r"^\d+[A-Z][a-z]", compact)
        )

    @staticmethod
    def _looks_like_running_header_footer(line: str) -> bool:
        compact = " ".join(line.split())
        if re.search(r"•\d{1,3}$", compact):
            return True
        if re.fullmatch(r"\d+•[A-Z][A-Za-z .'-]+", compact):
            return True
        if re.fullmatch(r"[A-Z][A-Za-z0-9:,\-–' ]{8,100}\d{1,3}$", compact):
            words = compact[:-3].split()
            if 2 <= len(words) <= 16:
                return True
        return False

    @classmethod
    def _should_drop_section(cls, title: str, text: str) -> bool:
        compact = " ".join(text.split())
        if not compact:
            return True
        if cls._infer_content_role(title) == "toc":
            return True

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines and len(lines) <= 12 and all(cls._looks_like_toc_line(line) for line in lines):
            return True
        return False

    @staticmethod
    def _starts_mid_sentence(text: str, start: int) -> bool:
        if start <= 0:
            return False

        while start < len(text) and text[start].isspace():
            start += 1
        if start >= len(text):
            return False

        previous_index = start - 1
        while previous_index >= 0 and text[previous_index].isspace():
            previous_index -= 1
        if previous_index < 0:
            return False

        previous_char = text[previous_index]
        current_char = text[start]
        if previous_char in ".?!:\n":
            return False
        if current_char in ",.;:)]}%-":
            return True
        if previous_char.isalnum() and current_char.isalnum():
            return True
        return current_char.islower() or current_char.isdigit()

    @staticmethod
    def _ends_mid_sentence(text: str, end: int) -> bool:
        if end >= len(text):
            return False

        current_index = max(0, end - 1)
        while current_index >= 0 and text[current_index].isspace():
            current_index -= 1
        if current_index < 0:
            return False

        next_index = end
        while next_index < len(text) and text[next_index].isspace():
            next_index += 1
        if next_index >= len(text):
            return False

        current_char = text[current_index]
        next_char = text[next_index]
        if current_char in ".?!:\n":
            return False
        if next_char in ",.;:)]}%-":
            return True
        if current_char.isalnum() and next_char.isalnum():
            return True
        return next_char.islower() or next_char.isdigit()

    @staticmethod
    def _annotate_chunk_links(chunks: list[dict[str, Any]]) -> None:
        for index, chunk in enumerate(chunks):
            metadata = chunk.setdefault("metadata", {})
            metadata["prev_chunk_index"] = chunks[index - 1]["chunk_index"] if index > 0 else None
            metadata["next_chunk_index"] = chunks[index + 1]["chunk_index"] if index + 1 < len(chunks) else None
            metadata["continues_previous"] = bool(metadata.get("starts_mid_sentence"))
            metadata["continues_next"] = bool(metadata.get("ends_mid_sentence"))

    @staticmethod
    def _looks_like_toc_line(line: str) -> bool:
        compact = " ".join(line.split())
        if compact.lower() in {"contents", "table of contents"}:
            return True
        if re.search(r"(?:\. ?){6,}\d+$", compact):
            return True
        if re.fullmatch(r"(?:\d+(?:\.\d+)*\.?)\s+.+(?:\. ?){3,}\d{1,3}", compact):
            return True
        if re.fullmatch(r"(?:\d+(?:\.\d+)*|[A-Z])\s+[A-Z][A-Za-z0-9 ,:/()'&-]{1,80}\s+\d{1,3}", compact):
            return True
        return bool(re.fullmatch(r"(?:\d+(?:\.\d+)*)\s+.+\s+\d{1,3}", compact) and compact.count(".") >= 4)
