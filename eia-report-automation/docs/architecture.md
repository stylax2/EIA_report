# 아키텍처

기획안 `doc/eia_ecology_report_automation_plan.md` 의 설계를 코드 구조로
옮긴 문서다. 상세 배경은 기획안을 따르고, 이 문서는 계층 간 경계만 다룬다.

## 계층

| 계층 | 위치 | 책임 |
|---|---|---|
| 원자료 | `datamaster/` | Excel 조사자료, 표준종목록 마스터 DB |
| 데이터 | `src/data/` | 로딩, 검증, 분류군·종명 정규화 |
| 분석 | `src/analysis/` | 종목록·종수 집계, 생태통계 지수 |
| 그래프 | `src/charts/` | 평가서용 그래프 생성 |
| 언어 | `src/llm/` | 확정된 사실의 자연어 서술 |
| 사진 | `src/photos/` | 사진 폴더 탐색, 사진대지 구성 |
| 조판 | `src/hwpx/` | pyhwpx 로 표·문장·이미지 배치 |

## 경계 규칙

1. **계산은 Python 이 확정한다.** LLM 은 종수·다양도·보호종 판정을 직접
   계산하지 않는다. `src/analysis/` 의 결과만 `src/llm/` 으로 흐른다.
2. **LLM 입력은 구조화 페이로드로 제한한다.** Excel 원본을 통째로 넘기지
   않고 `SurveyFacts` 형태로 전달한다.
3. **삽입 위치는 결정론적으로 찾는다.** `{{TAXON_SLOT}}` 플레이스홀더를
   문자열로 탐색하며, 문서 해석으로 위치를 추측하지 않는다.
4. **서식은 설정으로 관리한다.** 표 스타일은 `config/report_styles.yaml`
   에만 정의하고 코드는 스타일 이름으로 참조한다.
5. **데이터와 조판을 분리한다.** 표 분할은 순수 데이터 연산이고, 실제
   페이지 배치는 `src/hwpx/tables.py` 가 맡는다.

## 데이터 흐름

```
Excel → loader → validator → species_summary / diversity
                                   ↓                ↓
                            chart_generator     SurveyFacts
                                   ↓                ↓
                                   └──→ hwpx ←── LocalLLMClient
                                          ↓
                                    출력 평가서
```

## 파일럿 단계의 예외

기획안 11.1 은 실제 조사자료와 대용량 평가서를 GitHub 에 두지 않도록
정하고 있으나, 파일럿 기간에는 `datamaster/` 의 Excel 과 `평가서샘플/` 의
HWPX 를 저장소에 유지한다. 실제 운용 단계로 넘어갈 때 별도 저장소로
옮긴다.
