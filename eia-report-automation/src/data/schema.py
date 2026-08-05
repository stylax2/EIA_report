"""분류군별 원자료 사양.

출현 컬럼의 값이 분류군마다 다른 의미를 가지므로(포유류의 "1"은 출현
표시, 조류의 "1"은 개체수 1개체), 파싱 규칙을 여기서 선언한다.
자세한 배경은 `docs/analysis_workflow.md` 3장에 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LITERATURE_COLUMNS = ["문헌1", "문헌2"]
FIELD_ROUNDS = ["현지조사1", "현지조사2"]

# 정점조사를 하지 않는 분류군의 현지조사 컬럼. 정점 분류군은
# `field_columns(spec)` 가 회차 × 정점으로 펼쳐 준다.
FIELD_COLUMNS = list(FIELD_ROUNDS)
SURVEY_COLUMNS = LITERATURE_COLUMNS + FIELD_COLUMNS

INPUT_COLUMNS = ["family_kr", "scientific_name", "korean_name", "abb", "abb2"]

# 정점 컬럼 이름 규칙: 현지조사1_St1 … 표기는 화면에서 'St.1' 로 바꾼다.
STATION_SEPARATOR = "_St"

# 포유류 현지조사 방법 약어 (가상데이터 범례 시트)
MAMMAL_METHODS = {
    "SI": "목견",
    "TR": "족적",
    "SC": "배설물",
    "AU": "청문",
    "CT": "카메라트랩",
}

# 현지조사 값의 해석 방식
PRESENCE = "presence"  # 1 = 출현 표시
COUNT = "count"  # 정수 = 개체수
METHOD = "method"  # SI/TR/... = 조사방법 코드


@dataclass(frozen=True)
class TaxonSpec:
    """분류군 하나의 원자료 사양과 적용 가능한 분석항목."""

    code: str  # 영문 키. 플레이스홀더·폴더명·파일명에 쓴다
    name: str  # 시트명이자 보고서 표기명
    field_value: str  # PRESENCE | COUNT | METHOD
    specific_items: tuple[str, ...] = ()  # T2 분류군 특이 항목
    stations: int = 0  # 정점조사 정점 수. 0 이면 정점 구분 없음

    @property
    def has_stations(self) -> bool:
        """정점조사를 하는가. 지점별 분석 가능 여부와 같다."""
        return self.stations > 0

    @property
    def has_individuals(self) -> bool:
        """개체수를 기록하는가. T3 정량분석 가능 여부와 같다."""
        return self.field_value == COUNT

    @property
    def t3_unavailable_reason(self) -> str | None:
        if self.has_individuals:
            return None
        if self.field_value == METHOD:
            return "현지조사를 조사방법 코드로 기록하여 개체수가 없습니다."
        return "현지조사를 출현 여부로만 기록하여 개체수가 없습니다."


TAXON_SPECS: tuple[TaxonSpec, ...] = (
    TaxonSpec("plants", "관속식물", PRESENCE,
              ("식물구계학적특정종", "희귀식물등급", "특산식물", "귀화식물", "생활형")),
    TaxonSpec("mammals", "포유류", METHOD, ("조사방법",)),
    TaxonSpec("birds", "조류", COUNT, ("도래유형",)),
    TaxonSpec("amphibians", "양서류", PRESENCE),
    TaxonSpec("reptiles", "파충류", PRESENCE),
    TaxonSpec("insects", "육상곤충류", PRESENCE, ("고유종",)),
    # 어류·저서성대형무척추동물은 정점조사를 한다
    TaxonSpec("fish", "어류", COUNT, ("고유종", "외래종"), stations=5),
    TaxonSpec("benthos", "저서성대형무척추동물", COUNT, ("오수생물지수",), stations=5),
)

SPEC_BY_NAME = {s.name: s for s in TAXON_SPECS}
SPEC_BY_CODE = {s.code: s for s in TAXON_SPECS}

# 마스터DB 법정 지위 컬럼. 분류군에 따라 존재하지 않을 수 있다.
LEGAL_COLUMNS = ["멸종위기야생생물", "천연기념물", "생태계교란생물"]

# "값 없음"을 나타내는 표기
NULL_TOKENS = {"-", "", "nan", "None", "NaN"}


def is_null_token(value: object) -> bool:
    return value is None or str(value).strip() in NULL_TOKENS


# 로마숫자 등급은 표기가 흔들린다. 원자료는 유니코드 로마숫자(Ⅰ~Ⅴ)를 쓰지만
# NFKC 정규화를 거치면 ASCII(I~V)가 되고, 손입력에는 아라비아 숫자도 섞인다.
# 판정 코드가 특정 표기를 직접 찾으면 표기가 바뀌는 순간 조용히 0건이 된다.
ROMAN_ALIASES = {
    "Ⅰ": "Ⅰ", "I": "Ⅰ", "1": "Ⅰ",
    "Ⅱ": "Ⅱ", "II": "Ⅱ", "2": "Ⅱ",
    "Ⅲ": "Ⅲ", "III": "Ⅲ", "3": "Ⅲ",
    "Ⅳ": "Ⅳ", "IV": "Ⅳ", "4": "Ⅳ",
    "Ⅴ": "Ⅴ", "V": "Ⅴ", "5": "Ⅴ",
}


def normalize_grade(value: object) -> str:
    """등급 표기를 유니코드 로마숫자로 통일한다.

    접두사(멸)와 접미사(급)를 떼고 숫자 부분만 본다.
    '멸Ⅱ', '멸II', 'Ⅱ급', 'II' 는 모두 'Ⅱ' 가 된다. 등급을 찾지 못하면
    원래 문자열을 그대로 돌려준다.
    """
    if is_null_token(value):
        return ""
    text = str(value).strip()
    core = text.removeprefix("멸").removesuffix("급").strip()
    return ROMAN_ALIASES.get(core.upper(), text)


def station_label(index: int) -> str:
    """정점 번호를 평가서 표기로. 1 → 'St.1'"""
    return f"St.{index}"


def station_columns(spec: TaxonSpec, round_name: str) -> list[str]:
    """현지조사 회차 하나의 컬럼 목록.

    정점 분류군은 회차가 정점 수만큼 펼쳐지고, 아니면 회차 자체가 컬럼이다.
    """
    if not spec.has_stations:
        return [round_name]
    return [f"{round_name}{STATION_SEPARATOR}{i}" for i in range(1, spec.stations + 1)]


def field_columns(spec: TaxonSpec) -> list[str]:
    """현지조사 컬럼 전체."""
    return [c for r in FIELD_ROUNDS for c in station_columns(spec, r)]


def survey_columns(spec: TaxonSpec) -> list[str]:
    """분류군의 출현 컬럼 전체. 문헌조사는 정점 개념이 없다."""
    return LITERATURE_COLUMNS + field_columns(spec)


# 로더가 붙이는 집계 플래그. 개별 출현 컬럼과 구분해야 한다.
DERIVED_FLAGS = {"present_any", "present_lit", "present_field"}


def columns_in(df) -> list[str]:
    """DataFrame 에 실제로 실린 출현 컬럼 목록.

    정점 유무에 따라 컬럼이 달라지므로 상수 대신 자료에서 읽는다.
    """
    return [c[len("present_"):] for c in df.columns
            if c.startswith("present_") and c not in DERIVED_FLAGS]


def split_columns(columns: list[str]) -> tuple[list[str], list[str]]:
    """출현 컬럼을 (문헌, 현지)로 나눈다."""
    lit = [c for c in columns if c in LITERATURE_COLUMNS]
    return lit, [c for c in columns if c not in LITERATURE_COLUMNS]


def round_of(column: str) -> str:
    """컬럼이 속한 조사 회차. 정점 컬럼이면 정점 부분을 뗀다."""
    return parse_station(column)[0]


def parse_station(column: str) -> tuple[str, int | None]:
    """컬럼명을 (회차, 정점번호)로 나눈다. 정점이 없으면 번호는 None."""
    if STATION_SEPARATOR not in column:
        return column, None
    round_name, _, index = column.partition(STATION_SEPARATOR)
    return round_name, int(index) if index.isdigit() else None


def get_spec(taxon: str) -> TaxonSpec:
    """분류군 이름 또는 코드로 사양을 찾는다."""
    if taxon in SPEC_BY_NAME:
        return SPEC_BY_NAME[taxon]
    if taxon in SPEC_BY_CODE:
        return SPEC_BY_CODE[taxon]
    raise KeyError(f"알 수 없는 분류군: {taxon}")
