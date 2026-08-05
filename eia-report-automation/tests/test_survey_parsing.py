"""출현값 파싱 테스트.

같은 "1" 이 분류군에 따라 다른 뜻을 가진다. 포유류의 1은 출현 표시,
조류의 1은 개체수 1개체다. 이 구분이 깨지면 모든 수치가 어긋난다.
"""

import pytest

from src.data.loader import normalize_text, parse_survey_value
from src.data.schema import COUNT, METHOD, PRESENCE, get_spec


def test_normalize_unicode_italic_scientific_name():
    # 마스터DB는 유니코드 수학 이탤릭, 가상데이터는 ASCII 로 같은 학명을 담는다
    assert normalize_text("𝐸𝑟𝑖𝑛𝑎𝑐𝑒𝑢𝑠 𝑎𝑚𝑢𝑟𝑒𝑛𝑠𝑖𝑠") == "Erinaceus amurensis"


def test_normalize_collapses_whitespace():
    assert normalize_text("  Hynobius   leechii ") == "Hynobius leechii"


@pytest.mark.parametrize("empty", [None, "", "-", "  "])
def test_blank_is_absent(empty):
    assert parse_survey_value(empty, COUNT, is_literature=False).present is False


def test_count_taxon_reads_individuals():
    r = parse_survey_value(147, COUNT, is_literature=False)
    assert r.present and r.individuals == 147


def test_presence_taxon_does_not_read_individuals():
    # 관속식물의 1은 개체수가 아니다
    r = parse_survey_value(1, PRESENCE, is_literature=False)
    assert r.present and r.individuals is None


def test_literature_column_never_reads_individuals():
    # 문헌조사는 분류군과 무관하게 출현 표시일 뿐이다
    r = parse_survey_value(1, COUNT, is_literature=True)
    assert r.present and r.individuals is None


def test_mammal_method_codes():
    r = parse_survey_value("TR/CT", METHOD, is_literature=False)
    assert r.present and set(r.methods) == {"TR", "CT"}


def test_unknown_method_code_is_flagged():
    r = parse_survey_value("SI/XX", METHOD, is_literature=False)
    assert r.methods == ("SI",)
    assert r.unknown_tokens == ("XX",)


def test_non_numeric_in_count_taxon_is_flagged():
    r = parse_survey_value("다수", COUNT, is_literature=False)
    assert r.present and r.individuals is None and r.unknown_tokens == ("다수",)


def test_spec_declares_quantitative_availability():
    assert get_spec("조류").has_individuals is True
    assert get_spec("관속식물").has_individuals is False
    assert "개체수가 없" in get_spec("포유류").t3_unavailable_reason
    assert get_spec("어류").t3_unavailable_reason is None


def test_spec_lookup_by_code_and_name():
    assert get_spec("birds") is get_spec("조류")
    with pytest.raises(KeyError):
        get_spec("없는분류군")
