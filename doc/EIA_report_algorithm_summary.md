> **[이력용] 이 문서는 더 이상 설계 근거로 참고하지 않습니다.**
> 과거 시스템의 요약본으로 기록만 남겨 둡니다.

# EIA_report 첨부용 — 데이터 정리·시각화 알고리즘 기술 요약

## 0. 문서 목적

환경영향평가서(EIA) 자동화 시스템의 웹 표출 작업은 기존에 본 프로젝트(`EAI_flora_local`)에 연결된 백엔드(FastAPI)와 프론트엔드(Next.js)로 구현되어 있다.

새로운 기술을 적용해 시스템을 확장하는 경우에도, **데이터 정리(집계·매칭·위계화·면적 보정)와 시각화(차트·표 렌더링)를 담당하는 핵심 로직은 신규로 개발하지 않고 본 프로젝트에 이미 연결된 로직을 그대로 사용**한다. 이 문서는 그 대상이 되는 알고리즘의 기술적 특징을 정리해, EIA_report에 첨부할 근거 자료로 전달하기 위해 작성했다.

## 1. 대상 범위

`backend/services/` 아래에서 데이터 정리·시각화에 직접 관여하는 모듈과 이를 소비하는 프론트엔드 차트 컴포넌트를 대상으로 한다. 종 판별용 AI 탐지 모델(조류·양서류·카메라트랩)과 원문 PDF 파싱 모듈은 별도 영역이므로 이 문서에서 제외했다.

| 영역 | 파일 | 역할 |
|---|---|---|
| 집계·분석 엔진 | `analyzer.py` | 출현종 집계표, 귀화율·도시화지수, 보전종 요약/목록, 라운키에르 생활형 스펙트럼 |
| 위계 구조 생성 | `hierarchical.py` | 문→강→목→과→종 계층 목록 생성 |
| 종 매칭 | `species_matcher.py` | 조사 데이터를 마스터 DB에 3단계 매칭 |
| 학명 서식 파싱 | `taxon_parser.py` | 학명을 이탤릭/정자체 세그먼트로 분해 |
| 공간 분석 | `spatial_analyzer.py`, `geometry_validator.py` | 현존식생도 면적 산출 파이프라인 |
| 비율·면적 보정 | `ratio_adjuster.py` | 최대잉여법 기반 비율 100% 보정 |
| 엑셀 출력 | `excel_veg_exporter.py` | 분석 결과 서식 엑셀 생성 |
| 세션 캐시 | `veg_file_cache.py` | 업로드 GeoDataFrame·분석 결과 메모리 보관 |
| 보고서 자동 조립 | `report_automation/*` | 세션 데이터 → HWPX 표/서술문/이미지 자동 채움 |
| 시각화 | `frontend/src/components/charts/LifeFormChart.tsx`, `lib/store.ts`, `lib/clipboard-utils.ts` 외 | 분석 결과를 Recharts 기반 차트로 렌더링, 상태 관리, HWP 붙여넣기용 내보내기 |

## 2. 데이터 정리 로직

### 2.1 종 매칭 — `species_matcher.py`

조사 원본 데이터(학명·국명)를 마스터 종 DB와 연결하는 3단계 매칭 알고리즘이다.

1. **학명 정확 매칭**: 명명자를 제거(`strip_author`)한 학명을 소문자 인덱스와 대조
2. **국명 정확 매칭**: 1단계 실패 시 국명 인덱스와 대조
3. **Fuzzy 매칭**: `difflib.SequenceMatcher` 기반 유사도 계산, 임계값 0.90 이상만 채택

각 결과에는 매칭 유형(`exact_sci`/`exact_kor`/`fuzzy`/`unmatched`)과 신뢰도(confidence)를 함께 반환해, 자동 매칭 결과를 사람이 검수할 수 있는 구조로 설계했다.

### 2.2 집계·분석 — `analyzer.py`

pandas 기반 `Analyzer` 클래스가 하나의 병합 DataFrame(조사 데이터 + 마스터 DB)을 입력받아 여러 관점의 집계표를 산출한다.

- **분류군별 집계표**: 양치식물문/나자식물문/피자식물문 등 사전 정의된 8개 행 기준으로 과·속·종/변종/아종/품종 수를 집계
- **귀화율·도시화지수**: 귀화식물 출현종수를 전국 귀화식물 기준종수(266종) 대비 백분율로 산출
- **보전종 요약/목록**: 멸종위기야생생물·희귀식물·특산식물·귀화식물·생태계교란식물·식물구계학적특정종을 등급별로 breakdown
- **비고 자동 생성**(`generate_note`): 멸종위기 → 희귀식물 → 식물구계 → 귀화 → 생태계교란 순의 우선순위로 종별 비고란 문자열을 결정론적으로 조합
- **라운키에르 생활형 스펙트럼**: 조사 컬럼별 생활형(M/N/E/Ch/H/G/HH/Th) 분포를 계수하고 백분율 환산, 국내 표준 스펙트럼과 비교 가능한 형태로 반환

### 2.3 위계 구조 생성 — `hierarchical.py`

출현종 DataFrame을 문(phylum)→강(class)→목(order)→과(family)→종(species) 순으로 정렬하고, 상위 분류가 바뀌는 지점마다 헤더 행을 삽입해 보고서 목록 형태의 트리 구조를 만든다. 국명·학명 병기 규칙, 조사 컬럼별 개체수 표시 여부까지 함께 처리한다.

### 2.4 학명 서식 파싱 — `taxon_parser.py`

국제 명명 규약(ICN/ICZN)의 표기 관례를 코드화한 상태 기계(state machine)다. 속명·종소명·종하위소명은 이탤릭, 명명자·계급 약어·상위분류군 접미사(-aceae, -idae 등)는 정자체로 자동 분류해 `(텍스트, is_italic)` 세그먼트를 반환한다. HWPX 문서용과 웹 렌더링용(`parse_taxon_html`) 출력을 동일 로직에서 파생시켜, 보고서 문서와 화면 표시 간 서식 불일치를 원천적으로 방지한다.

## 3. 공간 데이터 분석 로직

### 3.1 파이프라인 — `spatial_analyzer.py`

현존식생도(폴리곤 GIS 데이터)와 사업지구 경계를 입력받아 다음 순서로 처리한다.

1. 지오메트리 검증·자동 수정 (`geometry_validator.py`)
2. 라인 경계 → 폴리곤 변환 (필요 시)
3. 좌표계(CRS) 통일
4. 식생보전등급 표기 정규화(로마 숫자 등)
5. 사업지구 경계로 클립(clip) 및 슬리버 폴리곤 제거
6. 식생유형별·등급별 면적 집계 및 비율 보정
7. 등급별 디졸브(dissolve) 결과 생성(옵션)

geopandas/shapely 기반이며, 각 단계에서 발생하는 이슈(빈 지오메트리, 무효 지오메트리, 중복, 클립 결과 없음 등)를 심각도(INFO/WARNING/ERROR)와 함께 구조화된 리스트로 반환해 검수 가능성을 확보했다.

### 3.2 비율 보정 — `ratio_adjuster.py`

면적 비율의 합이 반올림 오차로 100%를 벗어나지 않도록 **최대잉여법(Largest Remainder Method)**을 적용한다. 또한 GIS 계산 면적과 토지이용계획상 공식 면적이 다를 경우, 비례 배분(scale factor)으로 개별 식생유형 면적을 공식 총면적에 맞춰 재조정한다.

## 4. 보고서 자동 조립 로직 — `report_automation/`

세션 캐시에 보관된 분석 결과를 HWPX 보고서 산출물로 연결하는 계층이다.

- **facts_builder.py**: `Analyzer`/`build_hierarchical_list` 결과를 표 단위 팩트 패키지(`ReportFactsPackage`)로 재구성
- **narrative_builder.py**: LLM 없이 팩트로부터 표준 EIA 서술문을 결정론적으로 생성(예: "조사 결과 총 O목 O과 O종의 관속식물이 확인되었다")
- **table_renderer.py**: lxml로 HWPX 표 XML(OWPML)을 직접 조작해 병합 셀(ghost cell)을 보존하면서 표 내용을 채움
- **image_matcher.py / action_planner.py**: 업로드 이미지·표·문단 각각에 대해 자동 치환(AUTO_REPLACE)·수동 필요(MANUAL_REQUIRED)·서술 채움(NARRATIVE_FILL)·원본 유지(KEEP_ORIGINAL) 중 하나의 액션을 캡션 별칭 매칭 규칙으로 결정

## 5. 산출물 생성 로직

- **excel_veg_exporter.py**: openpyxl로 식생유형별/등급별 표와 분석 요약 시트를 서식(테두리·헤더 색상·병합 셀·숫자 포맷)까지 포함해 생성
- **veg_file_cache.py**: 업로드된 GeoDataFrame과 분석 결과를 스레드 안전한 메모리 캐시에 보관해, 동일 세션 내 반복 분석·재출력 시 재계산을 방지

## 6. 시각화 로직 — 프론트엔드

### 6.1 기술 스택

- Next.js 16(App Router) + React 19 — `frontend/AGENTS.md`에 명시된 대로 이 버전은 이전 Next.js와 API·컨벤션이 다른 브레이킹 체인지를 포함하므로, 새 기술을 이 위에 얹을 때는 `node_modules/next/dist/docs/`의 최신 가이드와 지원 중단 공지를 우선 확인해야 한다. 즉 "새로운 기술 적용"이 프론트엔드 프레임워크 자체를 건드리는 경우, 본 프로젝트가 이미 검증해 둔 Next.js 16 대응 방식을 따르는 것이 안전하다.
- Recharts 3.8 — 차트 렌더링(BarChart 기반)
- Zustand — 세션/조사 컬럼 등 화면 간 공유 상태 관리(`useFloraStore`), 별도 영속화 없이 세션 단위로 초기화
- `@tanstack/react-table` — 표 형태 데이터 그리드
- `html2canvas` — 화면에 그려진 차트를 PNG로 캡처
- `xlsx` — 클라이언트 측 엑셀 파싱(업로드 원본 미리보기 등)

### 6.2 데이터 흐름 — "얇은 렌더링 계층"

`frontend/src/components/charts/LifeFormChart.tsx`를 비롯한 차트 컴포넌트는 자체적으로 통계를 계산하지 않는다. `RaunkiaerTab.tsx` 같은 탭 컴포넌트가 `api.raunkiaer(sessionId, cols)` 형태로 2장의 백엔드 분석 API(`analyzer.py`의 `get_raunkiaer_by_columns` 등)를 호출하면, 응답 JSON(스펙트럼 카운트·백분율·비교 기준값)을 그대로 `LifeFormChart`의 props로 전달해 그리는 구조다.

```
백엔드 Analyzer (집계·비율 계산)
   → REST API 응답(JSON)
   → Zustand 스토어(sessionId, surveyColumns)
   → 탭 컴포넌트(RaunkiaerTab / SummaryTableTab 등)가 상태로 보관
   → 차트 컴포넌트(LifeFormChart 등)는 값을 그대로 렌더링
```

계산 로직과 표현 로직을 분리해 둔 덕분에, 화면에 새 시각화 방식(다른 차트 라이브러리, 대시보드 등)을 추가하더라도 계산 결과를 재사용하기만 하면 되고 백엔드 분석 로직을 다시 구현할 필요가 없다.

### 6.3 사용자 조정 가능한 시각화 옵션

`RaunkiaerTab.tsx` / `SummaryTableTab.tsx` 등 탭 컴포넌트가 차트 설정 UI를 감싸고 있으며, `LifeFormChart`는 다음 옵션을 props로 받아 순수하게 렌더링만 수행한다.

- 크기: 높이(200~700px), 너비(자동/고정 400~1400px)
- 축 제목: X/Y축 라벨 사용자 입력
- 색상: 컬러 팔레트 / 흑백(인쇄용, 8단계 명도 균등 분포) / 사용자 지정(컬럼별 색상 피커)
- 값 라벨: 없음 / 비율(%) / 개체수(count) 전환, 라벨 폰트 크기 조절
- 조사 컬럼별 계열과 비교 기준(전국 일반 식물상 스펙트럼, 라운키에르 표준 등) 계열을 동일 좌표축에 중첩 표시

### 6.4 보고서 연계 — HWP 붙여넣기용 내보내기

`clipboard-utils.ts`는 시각화 결과를 환경영향평가서 문서(HWP) 작성 과정에 바로 연결하기 위한 두 가지 클립보드 복사 기능을 제공한다.

- `copyTableHtml`: 표 DOM을 클론해 배경색을 제거한 뒤 `text/html`로 클립보드에 기록 — 한글(HWP) 등에 붙여넣을 때 깨끗한 표로 표시
- `copyChartAsImage`: `html2canvas`로 차트 DOM을 PNG로 캡처해 `image/png`로 클립보드에 기록

이 두 기능 덕분에 화면에서 만든 차트·표를 별도 저장 없이 곧바로 보고서 문서에 붙여 넣을 수 있어, 시각화 계층이 웹 화면 표출뿐 아니라 EIA_report 작성 워크플로우와도 직접 연결되어 있다.

### 6.5 빌드 대상 분기와 재사용 범위

`next.config.ts`는 동일한 프론트엔드 코드베이스를 두 가지 빌드로 분기한다.

- **로컬(전체 기능)**: `/api/*` 요청을 로컬 백엔드(`localhost:8000`)로 프록시. 시각화가 실제 분석 API 결과를 그린다.
- **데모(정적 export)**: 백엔드를 호출하지 않는 완전 정적 빌드(`output: "export"`). Vercel 배포 시 `NEXT_PUBLIC_API_URL`을 비워 외부 백엔드 호출을 원천 차단한다.

이 분기 구조 자체는 코드 재사용 범위를 명확히 보여준다 — 시각화 컴포넌트(`components/charts/*`)와 상태 관리(`lib/store.ts`)는 두 빌드에서 동일하게 재사용되고, 차이는 오직 데이터를 어디서 가져오는지(API 호출 여부)에 있다. 새로운 기술을 적용해 시스템을 확장할 때도 이 경계— "계산은 백엔드, 표현은 프론트엔드 차트 컴포넌트, 데이터 소스만 교체 가능" — 를 유지하는 것이 기존 로직 재사용의 핵심이다.

## 7. 요약

| 구분 | 내용 |
|---|---|
| 데이터 정리 | 3단계 종 매칭, pandas 기반 집계/보전종 분석, 위계 구조 생성, 학명 서식 파싱 |
| 공간 분석 | geopandas/shapely 기반 지오메트리 검증·클립·면적 집계, 최대잉여법 비율 보정 |
| 보고서 조립 | 세션 팩트 → 결정론적 서술문 → HWPX 표/이미지 자동 채움 |
| 시각화 | Next.js 16 + React 19 + Recharts 3.8 기반. 백엔드 분석 결과를 그대로 소비하는 얇은 렌더링 계층, Zustand로 세션 상태 공유, 차트/표를 HWP 붙여넣기용 클립보드로 내보내기 지원 |

위 로직은 모두 본 프로젝트 백엔드(`backend/services/`)와 프론트엔드(`frontend/src/components/charts/`)에 이미 구현·연결되어 있다. 새로운 기술로 시스템을 확장하더라도 이 데이터 정리·시각화 로직은 신규 구현 없이 그대로 재사용하는 것을 전제로 한다.
