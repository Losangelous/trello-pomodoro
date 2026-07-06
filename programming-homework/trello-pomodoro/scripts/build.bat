@echo off
chcp 65001 >nul
REM Trello Pomodoro - Windows 构建脚本

echo ==========================================
echo   Trello Pomodoro - 构建脚本
echo ==========================================
echo.

REM 设置目录
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set CPP_DIR=%PROJECT_ROOT%\cpp
set BUILD_DIR=%PROJECT_ROOT%\build

REM 检查 CMake
cmake --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 CMake，请先安装 CMake
    exit /b 1
)
echo [OK] CMake 已找到

REM 检查 Qt
qmake --version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到 qmake，请确保 Qt 已正确安装并添加到 PATH
)

REM 创建构建目录
if not exist "%BUILD_DIR%" (
    mkdir "%BUILD_DIR%"
)

echo.
echo [1/3] 配置项目...
cd /d "%BUILD_DIR%"
cmake -S "%CPP_DIR%" -B . -G "MinGW Makefiles" 2>nul
if errorlevel 1 (
    cmake -S "%CPP_DIR%" -B . -G "Visual Studio 16 2019" 2>nul
)
if errorlevel 1 (
    echo [错误] CMake 配置失败
    exit /b 1
)

echo.
echo [2/3] 构建项目...
cmake --build . --config Release
if errorlevel 1 (
    echo [错误] 构建失败
    exit /b 1
)

echo.
echo [3/3] 完成！
echo 可执行文件位于: %BUILD_DIR%\Release\TrelloPomodoro.exe
echo.
echo 使用方法:
echo   1. 先启动后端服务: python scripts\start_backend.py
echo   2. 运行: %BUILD_DIR%\Release\TrelloPomodoro.exe
echo.

pause
