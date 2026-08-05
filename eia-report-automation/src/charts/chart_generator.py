"""평가서용 그래프 생성.

파일명 규칙을 고정해 두어야 HWPX 삽입 위치와 그래프 파일을 결정론적으로
연결할 수 있다(기획안 4.3).

    {taxon_code}_{chart_kind}[_{suffix}].png
    예) birds_species_by_round.png
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def chart_filename(taxon_code: str, chart_kind: str, suffix: str | None = None) -> str:
    """그래프 파일명을 규칙에 따라 생성한다."""
    raise NotImplementedError


def species_by_round(df: pd.DataFrame, out_dir: Path, taxon_code: str) -> Path:
    """조사시기(차수)별 종수 그래프를 생성한다."""
    raise NotImplementedError


def species_by_taxon(df: pd.DataFrame, out_dir: Path) -> Path:
    """분류군별 출현종수 그래프를 생성한다."""
    raise NotImplementedError


def diversity_by_site(df: pd.DataFrame, out_dir: Path, taxon_code: str) -> Path:
    """조사지점별 다양도 그래프를 생성한다."""
    raise NotImplementedError
