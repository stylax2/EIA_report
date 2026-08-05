"""조사자료 검증 계층.

LLM 에 넘기기 전에 원자료의 결함을 여기서 모두 걸러낸다. 검증을 통과하지
못한 자료는 계산으로 넘기지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationIssue:
    """검증 과정에서 발견한 개별 문제."""

    severity: str  # "error" | "warning"
    row: int | None
    column: str | None
    message: str


@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def validate_schema(df: pd.DataFrame) -> ValidationResult:
    """필수 컬럼 존재 여부와 자료형을 확인한다."""
    raise NotImplementedError


def validate_species_names(df: pd.DataFrame, master: pd.DataFrame) -> ValidationResult:
    """국명·학명을 표준종목록 마스터 DB 와 대조한다."""
    raise NotImplementedError


def validate_duplicates(df: pd.DataFrame) -> ValidationResult:
    """동일 지점·차수·종의 중복 입력을 찾는다."""
    raise NotImplementedError
