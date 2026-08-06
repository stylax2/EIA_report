# EIA 생태조사 보고서 자동화

환경영향평가 동·식물상 조사자료를 표준화해 관리하고, Python 의 결정론적
계산과 로컬 LLM 의 문장 생성을 결합해 한글(HWP/HWPX) 평가서 작성을
자동화한다.

설계 배경은 `../doc/eia_ecology_report_automation_plan.md` 에 있다.

| 문서 | 내용 |
|---|---|
| `docs/analysis_items.md` | 범용 분석항목 카탈로그 (T1/T2/T3) |
| `docs/analysis_items_by_taxon.md` | 분류군별 항목과 표·그래프 산출 가능성 판정 |
| `docs/analysis_workflow.md` | 원자료 구조와 분석 워크플로 |
| `docs/architecture.md` | 계층 경계 |
| `docs/data_schema.md` | 데이터 스키마 |
| `docs/hwpx_rules.md` | 한글 조판 규칙 |

## 원칙

> Excel 은 원자료, Python 은 계산, Local LLM 은 문장, pyhwpx 는 한글 문서
> 조판을 담당한다.

LLM 에게 계산을 맡기지 않는다. 수치와 목록은 Python 이 확정하고, LLM 은
확정된 결과를 자연어로 표현한다.

## 구조

```
eia-report-automation/
├── run.bat          Windows 실행 스크립트 (더블클릭)
├── docs/            설계 문서
├── src/
│   ├── data/        schema(분류군 사양·컬럼) · loader(조인·파싱)
│   ├── analysis/    scope(분석 단위) · species_summary · diversity
│   │                legal_status · taxon_specific · stations(정점)
│   │                item_catalog(항목 판정) · runner(집약)
│   ├── report_web/  payload(렌더 서술자) · builder(HTML·SVG)
│   ├── charts/      그래프 파일 생성 (미구현)
│   ├── llm/         로컬 LLM 클라이언트·프롬프트 (미구현)
│   ├── photos/      사진대지 구성 (미구현)
│   ├── hwpx/        한글 문서 조판 (미구현)
│   ├── analyze_web.py  분석 → 웹페이지 진입점
│   └── pipeline.py  1차 프로토타입 진입점
├── config/          모델·표 서식 설정
├── prompts/         프롬프트 템플릿
├── tools/           repair_datamaster · make_station_sample
├── tests/
└── samples/
```

## 실행

**모든 명령은 이 폴더(`eia-report-automation/`)에서 실행한다.** 모듈 경로가
여기를 기준으로 잡히기 때문이다.

Windows 는 `run.bat` 을 더블클릭하면 가상환경 생성부터 브라우저 열기까지
한 번에 끝난다. 직접 실행하려면 아래와 같다.

```bash
cd eia-report-automation
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m src.analyze_web              # 분석 → output/analysis_report.html
pytest -q                              # 테스트
```

원자료를 다시 만들어야 할 때만 쓰는 명령이다. 결과물이 이미 저장소에 있으므로
평소에는 실행할 필요가 없다.

```bash
python -m tools.repair_datamaster      # 마스터DB 정비        (v6 → v7)
python -m tools.make_station_sample    # 정점조사 데이터 생성  (v7 → v8)
```

두 도구 모두 시드를 고정하거나 결정론적으로 동작하므로, 언제 돌려도 같은
결과가 나온다.

## 현재 상태

분석 계층과 웹 작업대까지 동작한다. HWPX 조판 계층은 아직 인터페이스만 있다.

| 계층 | 상태 |
|---|---|
| 데이터 로딩·검증 (`species_id` 조인) | 구현 |
| T1 공통 분석 | 구현 |
| T2 분류군 특이 분석 | 구현 |
| T3 군집지수 | 구현 |
| 정점 분석 (지점별 종수·지수·유사도) | 구현 |
| 분석 선택 웹 작업대 | 구현 |
| 그래프 파일(PNG) 산출 | 미구현 |
| LLM 문장 생성 | 미구현 |
| HWPX 조판 | 미구현 |

원자료 3종은 `species_id` 로 연결된다. 입력지·예시데이터의 첫 컬럼이
조인 키이며 수정·삭제·정렬하면 안 된다.

한글 문서보다 웹페이지를 먼저 두는 이유는 수치 검수 비용이 훨씬 싸기
때문이다. 웹에서 확정한 수치를 그대로 조판으로 넘긴다.

### 웹 작업대

분류군 → 분석 단위 → 분석항목을 고르면 표와 그래프가 나오고, 평가서에
넣기로 한 항목이 채택 목록으로 모인다.

**분석 단위**는 회차·정점 조합이다. 임의 조합을 다 계산하면 정점 5개일 때
4,095가지가 되므로, 업무상 의미 있는 단위만 열거한다(정점 분류군 17개,
나머지 7개로 총 76개).

단위에 따라 항목 가용성이 바뀐다. 문헌 단위는 개체수가 없어 군집지수를 낼
수 없고, 정점 하나만 고르면 지점간 비교를 할 수 없다. **낼 수 없는 항목은
숨기지 않고 사유와 함께 비활성으로 표시한다.**

그래프는 외부 라이브러리 없이 인라인 SVG 로 그린다. 화면은 사전 계산된 값을
고르고 그릴 뿐 지수를 계산하지 않는다.

## 1차 구현 범위

분류군 하나를 대상으로 아래 흐름을 끝까지 연결하는 것이 목표다.

```
Excel 종목록 → 출현종 체크 → 종수 계산 → 종목록 표 생성
→ 그래프 생성 → LLM 문장 생성 → HWPX 지정 위치 삽입 → 저장
```

사진대지, 다른 분류군, 복잡한 통계는 이 경로가 안정된 뒤에 붙인다.

## 실행 환경

- **Python 3.11 이상.** 그 이하에서는 타입 표기(`str | None`)가 동작하지 않는다.
- 지금 필요한 패키지는 `pandas` 와 `openpyxl` 뿐이다. 아직 쓰지 않는 계층의
  의존성(matplotlib · PyYAML · requests · pyhwpx)은 `requirements.txt` 에
  주석으로 남겨 두었고, 해당 계층을 구현할 때 해제한다.
- pyhwpx 와 한글 프로그램은 Windows 에서만 동작한다. 데이터·분석 계층은
  플랫폼과 무관하게 테스트할 수 있도록 조판 계층과 분리했다.
- 로컬 LLM 런타임(Ollama)은 문장 생성 계층을 붙일 때 필요하다. 모델명은
  `config/model.yaml` 에서 관리한다.
