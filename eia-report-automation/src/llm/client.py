"""Local LLM 클라이언트.

Ollama 등 로컬 런타임을 감싼다. 모델명은 `config/model.yaml` 에서 읽으므로
개발 PC 가 달라져도 코드는 그대로 쓴다(기획안 5.1, 11.3).

이 계층은 외부 API 를 호출하지 않는다. 평가서 데이터는 로컬을 벗어나지
않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMConfig:
    provider: str  # 예: "ollama"
    model: str
    host: str
    temperature: float
    max_tokens: int


def load_config(path: str | None = None) -> LLMConfig:
    """`config/model.yaml` 에서 LLM 설정을 읽는다."""
    raise NotImplementedError


class LocalLLMClient:
    """로컬 런타임에 프롬프트를 보내고 생성 문장을 받는다."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def generate(self, prompt: str) -> str:
        """프롬프트를 보내 문장을 생성한다."""
        raise NotImplementedError

    def generate_from_facts(self, template_name: str, facts: dict[str, Any]) -> str:
        """확정된 사실(JSON)을 프롬프트 템플릿에 채워 문장을 생성한다."""
        raise NotImplementedError
