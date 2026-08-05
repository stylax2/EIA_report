"""사진대지 생성.

기획안 7. 정해진 폴더를 탐색해 사진 수를 세고, 배열을 정한 뒤 표 데이터를
만든다. 실제 한글 문서 삽입은 `hwpx/images.py` 가 맡는다.

    photos/
    ├── plants/
    ├── mammals/
    ├── birds/
    ├── herpetofauna/
    ├── insects/
    └── survey_sites/
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")

# 사진 수에 따라 고를 배열. (행, 열)
LAYOUTS: tuple[tuple[int, int], ...] = ((2, 3), (3, 3), (4, 4))


@dataclass
class PhotoCell:
    path: Path
    caption: str


@dataclass
class PhotoPlate:
    """사진대지 한 장. 페이지를 넘기면 새 PhotoPlate 를 만든다."""

    rows: int
    cols: int
    cells: list[PhotoCell]


def scan_photos(folder: Path) -> list[Path]:
    """폴더에서 이미지 파일을 정렬된 순서로 수집한다."""
    raise NotImplementedError


def caption_from_filename(path: Path) -> str:
    """파일명을 캡션으로 쓴다. 예) 붉은머리오목눈이.jpg -> 붉은머리오목눈이"""
    raise NotImplementedError


def choose_layout(photo_count: int) -> tuple[int, int]:
    """사진 수에 맞는 (행, 열) 배열을 고른다."""
    raise NotImplementedError


def build_plates(folder: Path) -> list[PhotoPlate]:
    """폴더 하나를 사진대지 목록으로 변환한다. 페이지 초과 시 분할한다."""
    raise NotImplementedError
