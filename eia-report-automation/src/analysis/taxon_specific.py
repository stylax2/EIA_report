"""T2 분류군 특이 분석항목.

마스터DB의 분류군별 속성 컬럼이 있어야 산출된다. 항목 정의는
`docs/analysis_items.md` 4장에 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..data.schema import FIELD_COLUMNS, MAMMAL_METHODS, is_null_token

# 마스터DB에 국명이 없는 종(어류 2건)은 학명으로 표시한다
MISSING_KOREAN_NAME = "[국명없음]"


def display_name(row: pd.Series) -> str:
    """보고서·화면에 쓸 종 표시명. 국명이 없으면 학명으로 대체한다."""
    name = str(row.get("korean_name", "")).strip()
    if not name or name == MISSING_KOREAN_NAME:
        return str(row.get("scientific_name", "")).strip() or MISSING_KOREAN_NAME
    return name

# 귀화율·도시화지수의 분모. 참조 문헌마다 달라 설정값으로 관리하고
# 산출 결과에 사용한 분모를 함께 표기한다.
NATURALIZED_TOTAL_KR = 375

# 조류 도래유형 코드
MIGRATORY_TYPES = {
    "R": "텃새",
    "S": "여름철새",
    "W": "겨울철새",
    "P": "나그네새",
    "V": "미조",
}


@dataclass
class SpecificItem:
    """T2 항목 하나의 결과."""

    name: str
    value: str  # 대표 수치를 문자열로 표기
    breakdown: list[tuple[str, int]] = field(default_factory=list)
    species: list[str] = field(default_factory=list)
    note: str = ""


def _counts(occurred: pd.DataFrame, column: str) -> pd.Series:
    if column not in occurred.columns:
        return pd.Series(dtype=int)
    s = occurred[column].astype(str).str.strip()
    return s[~s.map(is_null_token)].value_counts()


def _species_with(occurred: pd.DataFrame, column: str) -> list[str]:
    """해당 컬럼에 값이 있는 종의 표시명 목록. 종수 계산의 근거이므로
    자르지 않고 전부 반환한다. 화면 표시 상한은 렌더링 단계에서 건다."""
    if column not in occurred.columns:
        return []
    mask = ~occurred[column].map(is_null_token)
    return [display_name(r) for _, r in occurred.loc[mask].iterrows()]


def analyze_birds(occurred: pd.DataFrame) -> list[SpecificItem]:
    """도래유형 구성."""
    vc = _counts(occurred, "migratory_type")
    if vc.empty:
        return []
    breakdown = [(MIGRATORY_TYPES.get(k, k), int(v)) for k, v in vc.items()]
    breakdown.sort(key=lambda x: -x[1])
    return [SpecificItem(name="도래유형", value=f"{len(breakdown)}개 유형", breakdown=breakdown)]


def analyze_fish(occurred: pd.DataFrame) -> list[SpecificItem]:
    """고유종·외래종. 고유화빈도를 함께 낸다."""
    items: list[SpecificItem] = []
    total = len(occurred)
    endemic = _species_with(occurred, "고유종")
    if endemic:
        ratio = len(endemic) / total * 100 if total else 0
        items.append(SpecificItem(
            name="한국고유종", value=f"{len(endemic)}종",
            species=endemic, note=f"고유화빈도 {ratio:.1f}%"))
    alien = _species_with(occurred, "외래종")
    if alien:
        items.append(SpecificItem(name="외래종", value=f"{len(alien)}종", species=alien))
    return items


def analyze_insects(occurred: pd.DataFrame) -> list[SpecificItem]:
    endemic = _species_with(occurred, "고유종")
    if not endemic:
        return []
    return [SpecificItem(name="한국고유종", value=f"{len(endemic)}종", species=endemic)]


def analyze_benthos(occurred: pd.DataFrame) -> list[SpecificItem]:
    """오수생물지수 Qi 참고값.

    공식 KSI/ESB 는 지표가중치와 출현량 등급이 필요한데 마스터DB에 없다.
    여기서는 개체수 가중 Qi 평균만 참고값으로 낸다.
    """
    if "saprobic_index_Qi" not in occurred.columns:
        return []
    qi = pd.to_numeric(occurred["saprobic_index_Qi"], errors="coerce")
    ind_cols = [f"ind_{c}" for c in FIELD_COLUMNS if f"ind_{c}" in occurred.columns]
    if not ind_cols:
        return []
    counts = occurred[ind_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    mask = qi.notna() & (counts > 0)
    if not mask.any():
        return []
    weighted = float((qi[mask] * counts[mask]).sum() / counts[mask].sum())
    return [SpecificItem(
        name="오수생물지수 Qi (참고값)",
        value=f"{weighted:.2f}",
        breakdown=[("Qi 보유종", int(mask.sum())), ("Qi 미보유종", int(len(occurred) - mask.sum()))],
        note="공식 KSI/ESB 아님. 지표가중치·출현량 등급 확보 후 정식 산출 예정",
    )]


def analyze_plants(occurred: pd.DataFrame) -> list[SpecificItem]:
    """식물구계학적특정종·희귀식물·특산식물·귀화식물·생활형."""
    items: list[SpecificItem] = []
    total = len(occurred)

    floristic = _counts(occurred, "식물구계학적특정종")
    if not floristic.empty:
        order = ["Ⅴ", "Ⅳ", "Ⅲ", "Ⅱ", "Ⅰ"]
        bd = [(f"{g}등급", int(floristic.get(g, 0))) for g in order if g in floristic.index]
        items.append(SpecificItem(
            name="식물구계학적특정종", value=f"{int(floristic.sum())}종", breakdown=bd))

    rare = _counts(occurred, "희귀식물등급")
    if not rare.empty:
        order = ["EW", "CR", "EN", "VU", "NT", "LC", "DD"]
        bd = [(g, int(rare.get(g, 0))) for g in order if g in rare.index]
        bd += [(str(k), int(v)) for k, v in rare.items() if k not in order]
        items.append(SpecificItem(name="희귀식물", value=f"{int(rare.sum())}종", breakdown=bd))

    endemic = _species_with(occurred, "특산식물")
    if endemic:
        items.append(SpecificItem(name="특산식물", value=f"{len(endemic)}종", species=endemic))

    naturalized = _species_with(occurred, "귀화식물")
    if naturalized:
        n = len(naturalized)
        nr = n / total * 100 if total else 0
        ui = n / NATURALIZED_TOTAL_KR * 100
        items.append(SpecificItem(
            name="귀화식물", value=f"{n}종", species=naturalized,
            note=f"귀화율 {nr:.1f}% · 도시화지수 {ui:.1f}% (분모 {NATURALIZED_TOTAL_KR}종)"))

    life_form = _counts(occurred, "raunkiaer_form")
    if not life_form.empty:
        bd = [(str(k), int(v)) for k, v in life_form.head(10).items()]
        items.append(SpecificItem(
            name="생활형(Raunkiaer)", value=f"{len(life_form)}개 유형", breakdown=bd))
    return items


def analyze_mammals(occurred: pd.DataFrame) -> list[SpecificItem]:
    """조사방법별 확인종수. 한 종이 여러 방법으로 확인되면 중복 계수된다."""
    cols = [f"method_{c}" for c in FIELD_COLUMNS if f"method_{c}" in occurred.columns]
    if not cols:
        return []
    tally: dict[str, int] = {}
    for _, r in occurred.iterrows():
        codes = {c for col in cols for c in (r[col] or ())}
        for c in codes:
            tally[c] = tally.get(c, 0) + 1
    if not tally:
        return []
    bd = sorted(((f"{MAMMAL_METHODS.get(k, k)}({k})", v) for k, v in tally.items()),
                key=lambda x: -x[1])
    return [SpecificItem(
        name="현지조사 방법별 확인종수", value=f"{len(tally)}개 방법", breakdown=bd,
        note="한 종이 여러 방법으로 확인되면 각각 계수됨")]


ANALYZERS = {
    "조류": analyze_birds,
    "어류": analyze_fish,
    "육상곤충류": analyze_insects,
    "저서성대형무척추동물": analyze_benthos,
    "관속식물": analyze_plants,
    "포유류": analyze_mammals,
}


def analyze_specific(taxon: str, occurred: pd.DataFrame) -> list[SpecificItem]:
    """분류군에 맞는 T2 분석을 실행한다. 해당 없으면 빈 목록."""
    fn = ANALYZERS.get(taxon)
    return fn(occurred) if fn else []
