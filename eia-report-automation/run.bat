@echo off
rem ---------------------------------------------------------------
rem  EIA 생태조사 분석 실행 (Windows)
rem
rem  이 파일을 더블클릭하거나 명령창에서 run.bat 을 실행하십시오.
rem  가상환경 생성 → 패키지 설치 → 분석 → 브라우저 열기까지 한 번에 합니다.
rem ---------------------------------------------------------------

rem 한글 출력이 깨지지 않도록 코드페이지를 UTF-8 로 맞춘다
chcp 65001 > nul
setlocal

rem 어디서 실행하든 이 파일이 있는 폴더를 기준으로 삼는다
cd /d "%~dp0"

echo.
echo ============================================
echo  EIA 생태조사 분석
echo ============================================
echo.

rem 1. Python 확인
where python > nul 2>&1
if errorlevel 1 (
    echo [오류] Python 을 찾을 수 없습니다.
    echo        Python 3.11 이상을 설치하고, 설치 시
    echo        "Add Python to PATH" 를 체크하십시오.
    echo        https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

rem 2. 가상환경 준비 (없을 때만 생성)
if not exist ".venv" (
    echo [1/4] 가상환경을 만듭니다. 처음 한 번만 시간이 걸립니다...
    python -m venv .venv
    if errorlevel 1 (
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
) else (
    echo [1/4] 가상환경을 재사용합니다.
)

call ".venv\Scripts\activate.bat"

rem 3. 패키지 설치
echo [2/4] 필요한 패키지를 확인합니다...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인하십시오.
    pause
    exit /b 1
)

rem 4. 분석 실행
echo [3/4] 분석을 실행합니다. 30초 정도 걸립니다...
echo.
python -m src.analyze_web
if errorlevel 1 (
    echo.
    echo [오류] 분석에 실패했습니다. 위 메시지를 확인하십시오.
    pause
    exit /b 1
)

rem 5. 결과 열기
echo.
echo [4/4] 브라우저에서 결과를 엽니다.
start "" "output\analysis_report.html"

echo.
echo 완료되었습니다. 창을 닫아도 됩니다.
echo.
pause
