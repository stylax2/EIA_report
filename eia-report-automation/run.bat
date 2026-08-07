@echo off
rem ---------------------------------------------------------------
rem  EIA 생태조사 분석 실행 (Windows)
rem
rem  이 파일을 더블클릭하거나 명령창에서 run.bat 을 실행하십시오.
rem  가상환경 생성 → 패키지 설치 → 분석 → 브라우저 열기까지 한 번에 합니다.
rem
rem  아나콘다(Anaconda/Miniconda)는 설치해도 PATH 에 등록되지 않는 경우가
rem  많습니다. 그래서 PATH 뿐 아니라 활성 conda 환경·설치 경로·레지스트리
rem  까지 뒤져서 파이썬을 찾습니다.
rem ---------------------------------------------------------------

rem 한글 출력이 깨지지 않도록 코드페이지를 UTF-8 로 맞춘다
chcp 65001 > nul
setlocal

rem 어디서 실행하든 이 파일이 있는 폴더를 기준으로 삼는다
cd /d "%~dp0"

set "RUNBAT_VERSION=2026-08-07.2 (anaconda-detect+diag)"

echo.
echo ============================================
echo  EIA 생태조사 분석
echo  run.bat %RUNBAT_VERSION%
echo ============================================
echo.
echo  ^(이 줄에 버전이 안 보이면 예전 run.bat 입니다.
echo    git pull origin main 로 최신을 받으십시오.^)

rem 어느 커밋을 돌리는지 보여준다. git 이 없으면 조용히 넘어간다.
for /f "delims=" %%c in ('git -C "%~dp0.." log -1 --format^=" 커밋 %%h  %%ad  %%s" --date^=short 2^>nul') do echo %%c
echo.

set "PYDIR="
set "PYEXE="

rem ── 0) 사용자가 직접 지정한 경우 ───────────────────────────────
rem     자동 탐색이 모두 실패할 때의 확실한 탈출구다.
rem       set "EIA_PYTHON=C:\Users\사용자명\anaconda3\python.exe"
if defined EIA_PYTHON (
    if exist "%EIA_PYTHON%" (
        for %%F in ("%EIA_PYTHON%") do set "PYDIR=%%~dpF"
        goto :trimdir
    )
    echo [경고] EIA_PYTHON 에 지정한 경로가 없습니다: %EIA_PYTHON%
    echo.
)

rem ── 1) PATH 에 python 이 있는 경우 ──────────────────────────────
rem     Anaconda Prompt 로 실행했거나 conda 환경이 활성화된 상태
where python > nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python"
    goto :found
)

rem ── 2) 활성화된 conda 환경 ─────────────────────────────────────
if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\python.exe" (
        set "PYDIR=%CONDA_PREFIX%"
        goto :usedir
    )
)

rem ── 3) conda 명령 위치에서 역추적 ──────────────────────────────
rem     conda.exe 는 보통 <설치폴더>\Scripts\ 또는 <설치폴더>\condabin\ 에 있다
for /f "delims=" %%i in ('where conda 2^>nul') do (
    if not defined PYDIR (
        for %%p in ("%%~dpi..") do (
            if exist "%%~fp\python.exe" set "PYDIR=%%~fp"
        )
    )
)
if defined PYDIR goto :usedir

rem ── 4) 흔한 설치 경로 탐색 ─────────────────────────────────────
for %%D in (
  "%USERPROFILE%\anaconda3"
  "%USERPROFILE%\Anaconda3"
  "%USERPROFILE%\miniconda3"
  "%USERPROFILE%\Miniconda3"
  "%LOCALAPPDATA%\anaconda3"
  "%LOCALAPPDATA%\Continuum\anaconda3"
  "%ProgramData%\anaconda3"
  "%ProgramData%\Anaconda3"
  "%ProgramData%\miniconda3"
  "%ProgramData%\Miniconda3"
  "C:\Anaconda3"
  "C:\Miniconda3"
) do (
    if not defined PYDIR if exist "%%~D\python.exe" set "PYDIR=%%~D"
)
if defined PYDIR goto :usedir

rem ── 5) 레지스트리 조회 ─────────────────────────────────────────
for %%K in (
  "HKCU\Software\Python\ContinuumAnalytics\Anaconda3-64\InstallPath"
  "HKLM\Software\Python\ContinuumAnalytics\Anaconda3-64\InstallPath"
  "HKCU\Software\Python\PythonCore\3.12\InstallPath"
  "HKCU\Software\Python\PythonCore\3.11\InstallPath"
) do (
    if not defined PYDIR (
        for /f "tokens=2,*" %%a in ('reg query %%K /ve 2^>nul') do (
            if exist "%%b\python.exe" set "PYDIR=%%b"
        )
    )
)
if defined PYDIR goto :usedir

rem ── 6) py 런처 ─────────────────────────────────────────────────
where py > nul 2>&1
if not errorlevel 1 (
    set "PYEXE=py -3"
    goto :found
)

goto :notfound

rem 경로 끝의 백슬래시를 떼어 낸다 (%%~dpF 는 항상 붙여서 준다)
:trimdir
if "%PYDIR:~-1%"=="\" set "PYDIR=%PYDIR:~0,-1%"

rem ── 찾은 설치 폴더를 이 창에서만 PATH 에 올린다 ────────────────
:usedir
rem 아나콘다는 Scripts 와 Library\bin 이 PATH 에 있어야 numpy·pandas 의
rem DLL 을 찾는다. python.exe 만 직접 불러 쓰면 import 에서 실패한다.
set "PATH=%PYDIR%;%PYDIR%\Scripts;%PYDIR%\Library\bin;%PYDIR%\Library\usr\bin;%PYDIR%\Library\mingw-w64\bin;%PATH%"
set "PYEXE=python"
echo [0/4] 파이썬을 찾았습니다: %PYDIR%
echo.

:found
rem ── 버전 확인 (3.11 이상) ──────────────────────────────────────
for /f "delims=" %%v in ('%PYEXE% -c "import sys;print(sys.version.split()[0])" 2^>nul') do set "PYVER=%%v"
if not defined PYVER (
    echo [오류] 파이썬을 실행할 수 없습니다.
    echo.
    pause
    exit /b 1
)

%PYEXE% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" > nul 2>&1
if errorlevel 1 (
    echo [오류] 이 프로그램은 Python 3.11 이상이 필요합니다.
    echo        현재 버전: %PYVER%
    echo.
    echo        아나콘다를 쓰신다면 Anaconda Prompt 에서 아래처럼
    echo        3.11 환경을 하나 만든 뒤 다시 실행하십시오.
    echo.
    echo            conda create -n eia python=3.11
    echo            conda activate eia
    echo            run.bat
    echo.
    pause
    exit /b 1
)

rem ── 1. 가상환경 준비 (없을 때만 생성) ──────────────────────────
if not exist ".venv" (
    echo [1/4] 가상환경을 만듭니다. 처음 한 번만 시간이 걸립니다...
    %PYEXE% -m venv .venv
    if errorlevel 1 (
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
) else (
    echo [1/4] 가상환경을 재사용합니다.
)

call ".venv\Scripts\activate.bat"

rem ── 2. 패키지 설치 ─────────────────────────────────────────────
echo [2/4] 필요한 패키지를 확인합니다... ^(Python %PYVER%^)
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인하십시오.
    pause
    exit /b 1
)

rem ── 3. 분석 실행 ───────────────────────────────────────────────
echo [3/4] 분석을 실행합니다. 30초 정도 걸립니다...
echo.
python -m src.analyze_web
if errorlevel 1 (
    echo.
    echo [오류] 분석에 실패했습니다. 위 메시지를 확인하십시오.
    pause
    exit /b 1
)

rem ── 4. 결과 열기 ───────────────────────────────────────────────
echo.
echo [4/4] 브라우저에서 결과를 엽니다.
start "" "output\analysis_report.html"

echo.
echo 완료되었습니다. 창을 닫아도 됩니다.
echo.
pause
exit /b 0

rem ── 파이썬을 끝내 못 찾은 경우 ─────────────────────────────────
:notfound
echo [오류] 파이썬을 찾을 수 없습니다.
echo.
echo ---------- 진단 정보 (이 부분을 그대로 알려주십시오) ----------
echo run.bat 버전 : %RUNBAT_VERSION%
echo 실행 폴더    : %~dp0
echo CONDA_PREFIX : [%CONDA_PREFIX%]
echo USERPROFILE  : [%USERPROFILE%]
echo.
echo [1] where python
where python 2>&1
echo [2] where conda
where conda 2>&1
echo [3] where py
where py 2>&1
echo [4] 설치 경로 점검
for %%D in (
  "%USERPROFILE%\anaconda3"
  "%USERPROFILE%\Anaconda3"
  "%USERPROFILE%\miniconda3"
  "%USERPROFILE%\Miniconda3"
  "%LOCALAPPDATA%\anaconda3"
  "%LOCALAPPDATA%\Continuum\anaconda3"
  "%ProgramData%\anaconda3"
  "%ProgramData%\Anaconda3"
  "%ProgramData%\miniconda3"
  "%ProgramData%\Miniconda3"
  "C:\Anaconda3"
  "C:\Miniconda3"
) do (
    if exist "%%~D\python.exe" (echo   O  %%~D) else (echo   -  %%~D)
)
echo [5] 레지스트리
reg query "HKCU\Software\Python\ContinuumAnalytics" /s /f InstallPath 2^>nul | findstr /i "InstallPath REG_SZ"
reg query "HKLM\Software\Python\ContinuumAnalytics" /s /f InstallPath 2^>nul | findstr /i "InstallPath REG_SZ"
echo ---------------------------------------------------------------
echo.
echo   아나콘다(Anaconda/Miniconda)가 설치되어 있다면, 설치 위치가
echo   일반적이지 않아 자동 탐색에 걸리지 않은 것입니다.
echo   아래 두 방법 중 하나를 쓰십시오.
echo.
echo   [방법 1] Anaconda Prompt 에서 실행 ^(가장 간단^)
echo       시작 메뉴 - Anaconda Prompt 를 열고
echo           cd /d "%~dp0"
echo           run.bat
echo.
echo   [방법 2] python.exe 를 직접 지정 ^(가장 확실^)
echo       set "EIA_PYTHON=C:\Users\사용자명\anaconda3\python.exe"
echo       run.bat
echo.
echo   [방법 3] 설치 폴더를 직접 지정
echo       아나콘다 설치 폴더^(python.exe 가 있는 곳^)를 확인한 뒤
echo       명령창에서 아래처럼 실행하십시오.
echo           set "CONDA_PREFIX=C:\Users\사용자명\anaconda3"
echo           run.bat
echo.
echo   아나콘다가 없다면 Python 3.11 이상을 설치하고
echo   설치 시 "Add Python to PATH" 를 체크하십시오.
echo       https://www.python.org/downloads/
echo.
pause
exit /b 1
