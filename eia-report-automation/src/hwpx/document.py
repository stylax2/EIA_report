"""HWP/HWPX 문서 조작 진입점.

기획안 8, 9. pyhwpx 로 기존 평가서를 열고, 플레이스홀더 위치를 찾아
표·문장·이미지를 배치한 뒤 저장한다.

위치 탐색은 결정론적이어야 한다. AI 가 문서를 해석해 삽입 지점을 추측하지
않고, 아래 형식의 식별자를 그대로 찾는다.

    {{BIRD_SPECIES_TABLE}}
    {{BIRD_RESULT_TEXT}}
    {{BIRD_DIVERSITY_GRAPH}}
    {{BIRD_PHOTO_PLATE}}
"""

from __future__ import annotations

from pathlib import Path

PLACEHOLDER_PATTERN = r"\{\{([A-Z0-9_]+)\}\}"


def placeholder(taxon_code: str, slot: str) -> str:
    """분류군과 슬롯 이름으로 플레이스홀더 문자열을 만든다."""
    raise NotImplementedError


class ReportDocument:
    """평가서 파일 하나에 대한 조작 세션."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def open(self) -> None:
        """기존 평가서 파일을 연다."""
        raise NotImplementedError

    def find_placeholders(self) -> list[str]:
        """문서에 남아 있는 플레이스홀더 목록을 반환한다."""
        raise NotImplementedError

    def replace_text(self, marker: str, text: str) -> None:
        """플레이스홀더를 생성된 문장으로 교체한다."""
        raise NotImplementedError

    def save_as(self, out_path: Path) -> None:
        """결과 파일을 저장한다. 원본은 덮어쓰지 않는다."""
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
