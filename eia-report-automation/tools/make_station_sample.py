"""정점조사 가상데이터 생성 (v7 → v8).

어류와 저서성대형무척추동물은 정점조사를 한다. v7 까지는 현지조사가
회차당 컬럼 하나여서 지점별 분석이 통째로 막혀 있었다. 이 도구가 회차를
정점 5개로 펼친 예시데이터와 입력양식을 만든다.

    현지조사1  →  현지조사1_St1 … 현지조사1_St5
    현지조사2  →  현지조사2_St1 … 현지조사2_St5

문헌조사는 정점 개념이 없으므로 그대로 둔다. 나머지 6개 분류군도 손대지
않는다. 마스터DB 는 바뀌지 않으므로 v7 을 계속 쓴다.

개체수는 기존 값을 나누지 않고 **새로 생성한다.** 따라서 어류·저서무척추의
기존 수치는 모두 바뀐다.

실행:
    python -m tools.make_station_sample
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data.schema import (
    LITERATURE_COLUMNS,
    FIELD_ROUNDS,
    TAXON_SPECS,
    station_columns,
)

from .repair_datamaster import _guide, _style, is_null

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datamaster"

SRC_INPUT = DATA / "EIA_표준종목록_입력용_데이터시트_v7.xlsx"
SRC_SAMPLE = DATA / "EIA_가상데이터_v7.xlsx"
OUT_INPUT = DATA / "EIA_표준종목록_입력용_데이터시트_v8.xlsx"
OUT_SAMPLE = DATA / "EIA_가상데이터_v8.xlsx"

INPUT_COLS = ["species_id", "family_kr", "scientific_name", "korean_name", "abb", "abb2"]

# 재현성. 이 시드로 언제 돌려도 같은 데이터가 나온다.
SEED = 20260805


@dataclass(frozen=True)
class GenerationProfile:
    """분류군별 생성 파라미터.

    회차당 출현종 규모는 v7 과 비슷하게 유지한다. 정점 구조만 얹는 것이지
    분류군의 성격을 바꾸려는 것이 아니다.
    """

    taxon: str
    species_per_round: tuple[int, int]  # 회차당 출현종수 범위
    max_individuals: int  # 우점종 1종의 개체수 상한

    def draw_species_count(self, rng: random.Random) -> int:
        return rng.randint(*self.species_per_round)


PROFILES = {
    "어류": GenerationProfile("어류", (60, 90), 320),
    "저서성대형무척추동물": GenerationProfile("저서성대형무척추동물", (450, 560), 240),
}

# 정점 편중. 종마다 몇 개 정점에 나타나는지 뽑는 가중치다.
# 한 정점에만 나오는 종이 가장 많고 전 정점에 나오는 종은 드물어야
# 지점간 유사도와 군집지수가 의미 있는 값을 낸다.
STATION_SPREAD_WEIGHTS = (34, 26, 18, 13, 9)  # 1개소 … 5개소


def _draw_individuals(rng: random.Random, cap: int) -> int:
    """우편향 개체수. 소수 우점종과 다수 희소종이 생기게 한다.

    균등 분포로 뽑으면 H' 가 비현실적으로 높고 우점도가 평평해진다.
    """
    # 지수분포를 잘라 쓰면 1~2개체가 가장 흔하고 큰 값이 드물게 나온다
    value = int(rng.expovariate(1 / 12.0)) + 1
    return min(value, cap)


def generate_stations(sample: pd.DataFrame, spec, profile: GenerationProfile,
                      rng: random.Random) -> pd.DataFrame:
    """회차별 현지조사 컬럼을 정점 컬럼으로 교체한다."""
    out = sample[INPUT_COLS + LITERATURE_COLUMNS].copy()
    n_rows = len(sample)

    for round_name in FIELD_ROUNDS:
        cols = station_columns(spec, round_name)
        grid = {c: [""] * n_rows for c in cols}

        # 이 회차에 출현할 종을 새로 뽑는다
        occurring = rng.sample(range(n_rows), profile.draw_species_count(rng))
        for row in occurring:
            spread = rng.choices(range(1, len(cols) + 1), weights=STATION_SPREAD_WEIGHTS)[0]
            for col in rng.sample(cols, spread):
                grid[col][row] = str(_draw_individuals(rng, profile.max_individuals))

        for col in cols:
            out[col] = grid[col]
    return out


def _passthrough(sample: pd.DataFrame) -> pd.DataFrame:
    """정점조사를 하지 않는 분류군은 그대로 넘긴다."""
    return sample.copy()


def main() -> None:
    rng = random.Random(SEED)
    samples: dict[str, pd.DataFrame] = {}
    inputs: dict[str, pd.DataFrame] = {}

    for spec in TAXON_SPECS:
        sample = pd.read_excel(SRC_SAMPLE, sheet_name=spec.name)
        for col in sample.columns:
            sample[col] = sample[col].map(lambda v: "" if is_null(v) else str(v).strip())

        if spec.has_stations:
            profile = PROFILES[spec.name]
            out = generate_stations(sample, spec, profile, rng)
            occurred = sum(
                1 for _, r in out.iterrows()
                if any(str(r[c]).strip() for c in out.columns if c.startswith("현지조사"))
            )
            print(f"  {spec.name:<20} 정점 {spec.stations}개 · 현지 출현 {occurred:,}종")
        else:
            out = _passthrough(sample)
            print(f"  {spec.name:<20} 변경 없음")

        samples[spec.name] = out
        inputs[spec.name] = out[INPUT_COLS].copy()

    _write(OUT_SAMPLE, samples, "가상데이터")
    _write(OUT_INPUT, inputs, "입력용 데이터시트")
    for p in (OUT_SAMPLE, OUT_INPUT):
        print(f"  {p.name}  ({p.stat().st_size / 1024 / 1024:.1f} MB)")


def _write(path: Path, sheets: dict[str, pd.DataFrame], kind: str) -> None:
    guide = _guide(kind)
    extra = pd.DataFrame(
        [("정점조사", "어류·저서성대형무척추동물은 현지조사를 정점별로 기록합니다."),
         ("", "현지조사1_St1 … 현지조사1_St5 각 칸에 해당 정점의 관찰 개체수를 적습니다."),
         ("", "그 정점에서 확인되지 않았으면 빈칸으로 둡니다."),
         ("", "문헌조사는 정점 구분이 없으므로 기존과 같이 출현=1 로 적습니다.")],
        columns=["항목", "내용"])
    guide = pd.concat([guide, extra], ignore_index=True)

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        guide.to_excel(w, sheet_name="사용법", index=False)
        _style(w, "사용법", guide)
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name, index=False)
            _style(w, name, df)


if __name__ == "__main__":
    main()
