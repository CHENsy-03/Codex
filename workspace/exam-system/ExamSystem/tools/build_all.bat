@echo off
chcp 65001 >nul
set TOOLS_DIR=%~dp0
set ROOT_DIR=%TOOLS_DIR%..\..
echo ========== 考试系统 - 完整打包 ==========
echo.

echo [1/3] 编译 Go 后端...
cd /d "%TOOLS_DIR%..\server"
go build -o "..\release\backend\ExamSystem.exe" .\cmd\server\
if %ERRORLEVEL% NEQ 0 ( echo !! Go 编译失败 !! & pause & exit /b 1 )
echo      Go 后端 - OK

echo [2/3] 打包 Python 客户端...
cd /d "%ROOT_DIR%"
pyinstaller --onefile --windowed --name 考试系统 --distpath "ExamSystem\release" "ExamSystem\client\main.py"
if %ERRORLEVEL% NEQ 0 ( echo !! 客户端打包失败 !! & pause & exit /b 1 )
echo      考试系统.exe - OK

echo [3/3] 制作安装包...
pyinstaller --onefile --windowed --name "考试系统安装包" --distpath "%ROOT_DIR%" --add-data "ExamSystem\release\考试系统.exe;." --add-data "ExamSystem\release\backend;backend" --add-data "ExamSystem\release\config;config" --add-data "ExamSystem\release\data;data" --add-data "ExamSystem\release\tools;tools" --add-data "ExamSystem\release\卸载考试系统.bat;." "ExamSystem\release\setup.py"
if %ERRORLEVEL% NEQ 0 ( echo !! 安装包制作失败 !! & pause & exit /b 1 )

echo ========== 全部完成 ==========
dir "%ROOT_DIR%\考试系统安装包.exe"
pause
