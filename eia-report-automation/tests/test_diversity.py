"""생태통계 지수 테스트.

지수 계산은 보고서 수치의 근거이므로 손으로 검산한 값과 대조한다.
구현 전이므로 현재는 모두 skip 된다.
"""

import pytest

from src.analysis import diversity


@pytest.mark.skip(reason="구현 예정")
def test_shannon_diversity_uniform():
    # 네 종이 균등하면 H' = ln(4)
    assert diversity.shannon_diversity([10, 10, 10, 10]) == pytest.approx(1.3863, abs=1e-4)


@pytest.mark.skip(reason="구현 예정")
def test_shannon_diversity_single_species():
    # 한 종뿐이면 H' = 0
    assert diversity.shannon_diversity([10]) == pytest.approx(0.0)


@pytest.mark.skip(reason="구현 예정")
def test_evenness_uniform():
    # 균등 분포의 J' = 1
    assert diversity.evenness([5, 5, 5, 5]) == pytest.approx(1.0)


@pytest.mark.skip(reason="구현 예정")
def test_dominance_range():
    # 우점도는 0 과 1 사이
    assert 0.0 <= diversity.dominance([50, 30, 20]) <= 1.0
