"""분석 결과 웹페이지 생성.

`TaxonResult` 를 정적 HTML 한 장으로 렌더링한다. 외부 자원을 참조하지
않으므로 브라우저만 있으면 열린다.

이 페이지는 읽는 문서가 아니라 조판 전에 수치를 검수하는 도구다. 따라서
산출 가능성 매트릭스를 최상단에 두어 "이 분류군이 무엇을 낼 수 있는가"가
먼저 보이게 한다. 화면의 모든 수치는 `TaxonResult` 에서 오며 렌더링
단계에서 다시 계산하지 않는다.
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from ..analysis.runner import TaxonResult
from ..data.schema import FIELD_COLUMNS, LITERATURE_COLUMNS

SURVEY_COLS = LITERATURE_COLUMNS + FIELD_COLUMNS
SPECIES_PAGE = 100  # 종목록 1회 렌더링 행 수


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def _taxon_payload(r: TaxonResult) -> dict:
    """종목록 데이터를 압축된 배열로 만든다. 행이 많아 키를 반복하지 않는다."""
    rows = [
        [
            row.family,
            row.scientific_name,
            row.korean_name,
            row.abb,
            row.abb2,
            "".join("1" if row.marks.get(c) else "0" for c in SURVEY_COLS),
            row.individuals if row.individuals is not None else "",
        ]
        for row in r.species_rows
    ]
    return {"code": r.spec.code, "rows": rows}


def _cards(r: TaxonResult) -> str:
    t = r.totals
    legal = r.legal
    cards = [
        ("총 출현종수", f"{t.total:,}", f"목록 {r.total_species_in_db:,}종 중", "accent"),
        ("문헌조사", f"{t.literature:,}", f"단독 {t.literature_only:,}종", ""),
        ("현지조사", f"{t.field_survey:,}", f"단독 {t.field_only:,}종", ""),
        ("멸종위기야생생물", f"{legal.endangered_total:,}",
         f"Ⅰ급 {len(legal.endangered_1)} · Ⅱ급 {len(legal.endangered_2)}",
         "critical" if legal.endangered_total else ""),
        ("천연기념물", f"{len(legal.natural_monument):,}", "", ""),
        ("생태계교란생물", f"{len(legal.invasive):,}", "",
         "warn" if legal.invasive else ""),
    ]
    out = []
    for label, value, sub, tone in cards:
        out.append(
            f'<div class="card {tone}"><div class="card-label">{_esc(label)}</div>'
            f'<div class="card-value">{_esc(value)}</div>'
            f'<div class="card-sub">{_esc(sub)}</div></div>'
        )
    return f'<div class="cards">{"".join(out)}</div>'


def _survey_table(r: TaxonResult) -> str:
    t = r.totals
    rows = "".join(
        f"<tr><th>{_esc(c)}</th><td class='num'>{t.by_column[c]:,}</td></tr>"
        for c in SURVEY_COLS
    )
    return f"""
<div class="grid-2">
  <section class="panel">
    <h3>조사 회차별 출현종수</h3>
    <table class="kv"><tbody>{rows}</tbody></table>
  </section>
  <section class="panel">
    <h3>조사구분 대조</h3>
    <table class="kv"><tbody>
      <tr><th>문헌·현지 공통</th><td class="num">{t.both:,}</td></tr>
      <tr><th>문헌 단독</th><td class="num">{t.literature_only:,}</td></tr>
      <tr><th>현지 단독 <span class="hint">문헌 미기재</span></th><td class="num">{t.field_only:,}</td></tr>
      <tr><th>현지 2차 신규 <span class="hint">1차 미확인</span></th><td class="num">{t.new_in_field_round2:,}</td></tr>
    </tbody></table>
  </section>
</div>"""


def _bars(title: str, items: list[tuple[str, int]], note: str = "") -> str:
    if not items:
        return ""
    top = max(v for _, v in items) or 1
    rows = "".join(
        f'<div class="bar-row"><span class="bar-name">{_esc(k)}</span>'
        f'<span class="bar-track"><span class="bar-fill" style="width:{v / top * 100:.1f}%"></span></span>'
        f'<span class="bar-val">{v:,}</span></div>'
        for k, v in items
    )
    hint = f'<p class="hint">{_esc(note)}</p>' if note else ""
    return f'<section class="panel"><h3>{_esc(title)}</h3>{hint}<div class="bars">{rows}</div></section>'


def _legal_lists(r: TaxonResult) -> str:
    groups = [
        ("멸종위기야생생물 Ⅰ급", r.legal.endangered_1, "critical"),
        ("멸종위기야생생물 Ⅱ급", r.legal.endangered_2, "critical"),
        ("천연기념물", r.legal.natural_monument, ""),
        ("생태계교란생물", r.legal.invasive, "warn"),
    ]
    blocks = []
    for title, items, tone in groups:
        if not items:
            blocks.append(
                f'<div class="legal-group"><h4>{_esc(title)}</h4>'
                f'<p class="empty">출현하지 않음</p></div>')
            continue
        chips = "".join(
            f'<span class="chip {tone}">{_esc(s.korean_name)}'
            f'<i>{_esc(s.scientific_name)}</i></span>' for s in items)
        blocks.append(
            f'<div class="legal-group"><h4>{_esc(title)} '
            f'<span class="count">{len(items)}종</span></h4>'
            f'<div class="chips">{chips}</div></div>')
    local = r.legal.local_protected
    if local:
        blocks.append(
            f'<div class="legal-group"><h4>시·도보호종 '
            f'<span class="count">{len(local)}종</span></h4>'
            f'<p class="hint">사업 대상지의 시·도에 해당하는 종만 골라 사용한다.</p>'
            f'<div class="chips">'
            + "".join(f'<span class="chip">{_esc(s.korean_name)}</span>' for s in local[:60])
            + ("<span class='chip more'>…</span>" if len(local) > 60 else "")
            + "</div></div>")
    return f'<section class="panel"><h3>법정보호종 <span class="tier">T1-05·06·07</span></h3>{"".join(blocks)}</section>'


def _specific(r: TaxonResult) -> str:
    if not r.specific:
        return ""
    blocks = []
    for item in r.specific:
        bd = ""
        if item.breakdown:
            bd = '<div class="mini-bars">' + "".join(
                f'<div class="mini-row"><span>{_esc(k)}</span>'
                f'<span class="num">{v:,}</span></div>' for k, v in item.breakdown
            ) + "</div>"
        sp = ""
        if item.species:
            shown = item.species[:40]
            sp = ('<div class="chips">'
                  + "".join(f'<span class="chip">{_esc(s)}</span>' for s in shown)
                  + (f'<span class="chip more">외 {len(item.species) - 40}종</span>'
                     if len(item.species) > 40 else "")
                  + "</div>")
        note = f'<p class="note">{_esc(item.note)}</p>' if item.note else ""
        blocks.append(
            f'<div class="spec-item"><div class="spec-head">'
            f'<h4>{_esc(item.name)}</h4><span class="spec-value">{_esc(item.value)}</span>'
            f'</div>{note}{bd}{sp}</div>')
    return (f'<section class="panel"><h3>분류군 특이 분석 <span class="tier">T2</span></h3>'
            f'{"".join(blocks)}</section>')


def _quantitative(r: TaxonResult) -> str:
    if not r.quantitative:
        reason = r.quantitative_unavailable or "산출할 수 없습니다."
        return (f'<section class="panel unavailable"><h3>군집 분석 <span class="tier">T3</span></h3>'
                f'<div class="na"><strong>자료 없음</strong><p>{_esc(reason)}</p>'
                f'<p class="hint">개체수가 없으면 우점도·다양도·균등도·풍부도를 낼 수 없다. '
                f'0으로 채우지 않고 산출 불가로 표기한다.</p></div></section>')
    head = "".join(f"<th>{_esc(q.label)}</th>" for q in r.quantitative)
    def row(label, fmt, hint=""):
        cells = "".join(f'<td class="num">{fmt(q)}</td>' for q in r.quantitative)
        h = f' <span class="hint">{hint}</span>' if hint else ""
        return f"<tr><th>{label}{h}</th>{cells}</tr>"
    body = "".join([
        row("종수 S", lambda q: f"{q.species_count:,}"),
        row("개체수 N", lambda q: f"{q.individuals:,}"),
        row("우점도 DI", lambda q: f"{q.dominance:.3f}"),
        row("다양도 H&#39;", lambda q: f"{q.diversity:.3f}"),
        row("균등도 J&#39;", lambda q: f"{q.evenness:.3f}"),
        row("풍부도 R1", lambda q: f"{q.richness:.3f}"),
        row("우점종", lambda q: _esc(q.dominant_species)),
        row("아우점종", lambda q: _esc(q.subdominant_species)),
    ])
    tops = []
    for q in r.quantitative:
        items = "".join(
            f'<div class="mini-row"><span>{i}. {_esc(n)}</span>'
            f'<span class="num">{c:,} <em>{ra:.1f}%</em></span></div>'
            for i, (n, c, ra) in enumerate(q.dominant, 1))
        tops.append(f'<div class="top-block"><h4>{_esc(q.label)} 우점 상위</h4>'
                    f'<div class="mini-bars">{items}</div></div>')
    return f"""
<section class="panel">
  <h3>군집 분석 <span class="tier">T3</span></h3>
  <p class="hint">지수는 조사차수별로 각각 산출한다. 차수를 합산하면 조사 시기가 다른 자료를 섞게 된다.</p>
  <div class="scroll-x"><table class="matrix"><thead><tr><th></th>{head}</tr></thead>
  <tbody>{body}</tbody></table></div>
  <div class="grid-2">{"".join(tops)}</div>
</section>"""


def _species_section(r: TaxonResult) -> str:
    cols = "".join(f"<th>{_esc(c)}</th>" for c in SURVEY_COLS)
    ind = "<th>개체수</th>" if r.spec.has_individuals else ""
    return f"""
<section class="panel">
  <h3>종목록 <span class="tier">T1-08</span></h3>
  <div class="tools">
    <input type="search" class="search" data-taxon="{r.spec.code}"
           placeholder="국명 · 학명 · 과명 검색" aria-label="종 검색">
    <span class="result-count" data-count="{r.spec.code}"></span>
  </div>
  <div class="scroll-x">
    <table class="species" data-table="{r.spec.code}">
      <thead><tr><th>과명</th><th>학명</th><th>국명</th><th>법정지위</th>{cols}{ind}</tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <button class="more" data-more="{r.spec.code}" hidden>더 보기</button>
</section>"""


def _notes(r: TaxonResult) -> str:
    if not r.notes:
        return ""
    items = "".join(f"<li>{_esc(n)}</li>" for n in r.notes)
    return (f'<section class="panel warn-panel"><h3>자료 확인 사항</h3>'
            f'<ul class="notes">{items}</ul></section>')


def _matrix(results: list[TaxonResult]) -> str:
    rows = []
    for r in results:
        t3 = ('<span class="ok">산출</span>' if r.quantitative
              else f'<span class="no" title="{_esc(r.quantitative_unavailable or "")}">불가</span>')
        t2 = (", ".join(i.name for i in r.specific)) or "—"
        field_kind = {"count": "개체수", "method": "조사방법 코드", "presence": "출현 여부"}[
            r.spec.field_value]
        rows.append(
            f'<tr><th><a href="#{r.spec.code}">{_esc(r.name)}</a></th>'
            f'<td class="num">{r.totals.total:,}</td>'
            f'<td>{_esc(field_kind)}</td>'
            f'<td><span class="ok">산출</span></td>'
            f'<td class="t2">{_esc(t2)}</td>'
            f'<td>{t3}</td></tr>')
    return f"""
<section class="panel" id="overview">
  <h3>산출 가능성 매트릭스</h3>
  <p class="hint">분석항목은 업체 양식이 아니라 원자료가 지지하는 범위로 정한다.
     개체수를 기록한 분류군에서만 T3 군집지수를 낼 수 있다.</p>
  <div class="scroll-x">
    <table class="matrix">
      <thead><tr><th>분류군</th><th>출현종수</th><th>현지조사 기록 방식</th>
        <th>T1 공통</th><th>T2 분류군 특이</th><th>T3 군집지수</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
</section>"""


CSS = """
:root{
  --ink:#16211d; --ink-2:#3d4b45; --ink-3:#6b7a72;
  --paper:#f4f6f3; --surface:#ffffff; --surface-2:#eceff0;
  --line:#d6ddd7; --line-2:#e6ebe6;
  --moss:#2f6b4f; --moss-soft:#e3efe7;
  --critical:#a3341f; --critical-soft:#f7e6e1;
  --warn:#8a6112; --warn-soft:#f6eedc;
  --muted:#8a938c;
}
@media (prefers-color-scheme: dark){
  :root{
    --ink:#e6ece8; --ink-2:#b3bfb8; --ink-3:#8a968f;
    --paper:#101614; --surface:#18211e; --surface-2:#1f2a26;
    --line:#2c3a34; --line-2:#243029;
    --moss:#6fbf95; --moss-soft:#1d3129;
    --critical:#e0836c; --critical-soft:#33211c;
    --warn:#d6ac5c; --warn-soft:#2e2718;
    --muted:#7d8a83;
  }
}
:root[data-theme="dark"]{
  --ink:#e6ece8; --ink-2:#b3bfb8; --ink-3:#8a968f;
  --paper:#101614; --surface:#18211e; --surface-2:#1f2a26;
  --line:#2c3a34; --line-2:#243029;
  --moss:#6fbf95; --moss-soft:#1d3129;
  --critical:#e0836c; --critical-soft:#33211c;
  --warn:#d6ac5c; --warn-soft:#2e2718;
  --muted:#7d8a83;
}
:root[data-theme="light"]{
  --ink:#16211d; --ink-2:#3d4b45; --ink-3:#6b7a72;
  --paper:#f4f6f3; --surface:#ffffff; --surface-2:#eceff0;
  --line:#d6ddd7; --line-2:#e6ebe6;
  --moss:#2f6b4f; --moss-soft:#e3efe7;
  --critical:#a3341f; --critical-soft:#f7e6e1;
  --warn:#8a6112; --warn-soft:#f6eedc;
  --muted:#8a938c;
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",
              system-ui,-apple-system,sans-serif;
  font-size:15px; line-height:1.6;
  -webkit-font-smoothing:antialiased;
}
.mono,.num,td.num,.card-value,.bar-val{
  font-family:"SFMono-Regular",Menlo,Consolas,"D2Coding",monospace;
  font-variant-numeric:tabular-nums;
}
i,em.sci,.chip i{font-style:italic}

/* ── 헤더 ── */
header.top{
  border-bottom:1px solid var(--line); background:var(--surface);
  padding:26px clamp(16px,4vw,40px);
}
.top-inner{max-width:1180px;margin:0 auto;display:flex;flex-wrap:wrap;
  gap:18px;align-items:flex-end;justify-content:space-between}
h1{font-size:1.5rem;margin:0 0 6px;letter-spacing:-.01em;text-wrap:balance}
.eyebrow{font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--moss);font-weight:600;margin:0 0 8px}
.meta{font-size:.8rem;color:var(--ink-3);margin:0;line-height:1.8}
.meta code{background:var(--surface-2);padding:1px 6px;border-radius:3px;
  font-size:.95em;color:var(--ink-2)}
.banner{
  background:var(--warn-soft);border:1px solid var(--warn);
  color:var(--warn);border-radius:4px;padding:9px 14px;
  font-size:.8rem;font-weight:600;
}

/* ── 레이아웃 ── */
.shell{max-width:1180px;margin:0 auto;display:grid;
  grid-template-columns:210px minmax(0,1fr);gap:30px;
  padding:30px clamp(16px,4vw,40px) 80px}
@media (max-width:860px){.shell{grid-template-columns:1fr;gap:18px}}

nav.rail{position:sticky;top:20px;align-self:start}
@media (max-width:860px){nav.rail{position:static}}
.rail-title{font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;
  color:var(--ink-3);font-weight:700;margin:0 0 10px;padding-left:10px}
.rail ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:1px}
@media (max-width:860px){.rail ul{flex-direction:row;flex-wrap:wrap;gap:6px}}
.rail button{
  width:100%;display:flex;justify-content:space-between;align-items:center;gap:8px;
  background:none;border:0;border-left:2px solid transparent;
  padding:8px 10px;font:inherit;font-size:.86rem;color:var(--ink-2);
  cursor:pointer;text-align:left;border-radius:0 3px 3px 0;
}
.rail button:hover{background:var(--surface);color:var(--ink)}
.rail button[aria-current="true"]{
  background:var(--moss-soft);border-left-color:var(--moss);
  color:var(--moss);font-weight:700}
.rail .badge{font-size:.74rem;color:var(--ink-3);
  font-family:"SFMono-Regular",Menlo,monospace;font-variant-numeric:tabular-nums}
.rail button[aria-current="true"] .badge{color:var(--moss)}
.rail button:focus-visible{outline:2px solid var(--moss);outline-offset:-2px}

main{min-width:0;display:flex;flex-direction:column;gap:22px}
.taxon-panel[hidden]{display:none}
.taxon-panel{display:flex;flex-direction:column;gap:18px}
.taxon-head h2{font-size:1.24rem;margin:0 0 4px;letter-spacing:-.01em}
.taxon-head p{margin:0;font-size:.82rem;color:var(--ink-3)}

/* ── 패널 ── */
.panel{background:var(--surface);border:1px solid var(--line);
  border-radius:5px;padding:20px 22px}
.panel h3{font-size:.94rem;margin:0 0 14px;display:flex;align-items:center;
  gap:9px;letter-spacing:-.005em}
.panel h4{font-size:.84rem;margin:0 0 8px;color:var(--ink-2)}
.tier{font-size:.64rem;letter-spacing:.09em;font-weight:700;
  background:var(--surface-2);color:var(--ink-3);
  padding:2px 7px;border-radius:3px;font-family:Menlo,monospace}
.hint{font-size:.78rem;color:var(--ink-3);margin:0 0 12px;line-height:1.65}
.note{font-size:.78rem;color:var(--moss);margin:0 0 10px}
.grid-2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}

/* ── 카드 ── */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:10px}
.card{background:var(--surface);border:1px solid var(--line);
  border-radius:5px;padding:14px 16px;border-top:2px solid var(--line)}
.card.accent{border-top-color:var(--moss)}
.card.critical{border-top-color:var(--critical)}
.card.warn{border-top-color:var(--warn)}
.card-label{font-size:.72rem;color:var(--ink-3);font-weight:600;
  letter-spacing:.02em;margin-bottom:5px}
.card-value{font-size:1.6rem;font-weight:700;line-height:1.15;letter-spacing:-.02em}
.card.critical .card-value{color:var(--critical)}
.card.warn .card-value{color:var(--warn)}
.card-sub{font-size:.72rem;color:var(--ink-3);margin-top:3px;min-height:1em}

/* ── 표 ── */
table{border-collapse:collapse;width:100%;font-size:.84rem}
.scroll-x{overflow-x:auto}
.kv th{text-align:left;font-weight:500;color:var(--ink-2);
  padding:7px 0;border-bottom:1px solid var(--line-2)}
.kv td{text-align:right;padding:7px 0;border-bottom:1px solid var(--line-2);font-weight:600}
.kv tr:last-child th,.kv tr:last-child td{border-bottom:0}
.matrix th,.matrix td{padding:8px 12px;border-bottom:1px solid var(--line-2);
  text-align:left;vertical-align:middle}
.matrix thead th{font-size:.74rem;color:var(--ink-3);font-weight:700;
  border-bottom:1px solid var(--line);white-space:nowrap}
.matrix tbody th{font-weight:600;white-space:nowrap}
.matrix td.num,.matrix .num{text-align:right;font-weight:600}
.matrix td.t2{font-size:.78rem;color:var(--ink-2);min-width:200px}
.matrix a{color:var(--moss);text-decoration:none;font-weight:700}
.matrix a:hover{text-decoration:underline}
.ok{color:var(--moss);font-weight:700;font-size:.78rem}
.no{color:var(--muted);font-weight:700;font-size:.78rem;cursor:help;
  border-bottom:1px dotted var(--muted)}
.species th,.species td{padding:6px 10px;border-bottom:1px solid var(--line-2);
  text-align:left;white-space:nowrap}
.species thead th{font-size:.74rem;color:var(--ink-3);position:sticky;top:0;
  background:var(--surface);border-bottom:1px solid var(--line)}
.species .sci{font-style:italic;color:var(--ink-2)}
.species .mark{text-align:center;color:var(--moss);font-weight:700}
.species .dash{text-align:center;color:var(--line)}
.species td.num{text-align:right}
.species .abb{font-size:.74rem;font-weight:700;color:var(--critical)}

/* ── 막대 ── */
.bars{display:flex;flex-direction:column;gap:5px}
.bar-row{display:grid;grid-template-columns:132px minmax(0,1fr) 52px;
  gap:10px;align-items:center;font-size:.8rem}
.bar-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink-2)}
.bar-track{background:var(--surface-2);border-radius:2px;height:11px;overflow:hidden}
.bar-fill{display:block;height:100%;background:var(--moss);border-radius:2px}
.bar-val{text-align:right;font-size:.78rem;font-weight:600;color:var(--ink-2)}

.mini-bars{display:flex;flex-direction:column;gap:1px;margin-top:8px}
.mini-row{display:flex;justify-content:space-between;gap:12px;
  padding:5px 0;border-bottom:1px solid var(--line-2);font-size:.81rem}
.mini-row:last-child{border-bottom:0}
.mini-row .num{font-weight:600}
.mini-row em{font-style:normal;color:var(--ink-3);font-size:.9em;margin-left:4px}

/* ── 칩 ── */
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{display:inline-flex;align-items:baseline;gap:5px;
  background:var(--surface-2);border-radius:3px;padding:3px 8px;font-size:.78rem}
.chip i{font-size:.9em;color:var(--ink-3)}
.chip.critical{background:var(--critical-soft);color:var(--critical);font-weight:600}
.chip.critical i{color:var(--critical);opacity:.75}
.chip.warn{background:var(--warn-soft);color:var(--warn);font-weight:600}
.chip.warn i{color:var(--warn);opacity:.75}
.chip.more{background:none;color:var(--ink-3);border:1px dashed var(--line)}
.legal-group{padding:12px 0;border-bottom:1px solid var(--line-2)}
.legal-group:last-child{border-bottom:0;padding-bottom:0}
.legal-group:first-child{padding-top:0}
.count{font-size:.74rem;color:var(--moss);font-weight:700}
.empty{font-size:.79rem;color:var(--ink-3);margin:0}

/* ── 산출 불가 ── */
.unavailable{border-style:dashed}
.na{background:var(--surface-2);border-radius:4px;padding:16px 18px}
.na strong{display:block;color:var(--muted);font-size:.88rem;margin-bottom:5px}
.na p{margin:0 0 6px;font-size:.81rem;color:var(--ink-2)}
.na .hint{margin:0}

.spec-item{padding:14px 0;border-bottom:1px solid var(--line-2)}
.spec-item:last-child{border-bottom:0;padding-bottom:0}
.spec-item:first-child{padding-top:0}
.spec-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.spec-head h4{margin:0}
.spec-value{font-weight:700;color:var(--moss);
  font-family:Menlo,monospace;font-variant-numeric:tabular-nums;font-size:.9rem}

.warn-panel{border-color:var(--warn)}
.notes{margin:0;padding-left:18px;font-size:.82rem;color:var(--ink-2)}
.notes li{margin-bottom:4px}

/* ── 도구 ── */
.tools{display:flex;gap:12px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.search{flex:1;min-width:200px;padding:7px 11px;border:1px solid var(--line);
  border-radius:4px;background:var(--paper);color:var(--ink);font:inherit;font-size:.84rem}
.search:focus{outline:2px solid var(--moss);outline-offset:-1px;border-color:var(--moss)}
.result-count{font-size:.78rem;color:var(--ink-3);
  font-family:Menlo,monospace;font-variant-numeric:tabular-nums}
.more{margin-top:12px;padding:7px 16px;border:1px solid var(--line);
  border-radius:4px;background:var(--surface);color:var(--ink-2);
  font:inherit;font-size:.82rem;cursor:pointer}
.more:hover{border-color:var(--moss);color:var(--moss)}
.more:focus-visible{outline:2px solid var(--moss);outline-offset:2px}

footer{border-top:1px solid var(--line);padding:22px clamp(16px,4vw,40px);
  font-size:.78rem;color:var(--ink-3)}
footer .inner{max-width:1180px;margin:0 auto}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""


JS = """
(function(){
  var DATA = window.__TAXA__, PAGE = %(page)d, COLS = %(ncols)d;
  var state = {};

  function esc(s){var d=document.createElement('span');d.textContent=s;return d.innerHTML;}

  function rowHtml(r, hasInd){
    var marks='';
    for(var i=0;i<COLS;i++){
      marks += r[5][i]==='1' ? '<td class="mark">●</td>' : '<td class="dash">·</td>';
    }
    return '<tr><td>'+esc(r[0])+'</td>'
      +'<td class="sci">'+esc(r[1])+'</td>'
      +'<td>'+esc(r[2])+'</td>'
      +'<td class="abb">'+esc(r[3]||'')+'</td>'
      + marks
      + (hasInd ? '<td class="num">'+(r[6]===''?'':Number(r[6]).toLocaleString())+'</td>' : '')
      +'</tr>';
  }

  function render(code){
    var st=state[code], tbody=document.querySelector('[data-table="'+code+'"] tbody');
    var slice=st.filtered.slice(0, st.shown);
    var html='';
    for(var i=0;i<slice.length;i++){ html+=rowHtml(slice[i], st.hasInd); }
    tbody.innerHTML=html;
    document.querySelector('[data-count="'+code+'"]').textContent =
      st.filtered.length.toLocaleString()+'종 중 '+slice.length.toLocaleString()+'종 표시';
    var btn=document.querySelector('[data-more="'+code+'"]');
    btn.hidden = st.shown >= st.filtered.length;
  }

  function initTaxon(code){
    var d=DATA[code];
    state[code]={rows:d.rows, filtered:d.rows, shown:Math.min(PAGE,d.rows.length),
                 hasInd:d.hasInd};
    render(code);
    var input=document.querySelector('[data-taxon="'+code+'"]');
    var timer;
    input.addEventListener('input', function(){
      clearTimeout(timer);
      timer=setTimeout(function(){
        var q=input.value.trim().toLowerCase(), st=state[code];
        st.filtered = q ? st.rows.filter(function(r){
          return (r[0]+' '+r[1]+' '+r[2]).toLowerCase().indexOf(q)>=0;
        }) : st.rows;
        st.shown=Math.min(PAGE, st.filtered.length);
        render(code);
      },140);
    });
    document.querySelector('[data-more="'+code+'"]').addEventListener('click',function(){
      state[code].shown=Math.min(state[code].shown+PAGE*5, state[code].filtered.length);
      render(code);
    });
  }

  function show(code){
    document.querySelectorAll('.taxon-panel').forEach(function(p){
      p.hidden = (p.id !== code);
    });
    document.querySelectorAll('.rail button').forEach(function(b){
      b.setAttribute('aria-current', String(b.dataset.go===code));
    });
    if(!state[code] && DATA[code]) initTaxon(code);
    if(history.replaceState) history.replaceState(null,'','#'+code);
  }

  document.querySelectorAll('.rail button').forEach(function(b){
    b.addEventListener('click',function(){show(b.dataset.go);});
  });
  document.querySelectorAll('.matrix a[href^="#"]').forEach(function(a){
    a.addEventListener('click',function(e){e.preventDefault();
      show(a.getAttribute('href').slice(1));
      window.scrollTo({top:0,behavior:'smooth'});});
  });

  var initial=(location.hash||'').slice(1);
  show(DATA[initial] ? initial : 'overview-panel');
})();
"""


def build_body(results: list[TaxonResult], master_path: str, survey_path: str) -> str:
    """`<body>` 안에 들어갈 내용만 만든다(style·script 포함).

    자체 완결형 HTML(`build_html`)과 문서 골격 없이 삽입하는 경우
    (아티팩트 게시 등) 모두 이 결과를 쓴다.
    """
    payload = {}
    for r in results:
        d = _taxon_payload(r)
        payload[r.spec.code] = {"rows": d["rows"], "hasInd": r.spec.has_individuals}

    rail = "".join(
        f'<li><button type="button" data-go="{r.spec.code}">'
        f'<span>{_esc(r.name)}</span><span class="badge">{r.totals.total:,}</span>'
        f'</button></li>' for r in results)

    panels = [
        f'<section class="taxon-panel" id="overview-panel">'
        f'<div class="taxon-head"><h2>전체 개요</h2>'
        f'<p>8개 분류군의 출현종수와 분석항목 산출 가능 범위</p></div>'
        f'{_matrix(results)}'
        f'{_bars("분류군별 출현종수", [(r.name, r.totals.total) for r in results])}'
        f'</section>'
    ]
    for r in results:
        panels.append(f"""
<section class="taxon-panel" id="{r.spec.code}" hidden>
  <div class="taxon-head">
    <h2>{_esc(r.name)}</h2>
    <p>표준종목록 {r.total_species_in_db:,}종 대조 · 현지조사 기록 방식:
       {_esc({"count": "개체수", "method": "조사방법 코드", "presence": "출현 여부"}[r.spec.field_value])}</p>
  </div>
  {_cards(r)}
  {_survey_table(r)}
  {_bars("과별 출현종수 상위", r.taxonomy.by_family,
         f"총 {r.taxonomy.family_count:,}과 / {r.taxonomy.order_count:,}목")}
  {_legal_lists(r)}
  {_specific(r)}
  {_quantitative(r)}
  {_species_section(r)}
  {_notes(r)}
</section>""")

    js = JS % {"page": SPECIES_PAGE, "ncols": len(SURVEY_COLS)}
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<style>{CSS}</style>
<header class="top">
  <div class="top-inner">
    <div>
      <p class="eyebrow">환경영향평가 동·식물상</p>
      <h1>생태조사 분석 결과 검수</h1>
      <p class="meta">
        마스터DB <code>{_esc(Path(master_path).name)}</code><br>
        조사자료 <code>{_esc(Path(survey_path).name)}</code> · 생성 {generated}
      </p>
    </div>
    <div class="banner">파일럿 가상데이터 — 실제 조사 결과 아님</div>
  </div>
</header>

<div class="shell">
  <nav class="rail" aria-label="분류군">
    <p class="rail-title">분류군</p>
    <ul>
      <li><button type="button" data-go="overview-panel">
        <span>전체 개요</span><span class="badge">8</span></button></li>
      {rail}
    </ul>
  </nav>
  <main>{"".join(panels)}</main>
</div>

<footer><div class="inner">
  화면의 모든 수치는 Python 분석 계층이 확정한 값이다. 이 페이지는 다시 계산하지 않는다.
  산출할 수 없는 항목은 0으로 채우지 않고 사유와 함께 표시한다.
</div></footer>

<script>window.__TAXA__={json.dumps(payload, ensure_ascii=False, separators=(",", ":"))};</script>
<script>{js}</script>"""


def build_html(results: list[TaxonResult], master_path: str, survey_path: str) -> str:
    """브라우저로 바로 여는 자체 완결형 HTML 문서."""
    body = build_body(results, master_path, survey_path)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>생태조사 분석 결과 검수</title>
</head>
<body>
{body}
</body>
</html>"""


def write_report(results: list[TaxonResult], out_path: Path | str,
                 master_path: str, survey_path: str, fragment: bool = False) -> Path:
    """HTML 파일로 저장한다.

    fragment=True 면 문서 골격 없이 내용만 쓴다. 게시 시 골격을 감싸주는
    환경에 넘길 때 사용한다.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    build = build_body if fragment else build_html
    out.write_text(build(results, master_path, survey_path), encoding="utf-8")
    return out
