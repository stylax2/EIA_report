"""HWPX 템플릿 추출 테스트.

업체마다 평가서 양식이 다르므로 스타일 ID 대신 번호 체계로 판정한다.
그 판정 규칙과, 실제 샘플에서 걸렸던 함정 두 가지를 지킨다.
"""

from pathlib import Path

import pytest

from src.hwpx.template import (
    _check,
    _classify,
    Heading,
    ReportTemplate,
    Slot,
    extract_template,
)

SAMPLE = (Path(__file__).resolve().parents[2] / "평가서샘플"
          / "(본안) 09.1.1 동식물상(대전열병합 현대화)_수정1.hwpx")


# ── 분류 규칙 ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,level", [
    ("9.1 자연생태환경", 1),
    ("9.1.1 동식물상", 1),
    ("가. 현 황", 1),
    ("1) 조사항목", 2),
    ("(1) 관속식물", 3),
    ("① 철새도래지", 4),
])
def test_heading_levels(text, level):
    kind, got, _, _ = _classify(text)
    assert kind == "heading"
    assert int(got) == level


@pytest.mark.parametrize("text,kind,number", [
    ("<표 9.1.1-1>  항목별 조사시기", "표", "9.1.1-1"),
    ("(그림 9.1.1-3) 식물구계 현황", "그림", "9.1.1-3"),
    ("<사진 8.1.1-1>  조사지역의 식생", "사진", "8.1.1-1"),
    ("【표 1-2】 종목록", "표", "1-2"),
])
def test_caption_detection(text, kind, number):
    got_kind, got_type, got_number, _ = _classify(text)
    assert got_kind == "caption"
    assert (got_type, got_number) == (kind, number)


def test_plain_text_is_not_classified():
    assert _classify("◦ 현지조사 결과 52과 113분류군이 확인되었다") is None


def test_caption_wins_over_heading():
    # '표 9.1.1-1' 은 숫자로 시작하지 않지만, 혼동 소지가 있는 형태를 확인
    kind, *_ = _classify("<표 9.1.1-1> 항목별 조사시기")
    assert kind == "caption"


# ── 양식 점검 ──────────────────────────────────────────────────────────

def template_with(slots):
    return ReportTemplate(source="t.hwpx", headings=[], slots=list(slots))


def test_detects_foreign_chapter_number():
    # 실제 샘플에 있던 결함: 9.1.1 문서에 8.1.1 캡션이 섞여 있다
    t = template_with([
        Slot("표", "9.1.1-1", "가", 1),
        Slot("표", "9.1.1-2", "나", 2),
        Slot("사진", "8.1.1-1", "다", 3),
    ])
    notes = _check(t)
    assert any("8.1.1-1" in n and "9.1.1" in n for n in notes)


def test_no_note_when_chapter_numbers_agree():
    t = template_with([Slot("표", "9.1.1-1", "가", 1), Slot("표", "9.1.1-2", "나", 2)])
    assert not [n for n in _check(t) if "장 번호" in n]


def test_detects_missing_caption_number():
    t = template_with([Slot("표", "9.1.1-1", "가", 1), Slot("표", "9.1.1-3", "나", 2)])
    assert any("비어 있습니다" in n and "2" in n for n in _check(t))


def test_warns_when_no_heading_found():
    assert any("목차를 찾지 못했" in n for n in _check(template_with([])))


# ── 번호 조율 ──────────────────────────────────────────────────────────
# 동·식물상 장 번호는 사업마다 다르다(7.1.1 · 8.1.1 · 9.1.1 …). 다른 평가
# 매체와의 순서로 정해지므로 고정하지 않고 다시 매길 수 있어야 한다.

def numbered(*specs):
    return template_with([Slot(k, n, f"제목{i}", i)
                          for i, (k, n) in enumerate(specs, start=1)])


def test_chapter_is_detected_from_captions():
    t = numbered(("표", "8.1.1-1"), ("표", "8.1.1-2"), ("그림", "8.1.1-1"))
    assert t.chapter == "8.1.1"


def test_chapter_is_empty_without_captions():
    assert template_with([]).chapter == ""


def test_renumber_rebases_chapter():
    t = numbered(("표", "9.1.1-1"), ("표", "9.1.1-2"))
    assert [s.number for s in t.renumber("7.1.1").tables] == ["7.1.1-1", "7.1.1-2"]


def test_renumber_keeps_series_separate():
    t = numbered(("표", "9.1.1-1"), ("그림", "9.1.1-1"), ("표", "9.1.1-2"))
    r = t.renumber("7.1.1")
    assert [s.number for s in r.tables] == ["7.1.1-1", "7.1.1-2"]
    assert [s.number for s in r.figures] == ["7.1.1-1"]


def test_renumber_closes_gaps():
    # 항목을 빼면 뒤 번호가 밀린다. 손으로 고치면 반드시 빠뜨린다.
    t = numbered(("표", "9.1.1-1"), ("표", "9.1.1-3"), ("표", "9.1.1-7"))
    assert [s.number for s in t.renumber().tables] == ["9.1.1-1", "9.1.1-2", "9.1.1-3"]


def test_renumber_fixes_foreign_chapter_number():
    # 다른 평가서에서 복사해 온 캡션이 제자리를 찾는다
    t = numbered(("그림", "9.1.1-1"), ("사진", "8.1.1-1"))
    r = t.renumber(merge_figures=True)
    assert [s.number for s in r.figures] == ["9.1.1-1", "9.1.1-2"]


def test_renumber_without_chapter_keeps_current():
    t = numbered(("표", "9.1.1-5"))
    assert t.renumber().tables[0].number == "9.1.1-1"


def test_renumber_updates_headings_too():
    t = numbered(("표", "9.1.1-1"))
    t.headings.append(Heading(level=1, marker="1", title="가", order=0,
                              slots=[t.slots[0]]))
    r = t.renumber("7.1.1")
    assert r.headings[0].slots[0].number == "7.1.1-1"


def test_renumber_does_not_mutate_original():
    t = numbered(("표", "9.1.1-1"))
    t.renumber("7.1.1")
    assert t.tables[0].number == "9.1.1-1"


# ── 실제 평가서 샘플 ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def template():
    """저장소의 실제 평가서. 25MB 라 한 번만 읽는다."""
    return extract_template(SAMPLE)


@pytest.mark.skipif(not SAMPLE.exists(), reason="평가서 샘플이 없습니다")
class TestRealSample:
    """저장소의 실제 평가서로 검증한다. 한글 프로그램 없이 읽힌다."""

    def test_extracts_outline_and_slots(self, template):
        assert len(template.headings) > 30
        assert len(template.tables) == 16
        assert len(template.figures) == 14

    def test_header_text_does_not_leak_into_heading(self, template):
        # 머리말이 본문 제목에 붙어 나오던 문제. 제목은 짧고 깔끔해야 한다.
        first = template.headings[0]
        assert first.title == "9.1 자연생태환경"
        assert "제 9 장" not in first.title

    def test_table_of_contents_table_does_not_leak(self, template):
        # 문단 안에 든 목차 표가 제목으로 섞이면 안 된다
        assert all(len(h.title) < 80 for h in template.headings)

    def test_slots_are_attached_to_headings(self, template):
        owned = sum(len(h.slots) for h in template.headings)
        assert owned == len(template.slots)

    def test_finds_real_chapter_number_defect(self, template):
        # 이 평가서에는 사진 8.1.1-1 이 섞여 있다
        assert any("8.1.1-1" in n for n in template.notes)
