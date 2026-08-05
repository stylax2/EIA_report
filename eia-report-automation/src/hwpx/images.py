"""한글 문서 이미지 삽입.

그래프와 사진대지 이미지를 셀 크기에 맞춰 넣는다. 이미지 비율은 유지한다
(기획안 7.2, 8.1).
"""

from __future__ import annotations

from pathlib import Path

from ..photos.photo_plate import PhotoPlate


def insert_image(marker: str, image_path: Path, width_mm: float | None = None) -> None:
    """지정 위치에 이미지를 삽입한다. 너비를 주면 비율을 유지해 맞춘다."""
    raise NotImplementedError


def insert_chart(marker: str, chart_path: Path) -> None:
    """생성된 그래프를 지정 위치에 삽입한다."""
    raise NotImplementedError


def insert_photo_plate(marker: str, plate: PhotoPlate) -> None:
    """사진대지 표를 만들고 각 셀에 사진과 캡션을 넣는다."""
    raise NotImplementedError
