"""정점 분석 테스트.

유사도는 평가서에 실리는 수치이므로 손으로 검산한 값과 대조한다.
"""

import pandas as pd
import pytest

from src.analysis.stations import analyze_round_stations, sorensen
from src.data.schema import get_spec


def test_sorensen_identical_sets():
    assert sorensen({"a", "b", "c"}, {"a", "b", "c"}) == pytest.approx(1.0)


def test_sorensen_disjoint_sets():
    assert sorensen({"a", "b"}, {"c", "d"}) == pytest.approx(0.0)


def test_sorensen_half_overlap():
    # 2 × |{b}| / (2 + 2) = 0.5
    assert sorensen({"a", "b"}, {"b", "c"}) == pytest.approx(0.5)


def test_sorensen_uneven_sizes():
    # 2 × 1 / (1 + 3) = 0.5
    assert sorensen({"a"}, {"a", "b", "c"}) == pytest.approx(0.5)


def test_sorensen_empty_pair_is_zero():
    assert sorensen(set(), set()) == pytest.approx(0.0)


def test_sorensen_is_symmetric():
    a, b = {"a", "b", "c"}, {"b", "c", "d", "e"}
    assert sorensen(a, b) == pytest.approx(sorensen(b, a))


def frame(per_station):
    """정점별 개체수 표를 만든다. per_station[i] 가 i번 정점의 개체수 목록."""
    n = len(per_station[0])
    data = {
        "species_id": [f"F{i:03d}" for i in range(n)],
        "korean_name": [f"종{i}" for i in range(n)],
        "scientific_name": [f"Genus sp{i}" for i in range(n)],
        "family_kr": ["가과"] * n,
        "멸종위기야생생물": ["-"] * n,
    }
    for idx, counts in enumerate(per_station, start=1):
        col = f"현지조사1_St{idx}"
        data[f"present_{col}"] = [c > 0 for c in counts]
        data[f"ind_{col}"] = [c if c > 0 else None for c in counts]
    return pd.DataFrame(data)


def test_station_counts_and_individuals():
    df = frame([[5, 0, 3], [0, 4, 3]])
    a = analyze_round_stations(df, get_spec("어류"), "현지조사1")
    assert [s.species_count for s in a.stations[:2]] == [2, 2]
    assert [s.individuals for s in a.stations[:2]] == [8, 7]


def test_station_similarity_matrix_shape_and_diagonal():
    df = frame([[1, 1, 0], [1, 0, 1]])
    a = analyze_round_stations(df, get_spec("어류"), "현지조사1")
    n = len(a.stations)
    assert len(a.similarity) == n
    assert all(len(row) == n for row in a.similarity)
    # 자기 자신과의 유사도는 1(출현종이 있는 정점만)
    assert a.similarity[0][0] == pytest.approx(1.0)


def test_shared_and_unique_counts():
    # St.1={종0,종1}, St.2={종0,종2}
    df = frame([[1, 1, 0], [1, 0, 1]])
    a = analyze_round_stations(df, get_spec("어류"), "현지조사1")
    assert a.shared_all == 1  # 종0 은 두 정점 모두에서
    assert a.unique_total == 2  # 종1, 종2 는 한 정점에서만


def test_labels_use_report_notation():
    df = frame([[1, 0], [0, 1]])
    a = analyze_round_stations(df, get_spec("어류"), "현지조사1")
    assert a.labels[:2] == ["St.1", "St.2"]


def test_non_station_taxon_returns_none():
    df = frame([[1, 1]])
    assert analyze_round_stations(df, get_spec("관속식물"), "현지조사1") is None
