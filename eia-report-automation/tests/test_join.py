"""조인 테스트.

v7 부터 species_id 로 조인한다. 사용자가 조사자료를 정렬하거나 행을
지워도 결과가 흔들리지 않아야 한다.
"""

import pandas as pd
import pytest

from src.data.loader import _join_by_id, _join_by_position


def master(ids=("A1", "A2", "A3")):
    return pd.DataFrame({
        "species_id": list(ids),
        "family_kr": ["가과", "나과", "다과"][:len(ids)],
        "scientific_name": ["Genus a", "Genus b", "Genus c"][:len(ids)],
        "korean_name": ["가", "나", "다"][:len(ids)],
    })


def survey(ids, lit1=None):
    n = len(ids)
    return pd.DataFrame({
        "species_id": list(ids),
        "scientific_name": ["Genus a", "Genus b", "Genus c"][:n],
        "korean_name": ["가", "나", "다"][:n],
        "문헌1": lit1 if lit1 is not None else [1] * n,
        "문헌2": [None] * n,
        "현지조사1": [None] * n,
        "현지조사2": [None] * n,
    })


def test_join_by_id_is_order_independent():
    # 조사자료를 뒤집어도 마스터 순서대로 값이 붙는다
    s = survey(["A3", "A2", "A1"], lit1=[1, None, None])
    df, warnings = _join_by_id(master(), s, "테스트")
    got = df["문헌1"]
    assert got.isna().tolist() == [True, True, False]  # A1·A2 미기록, A3 기록
    assert got.iloc[2] == 1
    assert warnings == []


def test_join_by_id_allows_missing_rows():
    # 조사자료에서 행을 지우면 미출현으로 처리하고 경고만 남긴다
    df, warnings = _join_by_id(master(), survey(["A1"]), "테스트")
    assert len(df) == 3
    assert df["문헌1"].isna().sum() == 2
    assert any("기록이 없는 종" in w for w in warnings)


def test_join_by_id_rejects_duplicate_ids():
    s = survey(["A1", "A1", "A2"])
    with pytest.raises(ValueError, match="중복"):
        _join_by_id(master(), s, "테스트")


def test_join_by_id_rejects_unknown_id():
    s = survey(["A1", "A2", "Z9"])
    with pytest.raises(ValueError, match="마스터DB에 없는"):
        _join_by_id(master(), s, "테스트")


def test_position_join_warns_about_missing_key():
    df, warnings = _join_by_position(master(), survey(["A1", "A2", "A3"]), "테스트")
    assert any("species_id 가 없어" in w for w in warnings)


def test_position_join_detects_reordering():
    # v6 방식은 행을 섞으면 국명 대조에서 걸린다
    s = survey(["A1", "A2", "A3"])
    s.loc[0, "korean_name"] = "다"
    with pytest.raises(ValueError, match="어긋납니다"):
        _join_by_position(master(), s, "테스트")


def test_position_join_detects_row_count_change():
    with pytest.raises(ValueError, match="행 수가 다릅니다"):
        _join_by_position(master(), survey(["A1", "A2"]), "테스트")
