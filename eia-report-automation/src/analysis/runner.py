"""분석 실행과 결과 집약.

분류군 하나의 모든 분석 결과를 `TaxonResult` 로 모은다. 이 객체가
웹페이지·그래프·HWPX 조판의 공통 입력이며, 산출물마다 다시 계산하지
않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..data.loader import TaxonDataset, load_all
from ..data.schema import FIELD_COLUMNS, TaxonSpec
from .diversity import CommunityIndices, analyze_community
from .legal_status import LegalSummary, summarize_legal
from .species_summary import (
    SpeciesRow,
    TaxonomyComposition,
    Totals,
    build_species_rows,
    summarize_taxonomy,
    summarize_totals,
)
from .taxon_specific import SpecificItem, analyze_specific, display_name


@dataclass
class TaxonResult:
    """분류군 하나의 분석 결과 전체."""

    spec: TaxonSpec
    total_species_in_db: int
    totals: Totals
    taxonomy: TaxonomyComposition
    legal: LegalSummary
    species_rows: list[SpeciesRow]
    specific: list[SpecificItem] = field(default_factory=list)
    quantitative: list[CommunityIndices] = field(default_factory=list)
    quantitative_unavailable: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.spec.name


def _quantitative(dataset: TaxonDataset, occurred: pd.DataFrame) -> list[CommunityIndices]:
    """현지조사 차수별 군집지수. 차수를 합산하지 않는다."""
    out: list[CommunityIndices] = []
    for col in FIELD_COLUMNS:
        ind_col = f"ind_{col}"
        if ind_col not in occurred.columns:
            continue
        counts = pd.to_numeric(occurred[ind_col], errors="coerce")
        if not (counts > 0).any():
            continue
        names = [display_name(r) for _, r in occurred.iterrows()]
        out.append(analyze_community(names, counts.fillna(0).tolist(), label=col))
    return out


def analyze_taxon(dataset: TaxonDataset) -> TaxonResult:
    """데이터셋 하나에 T1 → T2 → T3 순으로 분석을 실행한다."""
    occurred = dataset.occurred
    spec = dataset.spec

    result = TaxonResult(
        spec=spec,
        total_species_in_db=len(dataset.frame),
        totals=summarize_totals(occurred),
        taxonomy=summarize_taxonomy(occurred),
        legal=summarize_legal(occurred),
        species_rows=build_species_rows(occurred),
        specific=analyze_specific(spec.name, occurred),
        notes=list(dataset.warnings),
    )

    if spec.has_individuals:
        result.quantitative = _quantitative(dataset, occurred)
        if not result.quantitative:
            result.quantitative_unavailable = "개체수가 기록된 현지조사 자료가 없습니다."
    else:
        result.quantitative_unavailable = spec.t3_unavailable_reason

    return result


def analyze_all(master_path: Path | str, survey_path: Path | str) -> list[TaxonResult]:
    """8개 분류군을 모두 분석한다."""
    datasets = load_all(master_path, survey_path)
    return [analyze_taxon(d) for d in datasets.values()]
