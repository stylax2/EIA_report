"""분석 실행 → 웹페이지 생성 진입점.

    python -m src.analyze_web

한글 조판 전 단계에서 수치를 검수하기 위한 산출물을 만든다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .analysis.runner import analyze_all
from .hwpx.template import extract_template
from .report_web.builder import write_report

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MASTER = ROOT / "datamaster" / "EIA_표준종목록_마스터DB_통합본_v7.xlsx"
DEFAULT_SURVEY = ROOT / "datamaster" / "EIA_가상데이터_v8.xlsx"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "output" / "analysis_report.html"
DEFAULT_TEMPLATE = (ROOT / "평가서샘플"
                    / "(본안) 09.1.1 동식물상(대전열병합 현대화)_수정1.hwpx")


def main() -> None:
    p = argparse.ArgumentParser(description="생태조사 분석 결과 웹페이지 생성")
    p.add_argument("--master", type=Path, default=DEFAULT_MASTER, help="표준종목록 마스터DB")
    p.add_argument("--survey", type=Path, default=DEFAULT_SURVEY, help="조사자료(가상데이터)")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="출력 HTML 경로")
    p.add_argument("--fragment", action="store_true",
                   help="문서 골격 없이 내용만 출력(게시용)")
    p.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE,
                   help="보고서 미리보기의 기준이 될 기존 평가서 HWPX")
    p.add_argument("--chapter", default=None,
                   help="장 번호 조율 (예: 7.1.1). 생략하면 원본 번호를 유지한다")
    args = p.parse_args()

    results = analyze_all(args.master, args.survey)

    template = None
    if args.template and args.template.exists():
        template = extract_template(args.template)
        if args.chapter:
            template = template.renumber(args.chapter)

    out = write_report(results, args.out, str(args.master), str(args.survey),
                       fragment=args.fragment, template=template)
    total = sum(r.totals.total for r in results)
    scopes = sum(len(r.scopes) for r in results)
    print(f"분류군 {len(results)}개 · 분석 단위 {scopes}개 · 출현종 합계 {total:,}종")
    for r in results:
        st = f"정점 {r.spec.stations}" if r.spec.has_stations else "정점 없음"
        print(f"  {r.name:<14} {r.totals.total:>7,}종  단위 {len(r.scopes):>2}개  {st}")
    if template is not None:
        print(f"\n보고서 템플릿 {template.source}")
        print(f"  장 번호 {template.chapter} · 목차 {len(template.headings)}개 · "
              f"표 {len(template.tables)}개 · 그림·사진 {len(template.figures)}개")
        for n in template.notes:
            print(f"  ! {n}")
    print(f"\n{out}  ({out.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
