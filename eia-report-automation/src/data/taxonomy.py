"""분류군 정의와 표준종목록 대조.

분류군 코드는 Excel 시트명, 사진 폴더명, HWPX 플레이스홀더 이름을 잇는
공통 키로 사용한다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Taxon:
    code: str  # 플레이스홀더·폴더명에 쓰는 영문 키
    name: str  # 평가서 본문에 쓰는 국문 명칭


TAXA: tuple[Taxon, ...] = (
    Taxon("plants", "식물상"),
    Taxon("mammals", "포유류"),
    Taxon("birds", "조류"),
    Taxon("herpetofauna", "양서·파충류"),
    Taxon("insects", "육상곤충류"),
    Taxon("fish", "어류"),
    Taxon("benthos", "저서성대형무척추동물"),
)


def get_taxon(code: str) -> Taxon:
    """분류군 코드로 Taxon 을 찾는다."""
    raise NotImplementedError


def normalize_species_name(name: str) -> str:
    """국명 표기 흔들림(공백·중점·이명)을 표준형으로 정규화한다."""
    raise NotImplementedError
