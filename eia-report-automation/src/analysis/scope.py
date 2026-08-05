"""분석 단위(Scope).

분석가는 "이 분류군의 이 회차·정점에서 무엇이 나오는가"를 보고 평가서에
넣을 표·그래프를 고른다. 그 선택 단위를 정의한다.

임의 조합을 모두 계산하면 정점 5개일 때 4,095가지가 되어 감당할 수 없다.
업무상 의미 있는 단위만 열거한다. 정점 분류군 17개, 나머지 7개다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.schema import (
    FIELD_ROUNDS,
    LITERATURE_COLUMNS,
    TaxonSpec,
    station_columns,
    station_label,
    survey_columns,
)

# 단위 종류. 화면에서 묶어 보여줄 때 쓴다.
KIND_LITERATURE = "문헌"
KIND_STATION = "정점"
KIND_ROUND = "회차"
KIND_AGGREGATE = "종합"


@dataclass(frozen=True)
class Scope:
    """분석 단위 하나. 어떤 출현 컬럼을 볼 것인가를 정한다."""

    key: str  # URL·데이터 키로 쓰는 영문 식별자
    label: str  # 화면 표기
    kind: str
    columns: tuple[str, ...]
    round_name: str | None = None  # 소속 회차. 정점·회차 단위에만 있다
    station: int | None = None  # 정점 번호

    @property
    def is_single_column(self) -> bool:
        return len(self.columns) == 1

    @property
    def has_literature(self) -> bool:
        return any(c in LITERATURE_COLUMNS for c in self.columns)

    @property
    def has_field(self) -> bool:
        return any(c not in LITERATURE_COLUMNS for c in self.columns)

    @property
    def field_rounds(self) -> list[str]:
        """포함된 현지조사 회차."""
        return [r for r in FIELD_ROUNDS
                if any(c == r or c.startswith(f"{r}_") for c in self.columns)]


def _round_key(round_name: str) -> str:
    """'현지조사1' → 'field1'"""
    return f"field{round_name.removeprefix('현지조사')}"


def scopes_for(spec: TaxonSpec) -> list[Scope]:
    """분류군 하나의 분석 단위 목록.

    순서가 화면의 표시 순서가 된다. 좁은 단위에서 넓은 단위로 간다.
    """
    out: list[Scope] = []

    for i, col in enumerate(LITERATURE_COLUMNS, start=1):
        out.append(Scope(f"lit{i}", col, KIND_LITERATURE, (col,), round_name=col))
    out.append(Scope("lit", "문헌 전체", KIND_LITERATURE, tuple(LITERATURE_COLUMNS)))

    for round_name in FIELD_ROUNDS:
        cols = station_columns(spec, round_name)
        rk = _round_key(round_name)
        if spec.has_stations:
            for idx, col in enumerate(cols, start=1):
                out.append(Scope(
                    f"{rk}_st{idx}", f"{round_name} {station_label(idx)}",
                    KIND_STATION, (col,), round_name=round_name, station=idx))
            out.append(Scope(f"{rk}", f"{round_name} 전체", KIND_ROUND,
                             tuple(cols), round_name=round_name))
        else:
            out.append(Scope(rk, round_name, KIND_ROUND, tuple(cols),
                             round_name=round_name))

    field_all = tuple(c for r in FIELD_ROUNDS for c in station_columns(spec, r))
    out.append(Scope("field", "현지조사 전체", KIND_AGGREGATE, field_all))
    out.append(Scope("all", "전체", KIND_AGGREGATE, tuple(survey_columns(spec))))
    return out


def default_scope(spec: TaxonSpec) -> str:
    """처음 열었을 때 보여줄 단위."""
    return "all"


def unavailable_reason(scope: Scope, spec: TaxonSpec, item_tier: str) -> str | None:
    """이 단위에서 해당 계층 항목을 낼 수 없는 이유.

    낼 수 없는 항목을 숨기지 않고 사유와 함께 보여주기 위한 것이다.
    """
    if item_tier == "T3":
        if not spec.has_individuals:
            return spec.t3_unavailable_reason
        if not scope.has_field:
            return "문헌조사에는 개체수가 없습니다. 현지조사 단위를 고르십시오."
    return None
