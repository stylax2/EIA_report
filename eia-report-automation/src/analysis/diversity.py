"""생태통계 지수 계산.

기획안 4.2. 모든 지수는 Python 에서 확정하며 LLM 에 계산을 넘기지 않는다.
"""

from __future__ import annotations

from collections.abc import Sequence


def dominance(counts: Sequence[int]) -> float:
    """우점도(McNaughton) 를 계산한다."""
    raise NotImplementedError


def shannon_diversity(counts: Sequence[int]) -> float:
    """종다양도(Shannon-Wiener H') 를 계산한다."""
    raise NotImplementedError


def evenness(counts: Sequence[int]) -> float:
    """균등도(Pielou J') 를 계산한다."""
    raise NotImplementedError


def richness(counts: Sequence[int]) -> float:
    """풍부도(Margalef R1) 를 계산한다."""
    raise NotImplementedError
