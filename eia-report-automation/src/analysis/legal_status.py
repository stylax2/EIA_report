"""T1-05~07 법정보호종·생태계교란생물·시·도보호종.

마스터DB의 법정 지위 컬럼에서 추출한다. 최종 판정은 사람이 확인한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..data.schema import is_null_token, normalize_grade
from .taxon_specific import display_name


@dataclass
class ProtectedSpecies:
    korean_name: str
    scientific_name: str
    family: str
    grade: str  # 멸Ⅰ / 멸Ⅱ / 천연기념물 / 교란종 / 시·도보호종


@dataclass
class LegalSummary:
    """법정 지위별 종수와 목록."""

    endangered_1: list[ProtectedSpecies] = field(default_factory=list)
    endangered_2: list[ProtectedSpecies] = field(default_factory=list)
    natural_monument: list[ProtectedSpecies] = field(default_factory=list)
    invasive: list[ProtectedSpecies] = field(default_factory=list)
    local_protected: list[ProtectedSpecies] = field(default_factory=list)

    @property
    def endangered_total(self) -> int:
        return len(self.endangered_1) + len(self.endangered_2)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "멸종위기야생생물 Ⅰ급": len(self.endangered_1),
            "멸종위기야생생물 Ⅱ급": len(self.endangered_2),
            "천연기념물": len(self.natural_monument),
            "생태계교란생물": len(self.invasive),
            "시·도보호종": len(self.local_protected),
        }


def _entry(row: pd.Series, grade: str) -> ProtectedSpecies:
    return ProtectedSpecies(
        korean_name=display_name(row),
        scientific_name=str(row["scientific_name"]),
        family=str(row["family_kr"]),
        grade=grade,
    )


def summarize_legal(occurred: pd.DataFrame) -> LegalSummary:
    """출현종 중 법정 지위를 가진 종을 추출한다."""
    out = LegalSummary()
    for _, r in occurred.iterrows():
        # 표기가 흔들려도(멸Ⅱ / 멸II / Ⅱ급) 같은 등급으로 판정한다
        grade = normalize_grade(r.get("멸종위기야생생물"))
        if grade == "Ⅰ":
            out.endangered_1.append(_entry(r, "멸종위기야생생물 Ⅰ급"))
        elif grade == "Ⅱ":
            out.endangered_2.append(_entry(r, "멸종위기야생생물 Ⅱ급"))
        if not is_null_token(r.get("천연기념물")):
            out.natural_monument.append(_entry(r, "천연기념물"))
        if not is_null_token(r.get("생태계교란생물")):
            out.invasive.append(_entry(r, "생태계교란생물"))
        if not is_null_token(r.get("abb2")):
            out.local_protected.append(_entry(r, str(r["abb2"]).strip()))
    return out
