"""한글 표 생성과 페이지 조판.

기획안 6.2, 8.2. 종목록 데이터와 페이지 조판 로직을 분리한다. 표 서식은
`config/report_styles.yaml` 에 정의한 스타일 이름으로만 지정하며, LLM 이
선 두께나 셀 여백을 결정하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# config/report_styles.yaml 에 정의한 스타일 키
STYLE_SPECIES_LIST = "TABLE_SPECIES_LIST"
STYLE_SURVEY_RESULT = "TABLE_SURVEY_RESULT"
STYLE_PHOTO_PLATE = "TABLE_PHOTO_PLATE"
STYLE_PROTECTED_SPECIES = "TABLE_PROTECTED_SPECIES"


@dataclass
class TablePage:
    """표 한 페이지분. 머리글은 페이지마다 반복한다."""

    header: list[str]
    rows: list[list[str]]
    page_index: int
    total_pages: int


def split_pages(df: pd.DataFrame, rows_per_page: int) -> list[TablePage]:
    """긴 종목록을 페이지 단위로 나눈다. 조판이 아닌 순수 데이터 분할이다."""
    raise NotImplementedError


def insert_table(marker: str, pages: list[TablePage], style: str) -> None:
    """분할된 표를 지정 위치에 삽입한다. 마지막 페이지는 별도로 처리한다."""
    raise NotImplementedError


def clone_template_table(template_marker: str, target_marker: str) -> None:
    """기존 평가서의 정상 표를 복제한 뒤 내용만 바꾼다(기획안 8.2)."""
    raise NotImplementedError
