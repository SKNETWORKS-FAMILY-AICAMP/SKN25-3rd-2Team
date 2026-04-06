"""핵심 프롬프트 템플릿을 모아 노출하는 모듈"""

from .detailed_summary import DETAILED_SUMMARY_PROMPT
from .key_findings import KEY_FINDINGS_PROMPT
from .overview import OVERVIEW_PROMPT
from .paper_key_findings import PAPER_KEY_FINDINGS_PROMPT
from .paper_overview import PAPER_OVERVIEW_PROMPT
from .translation import TRANSLATION_PROMPT

__all__ = [
    "DETAILED_SUMMARY_PROMPT",
    "KEY_FINDINGS_PROMPT",
    "OVERVIEW_PROMPT",
    "PAPER_KEY_FINDINGS_PROMPT",
    "PAPER_OVERVIEW_PROMPT",
    "TRANSLATION_PROMPT",
]
