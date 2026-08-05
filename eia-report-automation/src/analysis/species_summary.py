"""T1 공통 분석항목.

출현 여부만으로 8개 분류군 모두에서 산출한다. 항목 정의는
`docs/analysis_items.md` 3장에 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..data.schema import FIELD_COLUMNS, LITERATURE_COLUMNS, is_null_token
from .taxon_specific import display_name

# 마스터DB에 과명이 없는 종(조류 22건 등)의 표시값
UNKNOWN_FAMILY = "과 미상"


@dataclass
class Totals:
    """T1-01~03 종수 집계."""

    total: int  # 총 출현종수
    literature: int  # 문헌조사 출현종
    field_survey: int  # 현지조사 출현종
    both: int  # 문헌·현지 공통
    literature_only: int  # 문헌 단독
    field_only: int  # 현지 단독(문헌 미기재 신규 확인종)
    by_column: dict[str, int]  # 컬럼별 출현종수
    new_in_field_round2: int  # 현지 1차 미확인 → 2차 확인


def summarize_totals(occurred: pd.DataFrame) -> Totals:
    lit = occurred["present_lit"]
    fld = occurred["present_field"]
    r1, r2 = (f"present_{c}" for c in FIELD_COLUMNS)
    return Totals(
        total=len(occurred),
        literature=int(lit.sum()),
        field_survey=int(fld.sum()),
        both=int((lit & fld).sum()),
        literature_only=int((lit & ~fld).sum()),
        field_only=int((~lit & fld).sum()),
        by_column={c: int(occurred[f"present_{c}"].sum())
                   for c in LITERATURE_COLUMNS + FIELD_COLUMNS},
        new_in_field_round2=int((~occurred[r1] & occurred[r2]).sum()),
    )


@dataclass
class TaxonomyComposition:
    """T1-04 분류체계별 구성."""

    by_order: list[tuple[str, int]]  # (목명, 종수)
    by_family: list[tuple[str, int]]  # (과명, 종수) 내림차순
    order_count: int
    family_count: int


def summarize_taxonomy(occurred: pd.DataFrame, top_families: int = 15) -> TaxonomyComposition:
    fam = occurred["family_kr"].value_counts()
    order_col = "order_kr" if "order_kr" in occurred.columns else "family_kr"
    orders = occurred[order_col].value_counts()
    return TaxonomyComposition(
        by_order=[(str(k), int(v)) for k, v in orders.head(top_families).items()],
        by_family=[(str(k), int(v)) for k, v in fam.head(top_families).items()],
        order_count=int(orders.size),
        family_count=int(fam.size),
    )


@dataclass
class SpeciesRow:
    """T1-08 종목록의 한 행."""

    family: str
    scientific_name: str
    korean_name: str
    abb: str
    abb2: str
    marks: dict[str, bool]  # 컬럼별 출현 표시
    individuals: int | None = None


def build_species_rows(occurred: pd.DataFrame) -> list[SpeciesRow]:
    """종목록 표 데이터를 만든다. 과명·학명 순으로 정렬한다."""
    cols = LITERATURE_COLUMNS + FIELD_COLUMNS
    ind_cols = [f"ind_{c}" for c in FIELD_COLUMNS if f"ind_{c}" in occurred.columns]
    rows: list[SpeciesRow] = []
    for _, r in occurred.iterrows():
        total_ind = None
        if ind_cols:
            vals = [r[c] for c in ind_cols if pd.notna(r[c])]
            total_ind = int(sum(vals)) if vals else None
        rows.append(
            SpeciesRow(
                family=UNKNOWN_FAMILY if is_null_token(r["family_kr"]) else str(r["family_kr"]),
                scientific_name=str(r["scientific_name"]),
                korean_name=display_name(r),
                abb="" if is_null_token(r.get("abb")) else str(r["abb"]),
                abb2="" if is_null_token(r.get("abb2")) else str(r["abb2"]),
                marks={c: bool(r[f"present_{c}"]) for c in cols},
                individuals=total_ind,
            )
        )
    # 과명이 비어 있는 종은 목록 끝으로 보낸다. 앞에 오면 검수에 방해가 된다.
    rows.sort(key=lambda x: (x.family == UNKNOWN_FAMILY, x.family, x.scientific_name))
    return rows
