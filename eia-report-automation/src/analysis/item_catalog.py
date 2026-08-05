"""분석항목 카탈로그와 표·그래프 산출 가능성 판정.

`docs/analysis_items_by_taxon.md` 의 판정표를 코드로 옮긴 것이다. 문서와
화면이 어긋나지 않도록 판정을 하드코딩하지 않고 `TaxonResult` 에서
파생시킨다.

판정 기호
    ○ 가능   바로 생성할 수 있다
    △ 제한   일부 결측·커버리지 부족, 또는 상위 N개만 의미 있다
    ✗ 불가   필요한 자료가 없거나 그래프로 의미가 없다
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .runner import TaxonResult

OK = "○"
LIMITED = "△"
NONE = "✗"

# 범주가 이보다 많으면 전체를 한 그래프에 담을 수 없다. 상위 N개만 쓴다.
MAX_GRAPH_CATEGORIES = 12
# 범주가 이보다 적으면 그래프보다 표가 낫다.
MIN_GRAPH_CATEGORIES = 3
# 종수가 이보다 적으면 그래프로 그릴 실익이 없다.
MIN_GRAPH_SPECIES = 10


@dataclass
class Verdict:
    """판정 하나. 기호와 근거를 함께 들고 다닌다."""

    mark: str
    reason: str


@dataclass
class ItemVerdict:
    """분류군 하나에 대한 항목 판정."""

    item: str
    tier: str
    taxon: str
    table: Verdict
    graph: Verdict


def _by_categories(count: int, subject: str, species: int | None = None) -> Verdict:
    """범주 수로 그래프 적합성을 판정한다."""
    if count == 0:
        return Verdict(NONE, "해당 자료 없음")
    if species is not None and species < MIN_GRAPH_SPECIES:
        return Verdict(NONE, f"{species}종으로 그래프 실익 없음")
    if count < MIN_GRAPH_CATEGORIES:
        return Verdict(LIMITED, f"{subject} {count}개로 표가 적합")
    if count > MAX_GRAPH_CATEGORIES:
        return Verdict(LIMITED, f"{subject} {count}개 — 상위 {MAX_GRAPH_CATEGORIES}개만")
    return Verdict(OK, f"{subject} {count}개")


# ── 공통 항목 (T1) ─────────────────────────────────────────────────────

def _v_total(r: TaxonResult) -> tuple[Verdict, Verdict]:
    n = r.totals.total
    return (Verdict(OK, f"출현 {n:,}종"),
            Verdict(OK, "분류군 간 비교 막대") if n else Verdict(NONE, "출현종 없음"))


def _v_source(r: TaxonResult) -> tuple[Verdict, Verdict]:
    t = r.totals
    detail = f"공통 {t.both:,} · 문헌단독 {t.literature_only:,} · 현지단독 {t.field_only:,}"
    return Verdict(OK, detail), Verdict(OK, "4구분 누적막대")


def _v_round(r: TaxonResult) -> tuple[Verdict, Verdict]:
    detail = f"2차 신규 {r.totals.new_in_field_round2:,}종"
    return Verdict(OK, detail), Verdict(LIMITED, "차수 2개뿐이라 추세 표현 어려움")


def _v_family(r: TaxonResult) -> tuple[Verdict, Verdict]:
    n = r.taxonomy.family_count
    top = r.taxonomy.by_family[0] if r.taxonomy.by_family else ("-", 0)
    return (Verdict(OK, f"{n:,}과 · 최다 {top[0]} {top[1]:,}종"),
            _by_categories(n, "과"))


def _v_order(r: TaxonResult) -> tuple[Verdict, Verdict]:
    n = r.taxonomy.order_count
    return Verdict(OK, f"{n:,}목"), _by_categories(n, "목")


def _v_legal(r: TaxonResult) -> tuple[Verdict, Verdict]:
    total = r.legal.endangered_total + len(r.legal.natural_monument)
    if not total:
        return Verdict(OK, "해당 없음(빈 표)"), Verdict(NONE, "출현 보호종 없음")
    detail = (f"멸Ⅰ {len(r.legal.endangered_1)} · 멸Ⅱ {len(r.legal.endangered_2)} · "
              f"천연 {len(r.legal.natural_monument)}")
    graph = (Verdict(LIMITED, f"{total}종으로 목록 표가 우선")
             if total < 20 else Verdict(OK, "등급별 막대"))
    return Verdict(OK, detail), graph


def _v_invasive(r: TaxonResult) -> tuple[Verdict, Verdict]:
    n = len(r.legal.invasive)
    return (Verdict(OK, f"{n}종"),
            Verdict(NONE, f"{n}종으로 그래프 실익 없음"))


def _v_local(r: TaxonResult) -> tuple[Verdict, Verdict]:
    n = len(r.legal.local_protected)
    return (Verdict(OK, f"{n}종 — 대상지 시·도만 선별"),
            Verdict(NONE, "시·도 선별 후 목록으로 제시"))


def _v_species_list(r: TaxonResult) -> tuple[Verdict, Verdict]:
    return (Verdict(OK, f"{len(r.species_rows):,}행"),
            Verdict(NONE, "목록 자체가 산출물"))


def _v_quantitative(r: TaxonResult) -> tuple[Verdict, Verdict]:
    if not r.quantitative:
        reason = r.quantitative_unavailable or "개체수 없음"
        return Verdict(NONE, reason), Verdict(NONE, reason)
    q = r.quantitative[0]
    return (Verdict(OK, f"{q.label} S={q.species_count:,} N={q.individuals:,}"),
            Verdict(LIMITED, "차수 2개 — 차수 간 비교 막대"))


def _v_dominant(r: TaxonResult) -> tuple[Verdict, Verdict]:
    if not r.quantitative:
        reason = r.quantitative_unavailable or "개체수 없음"
        return Verdict(NONE, reason), Verdict(NONE, reason)
    q = r.quantitative[0]
    share = sum(ra for _, _, ra in q.dominant)
    return (Verdict(OK, f"우점 {q.dominant_species} · 상위{len(q.dominant)}종 {share:.1f}%"),
            Verdict(OK, "상대풍부도 막대"))


# ── 분류군 특이 항목 (T2) ──────────────────────────────────────────────

def _specific(name: str) -> Callable[[TaxonResult], tuple[Verdict, Verdict]]:
    """T2 결과에서 해당 항목을 찾아 판정한다."""

    def check(r: TaxonResult) -> tuple[Verdict, Verdict]:
        item = next((i for i in r.specific if i.name.startswith(name)), None)
        if item is None:
            return Verdict(NONE, "해당 자료 없음"), Verdict(NONE, "해당 자료 없음")
        table = Verdict(OK, f"{item.value}{' · ' + item.note if item.note else ''}")
        if item.breakdown:
            graph = _by_categories(len(item.breakdown), "범주")
        elif item.species:
            graph = Verdict(NONE, f"{len(item.species)}종 목록 — 등급 구분 없음")
        else:
            graph = Verdict(LIMITED, "단일 수치")
        return table, graph

    return check


def _v_saprobic(r: TaxonResult) -> tuple[Verdict, Verdict]:
    """오수생물지수는 지수 자체보다 Qi 보유 커버리지가 신뢰도를 좌우한다."""
    item = next((i for i in r.specific if i.name.startswith("오수생물지수")), None)
    if item is None:
        return Verdict(NONE, "Qi 자료 없음"), Verdict(NONE, "Qi 자료 없음")
    bd = dict(item.breakdown)
    have = bd.get("Qi 보유 출현종", 0)
    contrib = bd.get("가중평균 기여종 (개체수 보유)", 0)
    total = have + bd.get("Qi 미보유 출현종", 0) or 1
    table = Verdict(
        LIMITED,
        f"Qi 보유 {have:,}/{total:,}종({have / total * 100:.1f}%), "
        f"가중평균 기여 {contrib:,}종({contrib / total * 100:.1f}%) — 참고값 한정")
    return table, Verdict(NONE, "단일 참고 수치, 등급 구분 없음")


@dataclass
class ItemSpec:
    """분석항목 하나의 정의."""

    code: str
    name: str
    tier: str
    taxa: tuple[str, ...] | None  # None 이면 전 분류군
    check: Callable[[TaxonResult], tuple[Verdict, Verdict]]
    note: str = ""

    def applies_to(self, taxon: str) -> bool:
        return self.taxa is None or taxon in self.taxa


ALL = None
COUNT_TAXA = ("조류", "어류", "저서성대형무척추동물")

ITEMS: tuple[ItemSpec, ...] = (
    ItemSpec("T1-01", "출현종 총괄", "T1", ALL, _v_total),
    ItemSpec("T1-02", "조사구분별 종수", "T1", ALL, _v_source),
    ItemSpec("T1-03", "조사차수별 종수·신규종", "T1", ALL, _v_round),
    ItemSpec("T1-04a", "목별 구성", "T1", ALL, _v_order),
    ItemSpec("T1-04b", "과별 출현종수", "T1", ALL, _v_family),
    ItemSpec("T1-05", "법정보호종", "T1", ALL, _v_legal),
    ItemSpec("T1-06", "생태계교란생물", "T1", ALL, _v_invasive),
    ItemSpec("T1-07", "시·도보호종", "T1", ALL, _v_local),
    ItemSpec("T1-08", "종목록", "T1", ALL, _v_species_list),

    ItemSpec("T2-P1", "식물구계학적특정종", "T2", ("관속식물",), _specific("식물구계학적특정종")),
    ItemSpec("T2-P2", "희귀식물", "T2", ("관속식물",), _specific("희귀식물")),
    ItemSpec("T2-P3", "특산식물", "T2", ("관속식물",), _specific("특산식물")),
    ItemSpec("T2-P4", "귀화식물·귀화율·도시화지수", "T2", ("관속식물",), _specific("귀화식물")),
    ItemSpec("T2-P5", "생활형(Raunkiaer) 스펙트럼", "T2", ("관속식물",), _specific("생활형")),
    ItemSpec("T2-M1", "조사방법별 확인종수", "T2", ("포유류",), _specific("현지조사 방법별")),
    ItemSpec("T2-B1", "도래유형 구성", "T2", ("조류",), _specific("도래유형")),
    ItemSpec("T2-F1", "한국고유종·고유화빈도", "T2", ("어류", "육상곤충류"), _specific("한국고유종")),
    ItemSpec("T2-F2", "외래종", "T2", ("어류",), _specific("외래종")),
    ItemSpec("T2-N1", "오수생물지수 Qi", "T2", ("저서성대형무척추동물",), _v_saprobic),

    ItemSpec("T3-01", "우점종·상대풍부도", "T3", COUNT_TAXA, _v_dominant),
    ItemSpec("T3-02", "군집지수 (DI·H'·J'·R1)", "T3", COUNT_TAXA, _v_quantitative),
)


def evaluate(results: list[TaxonResult]) -> list[ItemVerdict]:
    """모든 항목 × 분류군 조합을 판정한다."""
    by_name = {r.name: r for r in results}
    out: list[ItemVerdict] = []
    for spec in ITEMS:
        for r in results:
            if not spec.applies_to(r.name):
                continue
            table, graph = spec.check(r)
            out.append(ItemVerdict(spec.name, spec.tier, r.name, table, graph))
    return out


def summarize(results: list[TaxonResult]) -> dict[str, dict[str, int]]:
    """기호별 집계. 문서와 화면의 총계를 맞추는 데 쓴다."""
    counts: dict[str, dict[str, int]] = {"표": {OK: 0, LIMITED: 0, NONE: 0},
                                         "그래프": {OK: 0, LIMITED: 0, NONE: 0}}
    for v in evaluate(results):
        counts["표"][v.table.mark] += 1
        counts["그래프"][v.graph.mark] += 1
    return counts
