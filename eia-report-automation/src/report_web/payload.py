"""화면에 내보낼 데이터 구성.

분석 결과를 **렌더 서술자(block)** 로 바꾼다. 항목마다 전용 JS 를 짜지
않도록, 파이썬이 "이 항목은 이런 형태로 그려라"를 지정하고 화면은 몇 개의
범용 렌더러만 갖는다.

화면은 사전 계산된 값을 고르고 그릴 뿐 지수를 계산하지 않는다. 종목록
필터링만 출현 비트로 처리하는데, 이는 계산이 아니라 선별이다.
"""

from __future__ import annotations

from typing import Any

from ..analysis.item_catalog import ITEM_BY_CODE, ItemVerdict, evaluate_scope
from ..analysis.runner import ScopeResult, TaxonResult
from ..data.schema import LITERATURE_COLUMNS, is_null_token

# 렌더 서술자 종류
KV = "kv"  # 항목-값 표
BARS = "bars"  # 막대 + 표
STACKED = "stacked"  # 누적막대 + 표
MATRIX = "matrix"  # 행렬 표 (지수 비교 등)
HEATMAP = "heatmap"  # 지점간 유사도
CHIPS = "chips"  # 종 목록 칩
SPECIES = "species"  # 종목록 표 (단위로 필터)

CHIP_LIMIT = 60
SPECIES_CHIP_LIMIT = 40


def _kv(rows: list[tuple[str, Any]], note: str = "") -> dict:
    return {"kind": KV, "rows": [[k, v] for k, v in rows], "note": note}


def _bars(items: list[tuple[str, int]], unit: str = "종", note: str = "",
          limit: int = 12) -> dict:
    return {"kind": BARS, "items": [[k, v] for k, v in items[:limit]],
            "unit": unit, "note": note,
            "truncated": max(0, len(items) - limit)}


def _chips(groups: list[dict], note: str = "") -> dict:
    return {"kind": CHIPS, "groups": groups, "note": note}


def _matrix(columns: list[str], rows: list[list[Any]], note: str = "") -> dict:
    return {"kind": MATRIX, "columns": columns, "rows": rows, "note": note}


# ── 항목별 블록 ────────────────────────────────────────────────────────

def _blocks_totals(r: ScopeResult) -> list[dict]:
    t = r.totals
    rows = [("총 출현종수", t.total)]
    if r.scope.has_literature:
        rows.append(("문헌조사", t.literature))
    if r.scope.has_field:
        rows.append(("현지조사", t.field_survey))
    blocks = [_kv(rows)]
    if len(t.by_column) > 1:
        blocks.append(_bars(list(t.by_column.items()), note="컬럼별 출현종수"))
    return blocks


def _blocks_source(r: ScopeResult) -> list[dict]:
    t = r.totals
    seg = [("문헌 단독", t.literature_only), ("공통", t.both), ("현지 단독", t.field_only)]
    return [
        {"kind": STACKED, "segments": [[k, v] for k, v in seg], "total": t.total},
        _kv([("문헌조사 출현종", t.literature), ("현지조사 출현종", t.field_survey),
             ("문헌·현지 공통", t.both), ("문헌 단독", t.literature_only),
             ("현지 단독 (문헌 미기재)", t.field_only)]),
    ]


def _blocks_round(r: ScopeResult) -> list[dict]:
    t = r.totals
    blocks = [_kv([(k, v) for k, v in t.by_round.items()] +
                  [("현지 2차 신규 출현종", t.new_in_field_round2)])]
    if len(t.by_round) > 1:
        blocks.append(_bars(list(t.by_round.items()), note="회차별 출현종수"))
    return blocks


def _blocks_family(r: ScopeResult) -> list[dict]:
    return [_bars(r.taxonomy.by_family,
                  note=f"총 {r.taxonomy.family_count:,}과 중 상위")]


def _blocks_order(r: ScopeResult) -> list[dict]:
    return [_bars(r.taxonomy.by_order,
                  note=f"총 {r.taxonomy.order_count:,}목 중 상위")]


def _blocks_legal(r: ScopeResult) -> list[dict]:
    groups = []
    for title, items, tone in (
        ("멸종위기야생생물 Ⅰ급", r.legal.endangered_1, "critical"),
        ("멸종위기야생생물 Ⅱ급", r.legal.endangered_2, "critical"),
        ("천연기념물", r.legal.natural_monument, ""),
    ):
        groups.append({
            "title": title, "count": len(items), "tone": tone,
            "items": [f"{s.korean_name} ({s.scientific_name})" for s in items[:CHIP_LIMIT]],
        })
    counts = [(k, v) for k, v in r.legal.counts.items() if k != "시·도보호종"]
    return [_kv(counts), _chips(groups)]


def _blocks_invasive(r: ScopeResult) -> list[dict]:
    items = r.legal.invasive
    return [_chips([{"title": "생태계교란생물", "count": len(items), "tone": "warn",
                     "items": [f"{s.korean_name} ({s.scientific_name})" for s in items]}])]


def _blocks_local(r: ScopeResult) -> list[dict]:
    items = r.legal.local_protected
    return [_chips([{"title": "시·도보호종", "count": len(items), "tone": "",
                     "items": [s.korean_name for s in items[:CHIP_LIMIT]]}],
                   note="사업 대상지의 시·도에 해당하는 종만 골라 사용한다.")]


def _blocks_species(r: ScopeResult) -> list[dict]:
    return [{"kind": SPECIES}]


def _blocks_specific(name: str):
    def build(r: ScopeResult) -> list[dict]:
        item = next((i for i in r.specific if i.name.startswith(name)), None)
        if item is None:
            return []
        blocks: list[dict] = [_kv([(item.name, item.value)], note=item.note)]
        if item.breakdown:
            blocks.append(_bars(item.breakdown, note="구성"))
        if item.species:
            blocks.append(_chips([{
                "title": item.name, "count": len(item.species), "tone": "",
                "items": item.species[:SPECIES_CHIP_LIMIT]}]))
        return blocks
    return build


def _blocks_dominant(r: ScopeResult) -> list[dict]:
    if not r.quantitative:
        return []
    q = r.quantitative[0]
    return [
        _bars([(n, c) for n, c, _ in q.dominant], unit="개체",
              note=f"{q.label} 우점 상위 {len(q.dominant)}종"),
        _matrix(["종", "개체수", "상대풍부도(%)"],
                [[n, c, f"{ra:.1f}"] for n, c, ra in q.dominant]),
    ]


def _blocks_indices(r: ScopeResult) -> list[dict]:
    if not r.quantitative:
        return []
    cols = ["구분"] + [q.label for q in r.quantitative]
    rows = [
        ["종수 S"] + [q.species_count for q in r.quantitative],
        ["개체수 N"] + [q.individuals for q in r.quantitative],
        ["우점도 DI"] + [f"{q.dominance:.3f}" for q in r.quantitative],
        ["다양도 H'"] + [f"{q.diversity:.3f}" for q in r.quantitative],
        ["균등도 J'"] + [f"{q.evenness:.3f}" for q in r.quantitative],
        ["풍부도 R1"] + [f"{q.richness:.3f}" for q in r.quantitative],
        ["우점종"] + [q.dominant_species for q in r.quantitative],
    ]
    blocks = [_matrix(cols, rows,
                      note="지수는 단위마다 각각 산출한다. 단위를 합산하지 않는다.")]
    if len(r.quantitative) > 1:
        blocks.append(_bars([(q.label, round(q.diversity, 3)) for q in r.quantitative],
                            unit="H'", note="단위별 다양도 비교"))
    return blocks


def _station_round(r: ScopeResult):
    valid = [a for a in r.stations if len(a.stations) >= 2]
    return valid[0] if valid else None


def _blocks_station_species(r: ScopeResult) -> list[dict]:
    a = _station_round(r)
    if not a:
        return []
    return [_bars([(s.label, s.species_count) for s in a.stations],
                  note=f"{a.round_name} 정점별 출현종수"),
            _kv([("전 정점 공통 출현종", a.shared_all),
                 ("한 정점에서만 출현", a.unique_total)])]


def _blocks_station_individuals(r: ScopeResult) -> list[dict]:
    a = _station_round(r)
    if not a:
        return []
    items = [(s.label, s.individuals or 0) for s in a.stations]
    return [_bars(items, unit="개체", note=f"{a.round_name} 정점별 개체수")]


def _blocks_station_indices(r: ScopeResult) -> list[dict]:
    a = _station_round(r)
    if not a:
        return []
    stations = [s for s in a.stations if s.indices]
    if not stations:
        return []
    cols = ["구분"] + [s.label for s in stations]
    rows = [
        ["종수 S"] + [s.indices.species_count for s in stations],
        ["개체수 N"] + [s.indices.individuals for s in stations],
        ["우점도 DI"] + [f"{s.indices.dominance:.3f}" for s in stations],
        ["다양도 H'"] + [f"{s.indices.diversity:.3f}" for s in stations],
        ["균등도 J'"] + [f"{s.indices.evenness:.3f}" for s in stations],
        ["풍부도 R1"] + [f"{s.indices.richness:.3f}" for s in stations],
        ["우점종"] + [s.indices.dominant_species for s in stations],
    ]
    return [_matrix(cols, rows, note=f"{a.round_name} 정점별 군집지수"),
            _bars([(s.label, round(s.indices.diversity, 3)) for s in stations],
                  unit="H'", note="정점별 다양도")]


def _blocks_station_similarity(r: ScopeResult) -> list[dict]:
    a = _station_round(r)
    if not a:
        return []
    return [
        {"kind": HEATMAP, "labels": a.labels, "values": a.similarity,
         "note": f"{a.round_name} 지점간 Sørensen 유사도"},
        _kv([("전 정점 공통 출현종", a.shared_all),
             ("한 정점에서만 출현", a.unique_total)]),
    ]


BLOCK_BUILDERS = {
    "T1-01": _blocks_totals,
    "T1-02": _blocks_source,
    "T1-03": _blocks_round,
    "T1-04a": _blocks_order,
    "T1-04b": _blocks_family,
    "T1-05": _blocks_legal,
    "T1-06": _blocks_invasive,
    "T1-07": _blocks_local,
    "T1-08": _blocks_species,
    "T2-P1": _blocks_specific("식물구계학적특정종"),
    "T2-P2": _blocks_specific("희귀식물"),
    "T2-P3": _blocks_specific("특산식물"),
    "T2-P4": _blocks_specific("귀화식물"),
    "T2-P5": _blocks_specific("생활형"),
    "T2-M1": _blocks_specific("현지조사 방법별"),
    "T2-B1": _blocks_specific("도래유형"),
    "T2-F1": _blocks_specific("한국고유종"),
    "T2-F2": _blocks_specific("외래종"),
    "T2-N1": _blocks_specific("오수생물지수"),
    "T3-01": _blocks_dominant,
    "T3-02": _blocks_indices,
    "S-01": _blocks_station_species,
    "S-02": _blocks_station_individuals,
    "S-03": _blocks_station_indices,
    "S-04": _blocks_station_similarity,
}


def _item_payload(r: ScopeResult, verdict: ItemVerdict) -> dict:
    spec = ITEM_BY_CODE[verdict.code]
    usable = verdict.table.mark != "✗"
    blocks = BLOCK_BUILDERS[verdict.code](r) if usable else []
    return {
        "code": verdict.code,
        "name": spec.name,
        "tier": spec.tier,
        "table": [verdict.table.mark, verdict.table.reason],
        "graph": [verdict.graph.mark, verdict.graph.reason],
        "blocks": blocks,
    }


def scope_payload(result: TaxonResult, sr: ScopeResult) -> dict:
    verdicts = evaluate_scope(result, sr.key)
    return {
        "key": sr.key,
        "label": sr.scope.label,
        "kind": sr.scope.kind,
        "columns": list(sr.scope.columns),
        "total": sr.totals.total,
        "items": [_item_payload(sr, v) for v in verdicts],
    }


def taxon_payload(result: TaxonResult) -> dict:
    """분류군 하나의 전체 페이로드."""
    columns = list(result.species_rows[0].marks) if result.species_rows else []
    species = [
        [row.family, row.scientific_name, row.korean_name, row.abb,
         "".join("1" if row.marks.get(c) else "0" for c in columns)]
        for row in result.species_rows
    ]
    return {
        "code": result.spec.code,
        "label": result.name,
        "stations": result.spec.stations,
        "dbTotal": result.total_species_in_db,
        "columns": columns,
        "species": species,
        "notes": result.notes,
        "scopes": [scope_payload(result, sr) for sr in result.scopes],
    }


def build_payload(results: list[TaxonResult]) -> dict:
    return {r.spec.code: taxon_payload(r) for r in results}


def template_payload(template) -> dict:
    """보고서 템플릿을 우측 미리보기용 구조로 바꾼다.

    목차 순서대로 제목과 자리(표·그림)를 늘어놓는다. 어느 자리에 무엇을
    넣을지는 화면에서 사용자가 정하므로, 여기서는 자리만 만들어 준다.
    """
    rows: list[dict] = []
    for heading in template.headings:
        rows.append({
            "type": "heading",
            "level": heading.level,
            "title": heading.title,
            "order": heading.order,
        })
        for slot in heading.slots:
            rows.append({
                "type": "slot",
                "kind": slot.kind,
                "number": slot.number,
                "title": slot.title,
                "order": slot.order,
                "id": f"{slot.kind}:{slot.number}",
            })
    return {
        "source": template.source,
        "chapter": template.chapter,
        "rows": rows,
        "counts": {
            "heading": len(template.headings),
            "표": len(template.tables),
            "그림": len([s for s in template.figures if s.kind == "그림"]),
            "사진": len([s for s in template.figures if s.kind == "사진"]),
        },
        "notes": list(template.notes),
    }
