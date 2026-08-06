# EIA_report

환경영향평가 **동·식물상** 조사자료를 표준화해 관리하고, 분석 결과를 확인해
평가서에 넣을 표·그래프를 결정한 뒤, 최종적으로 한글(HWP/HWPX) 평가서 작성을
자동화하는 것을 목표로 하는 저장소입니다.

> Excel 은 원자료, Python 은 계산, Local LLM 은 문장, pyhwpx 는 한글 문서
> 조판을 담당합니다. **계산을 LLM 에 맡기지 않습니다.**

---

## 바로 실행하기 (Windows)

```
git clone https://github.com/stylax2/EIA_report.git
cd EIA_report\eia-report-automation
run.bat
```

`run.bat` 은 가상환경 생성 → 패키지 설치 → 분석 → 브라우저 열기까지 한 번에
합니다. 처음 한 번만 1~2분 걸리고, 이후에는 30초 정도면 끝납니다.

**필요한 것** — Python 3.11 이상. 설치할 때 *Add Python to PATH* 를 반드시
체크하십시오.

<details>
<summary>macOS · Linux 에서 실행하기</summary>

```bash
cd EIA_report/eia-report-automation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.analyze_web
open output/analysis_report.html      # Linux 는 xdg-open
```
</details>

실행하면 `output/analysis_report.html` 이 만들어집니다. **분석항목 선택
작업대**로, 분류군 → 분석 단위(회차·정점) → 분석항목을 고르면 표와 그래프가
나오고, 평가서에 넣기로 한 항목이 목록으로 모입니다.

---

## 구성

```
EIA_report/
├── datamaster/              원자료 엑셀
├── eia-report-automation/   코드 · 문서 · 실행 스크립트
├── doc/                     최초 기획안
└── 평가서샘플/               참고용 평가서 (HWPX · PDF)
```

### 원자료 3종

| 파일 | 역할 |
|---|---|
| `EIA_표준종목록_마스터DB_통합본_v7.xlsx` | 종 속성의 원천 — 분류체계, 법정 지위, 분류군별 속성 |
| `EIA_표준종목록_입력용_데이터시트_v8.xlsx` | 사용자 배포용 빈 입력지 |
| `EIA_가상데이터_v8.xlsx` | 파일럿 테스트용 입력 완료본 |

세 파일은 첫 컬럼 `species_id` 로 연결됩니다. **이 컬럼은 수정·삭제·정렬하면
안 됩니다.**

마스터DB 는 v8 에서 바뀌지 않아 v7 을 그대로 씁니다. 정점 컬럼이 조사자료
쪽에만 생겼기 때문입니다. v6 파일은 대조용으로 남겨 두었습니다.

### 분류군 8개

관속식물 · 포유류 · 조류 · 양서류 · 파충류 · 육상곤충류 · 어류 ·
저서성대형무척추동물

이 중 **어류와 저서성대형무척추동물은 정점조사**를 하므로 현지조사가
정점별(St.1~St.5)로 나뉘어 있습니다.

---

## 지금 되는 것

| 계층 | 상태 |
|---|---|
| 데이터 로딩·검증 (`species_id` 조인) | 구현 |
| 분석 — 공통 · 분류군 특이 · 군집지수 · 정점 | 구현 |
| 분석 선택 웹 작업대 | 구현 |
| 그래프 파일(PNG) 산출 | 미구현 |
| LLM 문장 생성 | 미구현 |
| HWPX 조판 | 미구현 |

한글 문서보다 웹페이지를 먼저 둔 이유는 수치를 사람이 검수하는 비용이 훨씬
싸기 때문입니다. 웹에서 확정한 수치를 그대로 조판으로 넘깁니다.

---

## 더 읽을 것

| 문서 | 내용 |
|---|---|
| [`eia-report-automation/README.md`](eia-report-automation/README.md) | 코드 구조와 실행 방법 |
| [`docs/analysis_items_by_taxon.md`](eia-report-automation/docs/analysis_items_by_taxon.md) | 분류군별 분석항목과 표·그래프 산출 가능성 |
| [`docs/analysis_workflow.md`](eia-report-automation/docs/analysis_workflow.md) | 원자료 구조와 분석 워크플로 |
| [`doc/eia_ecology_report_automation_plan.md`](doc/eia_ecology_report_automation_plan.md) | 최초 기획안 |
