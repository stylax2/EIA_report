"""T3 정량 분석항목 — 군집지수.

개체수가 있는 분류군(조류·어류·저서성대형무척추동물)에만 적용한다.
지수는 조사차수별로 각각 산출한다. 차수를 합산하면 조사 시기가 다른
자료를 섞게 되므로 평가서에서 쓰지 않는다.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


def _clean(counts: Sequence[float]) -> list[float]:
    return [float(c) for c in counts if c is not None and float(c) > 0]


def dominance(counts: Sequence[float]) -> float:
    """우점도 DI = (n1 + n2) / N. 상위 2종이 차지하는 비율이다."""
    c = sorted(_clean(counts), reverse=True)
    if not c:
        return 0.0
    return sum(c[:2]) / sum(c)


def shannon_diversity(counts: Sequence[float]) -> float:
    """종다양도 H' = -Σ(ni/N · ln(ni/N))."""
    c = _clean(counts)
    if not c:
        return 0.0
    total = sum(c)
    return -sum((n / total) * math.log(n / total) for n in c)


def evenness(counts: Sequence[float]) -> float:
    """균등도 J' = H' / ln S. 단일종이면 정의되지 않아 0으로 둔다."""
    c = _clean(counts)
    if len(c) <= 1:
        return 0.0
    return shannon_diversity(c) / math.log(len(c))


def richness(counts: Sequence[float]) -> float:
    """풍부도 R1 = (S - 1) / ln N."""
    c = _clean(counts)
    if not c:
        return 0.0
    total = sum(c)
    if total <= 1:
        return 0.0
    return (len(c) - 1) / math.log(total)


@dataclass
class CommunityIndices:
    """조사차수 하나의 군집 분석 결과."""

    label: str
    species_count: int  # S
    individuals: int  # N
    dominance: float  # DI
    diversity: float  # H'
    evenness: float  # J'
    richness: float  # R1
    dominant: list[tuple[str, int, float]]  # (국명, 개체수, 상대풍부도 %)

    @property
    def dominant_species(self) -> str:
        return self.dominant[0][0] if self.dominant else "-"

    @property
    def subdominant_species(self) -> str:
        return self.dominant[1][0] if len(self.dominant) > 1 else "-"


def analyze_community(names: Sequence[str], counts: Sequence[float], label: str,
                      top: int = 5) -> CommunityIndices:
    """종명과 개체수로 군집지수와 우점종을 낸다."""
    pairs = [(str(n), float(c)) for n, c in zip(names, counts)
             if c is not None and float(c) > 0]
    total = sum(c for _, c in pairs)
    values = [c for _, c in pairs]
    ranked = sorted(pairs, key=lambda x: -x[1])[:top]
    return CommunityIndices(
        label=label,
        species_count=len(pairs),
        individuals=int(total),
        dominance=dominance(values),
        diversity=shannon_diversity(values),
        evenness=evenness(values),
        richness=richness(values),
        dominant=[(n, int(c), c / total * 100 if total else 0.0) for n, c in ranked],
    )
