"""군집지수 테스트.

지수 계산은 보고서 수치의 근거이므로 손으로 검산한 값과 대조한다.
"""

import math

import pytest

from src.analysis import diversity


def test_shannon_uniform():
    # 네 종이 균등하면 H' = ln(4)
    assert diversity.shannon_diversity([10, 10, 10, 10]) == pytest.approx(math.log(4))


def test_shannon_single_species():
    assert diversity.shannon_diversity([10]) == pytest.approx(0.0)


def test_shannon_ignores_zero_and_none():
    assert diversity.shannon_diversity([10, 0, None, 10]) == pytest.approx(math.log(2))


def test_evenness_uniform():
    assert diversity.evenness([5, 5, 5, 5]) == pytest.approx(1.0)


def test_evenness_single_species_is_zero():
    # ln(1) = 0 이라 정의되지 않는다. 0으로 둔다.
    assert diversity.evenness([7]) == pytest.approx(0.0)


def test_dominance_top_two():
    # (50 + 30) / 100
    assert diversity.dominance([50, 30, 15, 5]) == pytest.approx(0.8)


def test_richness():
    # (S - 1) / ln N = 3 / ln(100)
    assert diversity.richness([25, 25, 25, 25]) == pytest.approx(3 / math.log(100))


def test_empty_input_is_zero():
    for fn in (diversity.dominance, diversity.shannon_diversity,
               diversity.evenness, diversity.richness):
        assert fn([]) == pytest.approx(0.0)


def test_analyze_community_ranks_dominant():
    r = diversity.analyze_community(["가", "나", "다"], [10, 60, 30], label="현지조사1")
    assert r.species_count == 3
    assert r.individuals == 100
    assert r.dominant_species == "나"
    assert r.subdominant_species == "다"
    assert r.dominant[0][2] == pytest.approx(60.0)  # 상대풍부도 %


def test_analyze_community_excludes_absent_species():
    # 개체수 0인 종은 종수에 들어가지 않는다
    r = diversity.analyze_community(["가", "나", "다"], [10, 0, 5], label="x")
    assert r.species_count == 2
