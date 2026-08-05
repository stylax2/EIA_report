"""분석항목 판정 규칙 테스트.

판정은 기계적이어야 한다. 문서와 화면이 같은 값을 가리키려면 규칙이
데이터에서만 나와야 하고, 사람이 손으로 정한 값이 섞이면 안 된다.
"""

import pytest

from src.analysis.item_catalog import (
    ITEMS,
    LIMITED,
    MAX_GRAPH_CATEGORIES,
    NONE,
    OK,
    _by_categories,
)


def test_zero_categories_is_impossible():
    assert _by_categories(0, "범주").mark == NONE


def test_few_categories_prefer_table():
    assert _by_categories(2, "목").mark == LIMITED


def test_moderate_categories_suit_graph():
    for n in (3, 5, 8, MAX_GRAPH_CATEGORIES):
        assert _by_categories(n, "범주").mark == OK, n


def test_many_categories_are_truncated():
    v = _by_categories(546, "과")
    assert v.mark == LIMITED
    assert str(MAX_GRAPH_CATEGORIES) in v.reason


def test_tiny_taxon_has_no_graph_value():
    # 종수가 적으면 범주가 충분해도 그래프 실익이 없다
    assert _by_categories(5, "범주", species=4).mark == NONE


def test_every_verdict_carries_a_reason():
    for n in (0, 2, 6, 100):
        assert _by_categories(n, "범주").reason


def test_item_codes_are_unique():
    codes = [i.code for i in ITEMS]
    assert len(codes) == len(set(codes))


def test_tiers_are_known():
    assert {i.tier for i in ITEMS} <= {"T1", "T2", "T3"}


def test_t3_items_limited_to_count_taxa():
    # 개체수를 기록하는 분류군에만 T3 를 걸어야 한다
    for item in ITEMS:
        if item.tier == "T3":
            assert item.taxa == ("조류", "어류", "저서성대형무척추동물")


def test_t1_items_apply_to_all_taxa():
    for item in ITEMS:
        if item.tier == "T1":
            assert item.taxa is None
            assert item.applies_to("아무분류군")
