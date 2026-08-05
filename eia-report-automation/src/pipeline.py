"""1차 프로토타입 파이프라인(기획안 14).

분류군 하나를 대상으로 아래 흐름을 끝까지 연결한다.

    Excel 종목록
    → 출현종 체크
    → Python 종수 계산
    → 종목록 표 생성
    → 간단한 그래프 생성
    → Local LLM 결과 문장 생성
    → 기존 HWP/HWPX 평가서의 지정 위치에 자동 삽입
    → 결과 파일 저장

이 단일 경로가 안정된 뒤에 사진대지와 다른 분류군으로 확장한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PipelineConfig:
    survey_xlsx: Path
    master_xlsx: Path
    template_hwpx: Path
    output_hwpx: Path
    chart_dir: Path
    taxon_code: str


def run(config: PipelineConfig) -> Path:
    """파이프라인을 실행하고 생성된 평가서 경로를 반환한다."""
    raise NotImplementedError


def main() -> None:
    """CLI 진입점."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
