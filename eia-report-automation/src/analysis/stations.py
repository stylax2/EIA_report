"""정점 기반 분석항목.

정점조사를 하는 어류·저서성대형무척추동물에만 적용한다. 조사지점이
없으면 평가서에서 사실상 필수인 지점별 표를 만들 수 없다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..data.schema import (
    FIELD_ROUNDS,
    TaxonSpec,
    station_columns,
    station_label,
)
from .diversity import CommunityIndices, analyze_community
from .taxon_specific import display_name


def sorensen(a: set[str], b: set[str]) -> float:
    """Sørensen 유사도 = 2|A∩B| / (|A|+|B|).

    출현 여부만으로 계산하므로 개체수가 없어도 쓸 수 있다. 두 지점이
    모두 비어 있으면 비교할 것이 없으므로 0으로 둔다.
    """
    if not a and not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


@dataclass
class StationSummary:
    """정점 하나의 집계."""

    index: int
    label: str
    column: str
    species_count: int
    individuals: int | None
    indices: CommunityIndices | None = None
    protected: list[str] = field(default_factory=list)


@dataclass
class StationAnalysis:
    """현지조사 회차 하나의 지점별 분석."""

    round_name: str
    stations: list[StationSummary]
    similarity: list[list[float]]  # 지점 × 지점 Sørensen
    shared_all: int  # 전 정점 공통 출현종
    unique_total: int  # 한 정점에서만 나온 종

    @property
    def labels(self) -> list[str]:
        return [s.label for s in self.stations]


def _station_species(occurred: pd.DataFrame, column: str) -> set[str]:
    present = occurred[f"present_{column}"]
    return set(occurred.loc[present, "species_id"].astype(str))


def analyze_round_stations(occurred: pd.DataFrame, spec: TaxonSpec,
                           round_name: str) -> StationAnalysis | None:
    """회차 하나를 정점별로 분석한다."""
    if not spec.has_stations:
        return None
    cols = [c for c in station_columns(spec, round_name)
            if f"present_{c}" in occurred.columns]
    if not cols:
        return None

    names = [display_name(r) for _, r in occurred.iterrows()]
    summaries: list[StationSummary] = []
    members: list[set[str]] = []

    for idx, col in enumerate(cols, start=1):
        present = occurred[f"present_{col}"]
        members.append(_station_species(occurred, col))

        individuals = None
        indices = None
        ind_col = f"ind_{col}"
        if ind_col in occurred.columns:
            counts = pd.to_numeric(occurred[ind_col], errors="coerce").fillna(0)
            if (counts > 0).any():
                individuals = int(counts.sum())
                indices = analyze_community(names, counts.tolist(),
                                            label=station_label(idx))

        protected = occurred.loc[
            present & (occurred.get("멸종위기야생생물", "-").astype(str) != "-")
        ]
        summaries.append(StationSummary(
            index=idx,
            label=station_label(idx),
            column=col,
            species_count=int(present.sum()),
            individuals=individuals,
            indices=indices,
            protected=[display_name(r) for _, r in protected.iterrows()],
        ))

    similarity = [[round(sorensen(a, b), 3) for b in members] for a in members]
    shared = set.intersection(*members) if members else set()
    counts_per_species: dict[str, int] = {}
    for m in members:
        for sid in m:
            counts_per_species[sid] = counts_per_species.get(sid, 0) + 1
    unique = sum(1 for v in counts_per_species.values() if v == 1)

    return StationAnalysis(
        round_name=round_name,
        stations=summaries,
        similarity=similarity,
        shared_all=len(shared),
        unique_total=unique,
    )


def analyze_stations(occurred: pd.DataFrame, spec: TaxonSpec) -> list[StationAnalysis]:
    """현지조사 전 회차를 정점별로 분석한다."""
    if not spec.has_stations:
        return []
    out = []
    for round_name in FIELD_ROUNDS:
        result = analyze_round_stations(occurred, spec, round_name)
        if result and any(s.species_count for s in result.stations):
            out.append(result)
    return out
