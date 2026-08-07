"""HWPX 평가서에서 보고서 템플릿(목차·표·그림 자리)을 추출한다.

HWPX 는 ZIP+XML(OWPML) 패키지이므로 한글 프로그램 없이 읽는다. 기존
평가서를 넣으면 목차 계층과 표·그림이 들어갈 자리를 뽑아내며, 이것이
"보고서 미리보기" 패널의 골격이 된다.

업체마다 평가서 양식이 다르므로 **스타일 ID 를 믿지 않는다.** 스타일 ID
는 문서마다 값이 달라(이 문서에서 21이 1수준이어도 다른 문서에서는 아니다)
이식되지 않는다. 대신 번호 체계와 캡션 표기를 1차 신호로 쓰고, 스타일 ID
는 같은 수준끼리 묶였는지 확인하는 보조 신호로만 쓴다.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hp": HP}

# 목차 번호 체계. 위에서부터 깊은 수준으로 본다.
# 환경영향평가서는 보통 "1)" 아래 "(1)" 아래 "①" 순으로 내려간다.
HEADING_PATTERNS: tuple[tuple[str, int], ...] = (
    (r"^(\d+\.\d+\.\d+)\s+\S", 1),
    (r"^(\d+\.\d+)\s+\S", 1),
    (r"^([가-힣])\.\s+\S", 1),
    (r"^(\d+)\)\s*\S", 2),
    (r"^\((\d+)\)\s*\S", 3),
    (r"^([①-⑮])\s*\S", 4),
)

# 캡션. 업체마다 괄호가 <> 또는 () 로 갈리고 '사진'을 따로 쓰기도 한다.
CAPTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^[<\(【]\s*표\s*([\d.\-]+)\s*[>\)】]\s*(.*)", "표"),
    (r"^[<\(【]\s*그림\s*([\d.\-]+)\s*[>\)】]\s*(.*)", "그림"),
    (r"^[<\(【]\s*사진\s*([\d.\-]+)\s*[>\)】]\s*(.*)", "사진"),
)


@dataclass
class Slot:
    """표·그림·사진이 들어갈 자리."""

    kind: str  # 표 | 그림 | 사진
    number: str  # 캡션 번호 (예: 9.1.1-4)
    title: str
    order: int  # 문서 전체에서의 등장 순서

    @property
    def label(self) -> str:
        return f"{self.kind} {self.number}"


@dataclass
class Heading:
    """목차 항목 하나."""

    level: int
    marker: str  # 번호 표기 (예: '4', '(1)')
    title: str
    order: int
    style_id: str | None = None
    slots: list[Slot] = field(default_factory=list)


@dataclass
class ReportTemplate:
    """추출된 보고서 구조."""

    source: str
    headings: list[Heading] = field(default_factory=list)
    slots: list[Slot] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def tables(self) -> list[Slot]:
        return [s for s in self.slots if s.kind == "표"]

    @property
    def figures(self) -> list[Slot]:
        return [s for s in self.slots if s.kind in ("그림", "사진")]

    @property
    def chapter(self) -> str:
        """이 문서의 장 번호(캡션 접두사).

        동·식물상은 사업마다 7.1.1·8.1.1·9.1.1 등으로 달라진다. 다른 평가
        매체와의 순서에 따라 정해지므로 문서에서 읽어 낼 뿐 고정하지 않는다.
        """
        counts: dict[str, int] = {}
        for s in self.slots:
            if "-" in s.number:
                prefix = s.number.rsplit("-", 1)[0]
                counts[prefix] = counts.get(prefix, 0) + 1
        return max(counts, key=counts.get) if counts else ""

    def renumber(self, chapter: str | None = None,
                 merge_figures: bool = False) -> "ReportTemplate":
        """캡션 번호를 다시 매긴다.

        장 번호가 바뀌거나(9.1.1 → 7.1.1) 항목을 넣고 빼면 뒤 번호가 전부
        밀린다. 손으로 고치면 반드시 빠뜨리므로 프로그램이 다시 매긴다.

        `chapter` 를 주지 않으면 현재 장 번호를 유지한다. `merge_figures`
        는 사진을 그림과 한 계열로 묶을지 정한다. 업체마다 관행이 다르다.
        """
        target = chapter or self.chapter
        series: dict[str, int] = {}
        renumbered: list[Slot] = []

        for slot in sorted(self.slots, key=lambda s: s.order):
            key = "그림" if (merge_figures and slot.kind == "사진") else slot.kind
            series[key] = series.get(key, 0) + 1
            renumbered.append(Slot(
                kind=slot.kind,
                number=f"{target}-{series[key]}" if target else str(series[key]),
                title=slot.title,
                order=slot.order,
            ))

        by_order = {s.order: s for s in renumbered}
        headings = [
            Heading(level=h.level, marker=h.marker, title=h.title, order=h.order,
                    style_id=h.style_id,
                    slots=[by_order[s.order] for s in h.slots])
            for h in self.headings
        ]
        return ReportTemplate(source=self.source, headings=headings,
                              slots=renumbered, notes=list(self.notes))

    def outline(self) -> str:
        """사람이 읽는 목차 문자열. 검수용."""
        lines = []
        for h in self.headings:
            lines.append("  " * (h.level - 1) + f"▸ {h.title}")
            for s in h.slots:
                lines.append("  " * h.level + f"[{s.kind}] {s.number} {s.title}")
        return "\n".join(lines)


# 문단 안에 들어와도 그 문단의 텍스트로 치지 않는 것들.
# 표(목차 표·글상자)와 제어 요소(머리말·바닥글·각주)가 여기에 해당한다.
NESTED_CONTAINERS = frozenset({f"{{{HP}}}tbl", f"{{{HP}}}ctrl"})

# 본문이 아닌 곳에 있는 문단. 목차로 잡으면 안 된다.
NON_BODY_ANCESTORS = frozenset({
    f"{{{HP}}}tc",        # 표 셀
    f"{{{HP}}}header",    # 머리말
    f"{{{HP}}}footer",    # 바닥글
    f"{{{HP}}}footNote",  # 각주
    f"{{{HP}}}endNote",   # 미주
})


def _paragraph_text(p) -> str:
    """문단 자신의 텍스트만 모은다.

    문단 안에 표나 머리말이 들어 있는 경우가 있다. `.//hp:t` 로 훑으면 그
    내용까지 딸려 와 제목이 뒤엉킨다(실제 샘플에서 머리말이 본문 제목에
    붙어 나왔다). 중첩 컨테이너 아래로는 내려가지 않는다.
    """
    parts: list[str] = []

    def walk(node) -> None:
        for child in node:
            if child.tag in NESTED_CONTAINERS:
                continue
            if child.tag == f"{{{HP}}}t":
                parts.append(child.text or "")
            else:
                walk(child)

    walk(p)
    return "".join(parts).strip()


def _in_table(p) -> bool:
    """본문 밖(표 셀·머리말·바닥글·각주)의 문단인가."""
    return any(a.tag in NON_BODY_ANCESTORS for a in p.iterancestors())


def _classify(text: str) -> tuple[str, ...] | None:
    """문단이 제목인지 캡션인지 판정한다."""
    for pattern, kind in CAPTION_PATTERNS:
        m = re.match(pattern, text)
        if m:
            return ("caption", kind, m.group(1), (m.group(2) or "").strip())
    for pattern, level in HEADING_PATTERNS:
        m = re.match(pattern, text)
        if m:
            return ("heading", str(level), m.group(1), text)
    return None


def _sections(path: Path) -> list[bytes]:
    """본문 섹션 XML 을 순서대로 읽는다."""
    with zipfile.ZipFile(path) as z:
        names = sorted(
            (n for n in z.namelist()
             if re.fullmatch(r"Contents/section\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[-1]).group(1)),
        )
        if not names:
            raise ValueError(f"[{path.name}] 본문 섹션을 찾을 수 없습니다. HWPX 가 맞습니까?")
        return [z.read(n) for n in names]


def extract_template(hwpx_path: Path | str) -> ReportTemplate:
    """기존 평가서에서 목차와 표·그림 자리를 추출한다."""
    path = Path(hwpx_path)
    template = ReportTemplate(source=path.name)
    order = 0
    current: Heading | None = None

    for raw in _sections(path):
        root = etree.fromstring(raw)
        for p in root.iter(f"{{{HP}}}p"):
            if _in_table(p):
                continue
            text = _paragraph_text(p)
            if not text:
                continue
            hit = _classify(text)
            if hit is None:
                continue
            order += 1

            if hit[0] == "caption":
                _, kind, number, title = hit
                slot = Slot(kind=kind, number=number, title=title, order=order)
                template.slots.append(slot)
                if current is not None:
                    current.slots.append(slot)
            else:
                _, level, marker, title = hit
                current = Heading(level=int(level), marker=marker, title=title,
                                  order=order, style_id=p.get("styleIDRef"))
                template.headings.append(current)

    template.notes.extend(_check(template))
    return template


def _check(t: ReportTemplate) -> list[str]:
    """양식의 흔들림을 잡아 둔다. 자동화가 고쳐 줄 수 있는 부분이다."""
    notes: list[str] = []
    if not t.headings:
        notes.append("목차를 찾지 못했습니다. 번호 체계가 다른 양식일 수 있습니다.")

    # 캡션의 장 번호는 문서 전체에서 하나여야 한다. 다른 장 번호가 섞였다면
    # 다른 평가서에서 복사해 온 흔적이다.
    prefixes: dict[str, list[Slot]] = {}
    for s in t.slots:
        if "-" in s.number:
            prefixes.setdefault(s.number.rsplit("-", 1)[0], []).append(s)
    if len(prefixes) > 1:
        dominant = max(prefixes, key=lambda k: len(prefixes[k]))
        for prefix, slots in prefixes.items():
            if prefix == dominant:
                continue
            labels = ", ".join(f"{s.kind} {s.number}" for s in slots)
            notes.append(
                f"장 번호가 다른 캡션이 있습니다: {labels} "
                f"(이 문서의 장 번호는 {dominant}). "
                f"renumber() 로 일괄 정정할 수 있습니다.")

    # 번호가 연속인지 (빠진 번호는 편집 중 삭제 흔적)
    for kind in ("표", "그림"):
        nums = []
        for s in t.slots:
            if s.kind != kind or "-" not in s.number:
                continue
            tail = s.number.rsplit("-", 1)[1]
            if tail.isdigit():
                nums.append(int(tail))
        if nums:
            missing = sorted(set(range(1, max(nums) + 1)) - set(nums))
            if missing:
                notes.append(f"{kind} 번호가 비어 있습니다: {missing}")
    return notes
