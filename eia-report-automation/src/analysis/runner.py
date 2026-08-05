"""분석 실행과 결과 집약.

분류군 하나를 **분석 단위(Scope)마다** 분석해 모은다. 이 결과가 웹페이지·
그래프·HWPX 조판의 공통 입력이며, 산출물마다 다시 계산하지 않는다.

종목록은 단위마다 다시 만들지 않는다. 전체 기준으로 한 번만 만들고 화면이
출현 비트로 걸러낸다(계산이 아니라 선별).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..data.loader import TaxonDataset, load_all
from ..data.schema import LITERATURE_COLUMNS, TaxonSpec, columns_in
from .diversity import CommunityIndices, analyze_community
from .legal_status import LegalSummary, summarize_legal
from .scope import Scope, scopes_for
from .species_summary import (
    SpeciesRow,
    TaxonomyComposition,
    Totals,
    build_species_rows,
    summarize_taxonomy,
    summarize_totals,
)
from .stations import StationAnalysis, analyze_stations
from .taxon_specific import SpecificItem, analyze_specific, display_name


@dataclass
class ScopeResult:
    """분석 단위 하나의 결과."""

    scope: Scope
    totals: Totals
    taxonomy: TaxonomyComposition
    legal: LegalSummary
    specific: list[SpecificItem] = field(default_factory=list)
    quantitative: list[CommunityIndices] = field(default_factory=list)
    quantitative_unavailable: str | None = None
    stations: list[StationAnalysis] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.scope.key


@dataclass
class TaxonResult:
    """분류군 하나의 분석 결과 전체.

    단위와 무관한 것(종목록·경고)은 여기에, 단위별 결과는 `scopes` 에 둔다.
    """

    spec: TaxonSpec
    total_species_in_db: int
    scopes: list[ScopeResult]
    species_rows: list[SpeciesRow]
    notes: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.spec.name

    def scope_result(self, key: str) -> ScopeResult:
        for s in self.scopes:
            if s.key == key:
                return s
        raise KeyError(f"[{self.name}] 알 수 없는 분석 단위: {key}")

    @property
    def overall(self) -> ScopeResult:
        """전체 단위. 요약·비교에 쓴다."""
        return self.scope_result("all")

    # 전체 단위를 가리키는 단축 속성. 기존 호출부가 그대로 동작한다.
    @property
    def totals(self) -> Totals:
        return self.overall.totals

    @property
    def taxonomy(self) -> TaxonomyComposition:
        return self.overall.taxonomy

    @property
    def legal(self) -> LegalSummary:
        return self.overall.legal

    @property
    def specific(self) -> list[SpecificItem]:
        return self.overall.specific

    @property
    def quantitative(self) -> list[CommunityIndices]:
        return self.overall.quantitative

    @property
    def quantitative_unavailable(self) -> str | None:
        return self.overall.quantitative_unavailable


def occurred_for(dataset: TaxonDataset, scope: Scope) -> pd.DataFrame:
    """분석 단위의 컬럼만으로 출현종을 고른다.

    개별 `present_{col}`·`ind_{col}` 은 로딩 때 이미 만들어 두었으므로
    집계 플래그만 다시 계산하고, 단위 밖 컬럼은 떨어낸다.
    """
    frame = dataset.frame
    cols = [c for c in scope.columns if f"present_{c}" in frame.columns]
    if not cols:
        return frame.iloc[0:0].copy()

    present = frame[[f"present_{c}" for c in cols]].any(axis=1)
    out = frame[present].copy()

    outside = [c for c in columns_in(frame) if c not in cols]
    out = out.drop(columns=[f"{prefix}{c}" for c in outside
                            for prefix in ("present_", "ind_", "method_")
                            if f"{prefix}{c}" in out.columns])

    lit = [c for c in cols if c in LITERATURE_COLUMNS]
    fld = [c for c in cols if c not in LITERATURE_COLUMNS]
    out["present_any"] = True
    out["present_lit"] = out[[f"present_{c}" for c in lit]].any(axis=1) if lit else False
    out["present_field"] = out[[f"present_{c}" for c in fld]].any(axis=1) if fld else False
    return out


def _quantitative(occurred: pd.DataFrame) -> list[CommunityIndices]:
    """컬럼별 군집지수. 컬럼을 합산하지 않는다.

    조사 시기·지점이 다른 자료를 섞으면 지수의 의미가 사라지기 때문이다.
    """
    out: list[CommunityIndices] = []
    if occurred.empty:
        return out
    names = [display_name(r) for _, r in occurred.iterrows()]
    for col in columns_in(occurred):
        ind_col = f"ind_{col}"
        if ind_col not in occurred.columns:
            continue
        counts = pd.to_numeric(occurred[ind_col], errors="coerce")
        if not (counts > 0).any():
            continue
        out.append(analyze_community(names, counts.fillna(0).tolist(), label=col))
    return out


def analyze_scope(dataset: TaxonDataset, scope: Scope) -> ScopeResult:
    """단위 하나를 분석한다."""
    occurred = occurred_for(dataset, scope)
    spec = dataset.spec

    result = ScopeResult(
        scope=scope,
        totals=summarize_totals(occurred),
        taxonomy=summarize_taxonomy(occurred),
        legal=summarize_legal(occurred),
        specific=analyze_specific(spec.name, occurred),
        stations=analyze_stations(occurred, spec) if scope.has_field else [],
    )

    if not spec.has_individuals:
        result.quantitative_unavailable = spec.t3_unavailable_reason
    elif not scope.has_field:
        result.quantitative_unavailable = (
            "문헌조사에는 개체수가 없습니다. 현지조사 단위를 고르십시오.")
    else:
        result.quantitative = _quantitative(occurred)
        if not result.quantitative:
            result.quantitative_unavailable = "개체수가 기록된 자료가 없습니다."

    return result


def analyze_taxon(dataset: TaxonDataset) -> TaxonResult:
    """분류군 하나를 모든 분석 단위로 분석한다."""
    return TaxonResult(
        spec=dataset.spec,
        total_species_in_db=len(dataset.frame),
        scopes=[analyze_scope(dataset, s) for s in scopes_for(dataset.spec)],
        species_rows=build_species_rows(dataset.occurred),
        notes=list(dataset.warnings),
    )


def analyze_all(master_path: Path | str, survey_path: Path | str) -> list[TaxonResult]:
    """8개 분류군을 모두 분석한다."""
    datasets = load_all(master_path, survey_path)
    return [analyze_taxon(d) for d in datasets.values()]
