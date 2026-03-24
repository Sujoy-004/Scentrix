@echo off
REM ScentScape Cleanup Script

setlocal enabledelayedexpansion

cd /d "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScape – AI-Driven Fragrance Discovery & Personalization\ScentScape"

echo.
echo ==================================================
echo       ScentScape Project Cleanup
echo ==================================================
echo.

REM Delete large directories
if exist "frontend\.next" (
    echo [Deleting] frontend\.next
    rd /s /q "frontend\.next"
    echo [OK] deleted
) else (
    echo [-] frontend\.next already gone
)

if exist "frontend\node_modules" (
    echo [Deleting] frontend\node_modules (this may take a minute)
    rd /s /q "frontend\node_modules"
    echo [OK] deleted
) else (
    echo [-] frontend\node_modules already gone
)

if exist "backend\.venv" (
    echo [Deleting] backend\.venv
    rd /s /q "backend\.venv"
    echo [OK] deleted
) else (
    echo [-] backend\.venv already gone
)

if exist "backend\__pycache__" (
    echo [Deleting] backend\__pycache__
    rd /s /q "backend\__pycache__"
    echo [OK] deleted
) else (
    echo [-] backend\__pycache__ already gone
)

if exist "backend\.pytest_cache" (
    echo [Deleting] backend\.pytest_cache
    rd /s /q "backend\.pytest_cache"
    echo [OK] deleted
) else (
    echo [-] backend\.pytest_cache already gone
)

REM Delete redundant docs
if exist "PHASE_4_AUTONOMOUS_EXECUTION_SUMMARY.md" (
    echo [Deleting] PHASE_4_AUTONOMOUS_EXECUTION_SUMMARY.md
    del "PHASE_4_AUTONOMOUS_EXECUTION_SUMMARY.md"
    echo [OK] deleted
)

cd ..
if exist "PROGRESS_CHECKPOINT.md" (
    echo [Deleting] PROGRESS_CHECKPOINT.md
    del "PROGRESS_CHECKPOINT.md"
    echo [OK] deleted
)

cd ScentScape

REM Delete config files
if exist "frontend\.env.local" (
    echo [Deleting] frontend\.env.local
    del "frontend\.env.local"
    echo [OK] deleted
)

if exist "frontend\.npmrc" (
    echo [Deleting] frontend\.npmrc
    del "frontend\.npmrc"
    echo [OK] deleted
)

if exist "frontend\run-dev.bat" (
    echo [Deleting] frontend\run-dev.bat
    del "frontend\run-dev.bat"
    echo [OK] deleted
)

echo.
echo ==================================================
echo       Cleanup Complete!
echo ==================================================
echo.

pause
