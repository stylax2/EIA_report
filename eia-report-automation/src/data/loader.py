"""Excel 조사자료 로더.

`datamaster/` 의 입력용 데이터시트를 분류군별로 읽어 Long Data 형태의
DataFrame 으로 변환한다. 이 계층은 파일 입출력만 담당하며, 값의 정합성
판단은 `validator.py`, 집계는 `analysis/` 가 맡는다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 기획안 3.2 의 주요 필드. 실제 평가서 양식 확정 시 갱신한다.
REQUIRED_COLUMNS = [
    "분류군",
    "과명",
    "국명",
    "학명",
    "조사구분",  # 문헌 / 현지
    "조사차수",
    "조사일자",
    "조사지점",
    "출현여부",
    "개체수",
    "법정보호종여부",
    "비고",
]


def load_survey_workbook(path: Path) -> dict[str, pd.DataFrame]:
    """조사자료 워크북을 읽어 {시트명: DataFrame} 으로 반환한다."""
    raise NotImplementedError


def load_taxon_sheet(path: Path, taxon: str) -> pd.DataFrame:
    """단일 분류군 시트를 Long Data DataFrame 으로 반환한다."""
    raise NotImplementedError


def load_master_species_db(path: Path) -> pd.DataFrame:
    """표준종목록 마스터 DB 를 읽는다. 국명·학명 대조의 기준표로 쓴다."""
    raise NotImplementedError
