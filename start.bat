@echo off
chcp 65001 >nul
title TutorFlow - AI 编程导师

:: ── 配置 ──
set PYTHON=C:\Python314\python.exe
set PORT=8501

echo.
echo ╔══════════════════════════════════════╗
echo ║   🎓 TutorFlow - AI 编程导师        ║
echo ╚══════════════════════════════════════╝
echo.

:: ── 检查 Python ──
if not exist "%PYTHON%" (
    echo ❌ 找不到 Python: %PYTHON%
    echo    请修改 start.bat 中的 PYTHON 路径
    pause
    exit /b 1
)

:: ── 自动安装依赖 ──
echo 🔍 检查依赖...
%PYTHON% -c "import streamlit, openai" 2>nul
if %errorlevel% neq 0 (
    echo 📦 安装依赖中...
    %PYTHON% -m pip install streamlit openai -q
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)
echo ✅ 依赖就绪
echo.

:: ── 启动 ──
echo 🚀 启动中... 浏览器打开 http://localhost:%PORT%
echo ─────────────────────────────────────
echo    按 Ctrl+C 停止服务
echo ─────────────────────────────────────
echo.

%PYTHON% -m streamlit run app.py --server.port %PORT% --server.headless true

pause
