"""분석 실행 → 웹페이지 생성 진입점.

    python -m src.analyze_web

한글 조판 전 단계에서 수치를 검수하기 위한 산출물을 만든다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .analysis.runner import analyze_all
from .report_web.builder import write_report

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MASTER = ROOT / "datamaster" / "EIA_표준종목록_마스터DB_통합본_v7.xlsx"
DEFAULT_SURVEY = ROOT / "datamaster" / "EIA_가상데이터_v7.xlsx"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "output" / "analysis_report.html"


def main() -> None:
    p = argparse.ArgumentParser(description="생태조사 분석 결과 웹페이지 생성")
    p.add_argument("--master", type=Path, default=DEFAULT_MASTER, help="표준종목록 마스터DB")
    p.add_argument("--survey", type=Path, default=DEFAULT_SURVEY, help="조사자료(가상데이터)")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="출력 HTML 경로")
    p.add_argument("--fragment", action="store_true",
                   help="문서 골격 없이 내용만 출력(게시용)")
    args = p.parse_args()

    results = analyze_all(args.master, args.survey)
    out = write_report(results, args.out, str(args.master), str(args.survey),
                       fragment=args.fragment)
    total = sum(r.totals.total for r in results)
    print(f"분류군 {len(results)}개 · 출현종 합계 {total:,}종")
    for r in results:
        t3 = f"{len(r.quantitative)}차수" if r.quantitative else "산출불가"
        print(f"  {r.name:<14} {r.totals.total:>7,}종  T2 {len(r.specific)}항목  T3 {t3}")
    print(f"\n{out}  ({out.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
