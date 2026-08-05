# EIA 생태조사 보고서 자동화

환경영향평가 동·식물상 조사자료를 표준화해 관리하고, Python 의 결정론적
계산과 로컬 LLM 의 문장 생성을 결합해 한글(HWP/HWPX) 평가서 작성을
자동화한다.

설계 배경은 `../doc/eia_ecology_report_automation_plan.md` 에 있다.

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
│   ├── data/        로딩·검증·분류군
│   ├── analysis/    집계·생태통계
│   ├── charts/      그래프 생성
│   ├── llm/         로컬 LLM 클라이언트·프롬프트
│   ├── photos/      사진대지 구성
│   ├── hwpx/        한글 문서 조판
│   └── pipeline.py  1차 프로토타입 진입점
├── config/          모델·표 서식 설정
├── prompts/         프롬프트 템플릿
├── tests/
└── samples/
```

## 현재 상태

디렉터리 골격과 인터페이스만 잡혀 있다. 각 모듈의 함수는 아직
`NotImplementedError` 이며, 테스트는 `skip` 상태다.

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
