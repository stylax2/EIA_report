# EIA 생태조사 보고서 자동화

환경영향평가 동·식물상 조사자료를 표준화해 관리하고, Python 의 결정론적
계산과 로컬 LLM 의 문장 생성을 결합해 한글(HWP/HWPX) 평가서 작성을
자동화한다.

설계 배경은 `../doc/eia_ecology_report_automation_plan.md` 에 있다.

| 문서 | 내용 |
|---|---|
| `docs/analysis_items.md` | 범용 분석항목 카탈로그 (T1/T2/T3) |
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
├── docs/            설계 문서
├── src/
│   ├── data/        스키마·로딩·검증
│   ├── analysis/    T1/T2/T3 분석과 결과 집약
│   ├── report_web/  분석 결과 웹페이지
│   ├── charts/      그래프 생성
│   ├── llm/         로컬 LLM 클라이언트·프롬프트
│   ├── photos/      사진대지 구성
│   ├── hwpx/        한글 문서 조판
│   ├── analyze_web.py  분석 → 웹페이지 진입점
│   └── pipeline.py  1차 프로토타입 진입점
├── config/          모델·표 서식 설정
├── prompts/         프롬프트 템플릿
├── tests/
└── samples/
```

## 현재 상태

분석 계층까지 동작한다. 가상데이터 8개 분류군을 읽어 분석하고 결과를
웹페이지로 낸다. HWPX 조판 계층은 아직 인터페이스만 있다.

```bash
python -m src.analyze_web          # → output/analysis_report.html
```

| 계층 | 상태 |
|---|---|
| 데이터 로딩·검증 | 구현 |
| T1 공통 분석 | 구현 |
| T2 분류군 특이 분석 | 구현 |
| T3 군집지수 | 구현 |
| 웹페이지 표출 | 구현 |
| 그래프 생성 | 미구현 |
| HWPX 조판 | 미구현 |

한글 문서보다 웹페이지를 먼저 두는 이유는 수치 검수 비용이 훨씬 싸기
때문이다. 웹에서 확정한 수치를 그대로 조판으로 넘긴다.

## 1차 구현 범위

분류군 하나를 대상으로 아래 흐름을 끝까지 연결하는 것이 목표다.

```
Excel 종목록 → 출현종 체크 → 종수 계산 → 종목록 표 생성
→ 그래프 생성 → LLM 문장 생성 → HWPX 지정 위치 삽입 → 저장
```

사진대지, 다른 분류군, 복잡한 통계는 이 경로가 안정된 뒤에 붙인다.

## 실행 환경

- Python 3.11 이상
- 로컬 LLM 런타임(Ollama). 모델은 `config/model.yaml` 에서 지정한다.
- pyhwpx 와 한글 프로그램은 Windows 환경에서만 동작한다. 데이터·분석
  계층은 플랫폼과 무관하게 테스트할 수 있도록 조판 계층과 분리했다.

```bash
pip install -r requirements.txt
pytest
```
