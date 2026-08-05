"""분석 단위(Scope) 테스트.

임의 조합을 모두 계산하면 정점 5개일 때 4,095가지가 되어 감당할 수 없다.
업무상 의미 있는 단위만 열거하는지, 각 단위가 올바른 컬럼을 가리키는지
확인한다.
"""

import pytest

from src.analysis.scope import KIND_STATION, scopes_for
from src.data.schema import get_spec


def keys(spec):
    return [s.key for s in scopes_for(spec)]


def test_station_taxon_scope_count():
    # 문헌 3 + (정점 5 + 회차 1) × 2 + 현지 전체 + 전체 = 17
    assert len(scopes_for(get_spec("어류"))) == 17


def test_plain_taxon_scope_count():
    # 문헌 3 + 회차 2 + 현지 전체 + 전체 = 7
    assert len(scopes_for(get_spec("관속식물"))) == 7


def test_total_combinations():
    taxa = ["관속식물", "포유류", "조류", "양서류", "파충류",
            "육상곤충류", "어류", "저서성대형무척추동물"]
    assert sum(len(scopes_for(get_spec(t))) for t in taxa) == 76


def test_scope_keys_are_unique():
    for taxon in ("어류", "관속식물"):
        k = keys(get_spec(taxon))
        assert len(k) == len(set(k))


def test_every_taxon_has_all_scope():
    for taxon in ("어류", "관속식물", "포유류"):
        assert "all" in keys(get_spec(taxon))


def test_station_scope_targets_single_column():
    scopes = {s.key: s for s in scopes_for(get_spec("어류"))}
    st = scopes["field1_st1"]
    assert st.kind == KIND_STATION
    assert st.columns == ("현지조사1_St1",)
    assert st.station == 1
    assert st.is_single_column


def test_round_scope_covers_all_stations():
    scopes = {s.key: s for s in scopes_for(get_spec("어류"))}
    assert scopes["field1"].columns == tuple(
        f"현지조사1_St{i}" for i in range(1, 6))


def test_plain_taxon_round_is_one_column():
    scopes = {s.key: s for s in scopes_for(get_spec("관속식물"))}
    assert scopes["field1"].columns == ("현지조사1",)


def test_literature_scope_has_no_field():
    scopes = {s.key: s for s in scopes_for(get_spec("어류"))}
    lit = scopes["lit"]
    assert lit.has_literature and not lit.has_field


def test_field_scope_has_no_literature():
    scopes = {s.key: s for s in scopes_for(get_spec("어류"))}
    fld = scopes["field"]
    assert fld.has_field and not fld.has_literature
    assert len(fld.columns) == 10  # 2회차 × 5정점


def test_all_scope_covers_everything():
    spec = get_spec("어류")
    scopes = {s.key: s for s in scopes_for(spec)}
    assert len(scopes["all"].columns) == 12  # 문헌 2 + 현지 10
    assert scopes["all"].has_literature and scopes["all"].has_field


def test_field_rounds_detected():
    scopes = {s.key: s for s in scopes_for(get_spec("어류"))}
    assert scopes["field1_st3"].field_rounds == ["현지조사1"]
    assert scopes["field"].field_rounds == ["현지조사1", "현지조사2"]
    assert scopes["lit"].field_rounds == []
