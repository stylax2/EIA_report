"""Excel 원자료 로딩과 정규화.

마스터DB(종 속성)와 조사자료(출현 기록)를 합쳐 분석 계층이 쓰는
`TaxonDataset` 을 만든다. 조인은 행 위치로 하고 국명·학명으로 검증한다.
근거는 `docs/analysis_workflow.md` 2장에 있다.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .schema import (
    COUNT,
    FIELD_COLUMNS,
    LITERATURE_COLUMNS,
    split_columns,
    survey_columns,
    MAMMAL_METHODS,
    METHOD,
    SURVEY_COLUMNS,
    TAXON_SPECS,
    TaxonSpec,
    get_spec,
    is_null_token,
)


def normalize_text(value: object) -> str:
    """유니코드 수학 이탤릭 학명을 ASCII 로 되돌리고 공백을 정리한다.

    마스터DB·입력지는 '𝐸𝑟𝑖𝑛𝑎𝑐𝑒𝑢𝑠 𝑎𝑚𝑢𝑟𝑒𝑛𝑠𝑖𝑠', 가상데이터는
    'Erinaceus amurensis' 로 같은 학명을 다르게 담고 있다.
    """
    if value is None:
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).split())


@dataclass
class ParsedSurvey:
    """출현 컬럼 하나를 분류군 규칙에 따라 해석한 결과."""

    present: bool
    individuals: int | None = None
    methods: tuple[str, ...] = ()
    unknown_tokens: tuple[str, ...] = ()


def parse_survey_value(value: object, field_value: str, is_literature: bool) -> ParsedSurvey:
    """출현 컬럼 값 하나를 해석한다.

    문헌조사는 분류군과 무관하게 항상 출현 표시(1)이고, 현지조사만
    분류군별 규칙(`field_value`)을 따른다.
    """
    if is_null_token(value):
        return ParsedSurvey(present=False)

    text = normalize_text(value)
    if is_literature or field_value not in (COUNT, METHOD):
        return ParsedSurvey(present=True)

    if field_value == COUNT:
        try:
            return ParsedSurvey(present=True, individuals=int(float(text)))
        except ValueError:
            return ParsedSurvey(present=True, unknown_tokens=(text,))

    # METHOD: "TR/CT" 처럼 "/" 로 결합될 수 있다
    codes = tuple(t.strip() for t in text.split("/") if t.strip())
    known = tuple(c for c in codes if c in MAMMAL_METHODS)
    unknown = tuple(c for c in codes if c not in MAMMAL_METHODS)
    return ParsedSurvey(present=True, methods=known, unknown_tokens=unknown)


@dataclass
class TaxonDataset:
    """분류군 하나의 마스터 속성 + 해석된 출현 기록."""

    spec: TaxonSpec
    frame: pd.DataFrame  # 마스터 컬럼 + present_*/ind_*/method_* 파생 컬럼
    warnings: list[str] = field(default_factory=list)

    @property
    def occurred(self) -> pd.DataFrame:
        """문헌·현지 어디에든 기록된 출현종만 남긴다."""
        return self.frame[self.frame["present_any"]].copy()


def _presence_columns(df: pd.DataFrame, spec: TaxonSpec) -> tuple[pd.DataFrame, list[str]]:
    """출현 컬럼을 해석해 파생 컬럼을 붙인다."""
    warnings: list[str] = []
    unknown: set[str] = set()

    columns = survey_columns(spec)
    for col in columns:
        is_lit = col in LITERATURE_COLUMNS
        parsed = [parse_survey_value(v, spec.field_value, is_lit) for v in df[col]]
        df[f"present_{col}"] = [p.present for p in parsed]
        if spec.field_value == COUNT and not is_lit:
            df[f"ind_{col}"] = [p.individuals for p in parsed]
        if spec.field_value == METHOD and not is_lit:
            df[f"method_{col}"] = [p.methods for p in parsed]
        for p in parsed:
            unknown.update(p.unknown_tokens)

    lit_cols, fld_cols = split_columns(columns)
    df["present_any"] = df[[f"present_{c}" for c in columns]].any(axis=1)
    df["present_lit"] = df[[f"present_{c}" for c in lit_cols]].any(axis=1)
    df["present_field"] = df[[f"present_{c}" for c in fld_cols]].any(axis=1)

    if unknown:
        warnings.append(f"해석하지 못한 출현값: {', '.join(sorted(unknown))}")

    if spec.field_value == COUNT:
        ind_cols = [f"ind_{c}" for c in fld_cols]
        counts = df[ind_cols].apply(pd.to_numeric, errors="coerce")
        nonpositive = int((counts <= 0).sum().sum())
        if nonpositive:
            warnings.append(f"0 이하 개체수 {nonpositive}건")
    return df, warnings


def _join_by_id(df: pd.DataFrame, survey: pd.DataFrame, taxon: str,
                columns: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """species_id 로 조인한다(v7 이후). 행 순서·행 수와 무관하다."""
    warnings: list[str] = []
    ids = df["species_id"].map(normalize_text)
    survey_ids = survey["species_id"].map(normalize_text)

    dup = survey_ids[survey_ids.duplicated()].tolist()
    if dup:
        raise ValueError(
            f"[{taxon}] 조사자료에 species_id 가 중복됩니다: {dup[:5]}. "
            "한 종은 한 행이어야 합니다."
        )

    unknown = sorted(set(survey_ids) - set(ids))
    if unknown:
        raise ValueError(
            f"[{taxon}] 마스터DB에 없는 species_id {len(unknown)}건: {unknown[:5]}. "
            "종을 추가하려면 마스터DB에 먼저 등록하십시오."
        )

    lookup = survey.set_index(survey_ids)
    missing = int((~ids.isin(set(survey_ids))).sum())
    if missing:
        warnings.append(f"조사자료에 기록이 없는 종 {missing}건 — 미출현으로 처리")

    for col in columns:
        df[col] = ids.map(lookup[col]) if col in lookup.columns else None
    return df, warnings


def _join_by_position(df: pd.DataFrame, survey: pd.DataFrame, taxon: str,
                      columns: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """행 위치로 조인한다(v6 이하). 국명·학명으로 어긋남을 잡는다."""
    warnings = ["조사자료에 species_id 가 없어 행 위치로 조인했습니다. v7 이상을 쓰십시오."]
    if len(df) != len(survey):
        raise ValueError(
            f"[{taxon}] 행 수가 다릅니다. 마스터DB {len(df)}행, 조사자료 {len(survey)}행. "
            "조사자료의 행을 삽입·삭제·정렬하면 위치 조인이 깨집니다."
        )
    for key in ("korean_name", "scientific_name"):
        left = df[key]
        right = survey[key].map(normalize_text)
        mismatch = left.values != right.values
        if mismatch.any():
            first = int(mismatch.argmax())
            raise ValueError(
                f"[{taxon}] {key} 가 {first + 2}행에서 어긋납니다: "
                f"마스터DB '{left.iloc[first]}' vs 조사자료 '{right.iloc[first]}'. "
                "조사자료의 행 순서를 바꾸지 마십시오."
            )
    for col in columns:
        df[col] = survey[col].values
    return df, warnings


def load_taxon(
    master_path: Path | str,
    survey_path: Path | str,
    taxon: str,
) -> TaxonDataset:
    """마스터DB와 조사자료에서 분류군 하나를 읽어 합친다.

    조사자료에 `species_id` 가 있으면 그것으로 조인하고, 없으면(v6 이하)
    행 위치로 조인한 뒤 경고를 남긴다.
    """
    spec = get_spec(taxon)
    master = pd.read_excel(master_path, sheet_name=spec.name)
    survey = pd.read_excel(survey_path, sheet_name=spec.name)

    df = master.copy()
    for key in ("scientific_name", "korean_name", "family_kr"):
        df[key] = df[key].map(normalize_text)

    if "species_id" in master.columns and "species_id" in survey.columns:
        df, warnings = _join_by_id(df, survey, spec.name, survey_columns(spec))
    else:
        df, warnings = _join_by_position(df, survey, spec.name, survey_columns(spec))

    df, parse_warnings = _presence_columns(df, spec)
    warnings += parse_warnings

    dup = df.duplicated(subset=["scientific_name", "korean_name"]).sum()
    if dup:
        warnings.append(f"마스터DB에 학명·국명이 같은 중복 행 {dup}건")

    for col, label in (("family_kr", "과명"), ("korean_name", "국명")):
        missing = int(df[col].map(is_null_token).sum() +
                      (df[col].astype(str).str.strip() == "[국명없음]").sum())
        if missing:
            warnings.append(f"마스터DB에 {label}이 비어 있는 종 {missing}건")

    return TaxonDataset(spec=spec, frame=df, warnings=warnings)


def load_all(master_path: Path | str, survey_path: Path | str) -> dict[str, TaxonDataset]:
    """8개 분류군을 모두 읽는다."""
    return {s.name: load_taxon(master_path, survey_path, s.name) for s in TAXON_SPECS}
