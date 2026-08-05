"""종목록·종수 집계.

기획안 4.1 의 기본 처리를 담당한다. 여기서 확정한 수치가 보고서의 사실
기준이 되며, LLM 은 이 결과를 바꾸지 못한다.
"""

from __future__ import annotations

import pandas as pd


def extract_occurred(df: pd.DataFrame) -> pd.DataFrame:
    """출현 여부가 체크된 행만 추출한다."""
    raise NotImplementedError


def build_species_list(df: pd.DataFrame) -> pd.DataFrame:
    """분류군별 종목록(과명·국명·학명 정렬)을 생성한다."""
    raise NotImplementedError


def count_species(df: pd.DataFrame) -> int:
    """중복을 제거한 전체 출현종수를 센다."""
    raise NotImplementedError


def count_by_round(df: pd.DataFrame) -> pd.DataFrame:
    """조사차수별 출현종수를 집계한다."""
    raise NotImplementedError


def count_by_site(df: pd.DataFrame) -> pd.DataFrame:
    """조사지점별 출현종수·개체수를 집계한다."""
    raise NotImplementedError


def compare_literature_field(df: pd.DataFrame) -> pd.DataFrame:
    """문헌조사와 현지조사 결과를 대조한다."""
    raise NotImplementedError


def extract_protected_species(df: pd.DataFrame) -> pd.DataFrame:
    """법정보호종을 추출한다. 최종 판정은 사람이 확인한다."""
    raise NotImplementedError
