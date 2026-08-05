"""표 분할 테스트.

페이지 분할은 조판이 아닌 순수 데이터 연산이므로 한글 없이 검증한다.
구현 전이므로 현재는 모두 skip 된다.
"""

import pandas as pd
import pytest

from src.hwpx import tables


@pytest.fixture
def species_df():
    return pd.DataFrame(
        {
            "과명": [f"과{i}" for i in range(70)],
            "국명": [f"종{i}" for i in range(70)],
            "학명": [f"Genus species{i}" for i in range(70)],
        }
    )


@pytest.mark.skip(reason="구현 예정")
def test_split_pages_count(species_df):
    # 70행을 30행씩 나누면 3페이지
    pages = tables.split_pages(species_df, rows_per_page=30)
    assert len(pages) == 3


@pytest.mark.skip(reason="구현 예정")
def test_split_pages_last_page_partial(species_df):
    # 마지막 페이지는 빈 행으로 채우지 않는다
    pages = tables.split_pages(species_df, rows_per_page=30)
    assert len(pages[-1].rows) == 10


@pytest.mark.skip(reason="구현 예정")
def test_split_pages_header_repeated(species_df):
    # 모든 페이지가 같은 머리글을 갖는다
    pages = tables.split_pages(species_df, rows_per_page=30)
    assert all(page.header == pages[0].header for page in pages)
