"""법정 지위 판정 테스트.

등급 표기가 흔들려도 같은 결과가 나와야 한다. v7 정비 때 NFKC 정규화가
로마숫자를 ASCII 로 바꿔(멸Ⅱ → 멸II) 멸종위기야생생물이 전 분류군 0건으로
집계된 적이 있다. 그 회귀를 막는다.
"""

import pandas as pd
import pytest

from src.analysis.legal_status import summarize_legal
from src.data.schema import normalize_grade


@pytest.mark.parametrize("value,expected", [
    ("멸Ⅰ", "Ⅰ"), ("멸I", "Ⅰ"), ("Ⅰ", "Ⅰ"), ("I", "Ⅰ"), ("Ⅰ급", "Ⅰ"), ("멸1", "Ⅰ"),
    ("멸Ⅱ", "Ⅱ"), ("멸II", "Ⅱ"), ("Ⅱ", "Ⅱ"), ("II", "Ⅱ"), ("Ⅱ급", "Ⅱ"),
    ("Ⅲ", "Ⅲ"), ("III", "Ⅲ"), ("Ⅳ", "Ⅳ"), ("IV", "Ⅳ"), ("Ⅴ", "Ⅴ"), ("V", "Ⅴ"),
])
def test_grade_aliases_collapse(value, expected):
    assert normalize_grade(value) == expected


@pytest.mark.parametrize("empty", [None, "", "-", "  "])
def test_null_grade_is_empty(empty):
    assert normalize_grade(empty) == ""


def test_unknown_grade_passes_through():
    assert normalize_grade("LC") == "LC"


def frame(grades):
    n = len(grades)
    return pd.DataFrame({
        "korean_name": [f"종{i}" for i in range(n)],
        "scientific_name": [f"Genus sp{i}" for i in range(n)],
        "family_kr": ["가과"] * n,
        "멸종위기야생생물": grades,
        "천연기념물": ["-"] * n,
        "생태계교란생물": ["-"] * n,
        "abb2": ["-"] * n,
    })


def test_endangered_counted_with_unicode_roman():
    s = summarize_legal(frame(["멸Ⅰ", "멸Ⅱ", "멸Ⅱ", "-"]))
    assert len(s.endangered_1) == 1
    assert len(s.endangered_2) == 2
    assert s.endangered_total == 3


def test_endangered_counted_with_ascii_roman():
    # NFKC 를 거친 자료도 같은 결과가 나와야 한다
    s = summarize_legal(frame(["멸I", "멸II", "멸II", "-"]))
    assert len(s.endangered_1) == 1
    assert len(s.endangered_2) == 2


def test_both_representations_agree():
    a = summarize_legal(frame(["멸Ⅰ", "멸Ⅱ"])).counts
    b = summarize_legal(frame(["멸I", "멸II"])).counts
    assert a == b


def test_natural_monument_and_invasive():
    df = frame(["-", "-"])
    df.loc[0, "천연기념물"] = "O"
    df.loc[1, "생태계교란생물"] = "O"
    s = summarize_legal(df)
    assert len(s.natural_monument) == 1
    assert len(s.invasive) == 1
