"""프롬프트 템플릿 로딩과 사실(fact) 페이로드 구성.

기획안 5.2. Excel 원본을 통째로 넘기지 않고, Python 이 확정한 수치만
구조화해 전달한다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


@dataclass
class SurveyFacts:
    """LLM 에 전달하는 확정 사실. 여기 없는 수치는 문장에 등장할 수 없다."""

    taxon: str
    survey_round: int
    species_count: int
    protected_species_count: int
    dominant_species: list[str]
    diversity_index: float

    def to_payload(self) -> dict:
        return asdict(self)


def load_template(name: str) -> str:
    """`prompts/` 에서 템플릿 파일을 읽는다."""
    raise NotImplementedError


def render(template: str, facts: SurveyFacts) -> str:
    """템플릿에 사실 페이로드를 채워 최종 프롬프트를 만든다."""
    raise NotImplementedError
