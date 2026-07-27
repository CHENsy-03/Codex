@echo off
chcp 65001 >nul
title 考试系统 安装程序

set SRC=%~dp0release
if not exist "%SRC%" (
    echo 错误：未找到 release\ 目录
    echo 请将此文件放在 ExamSystem\ 目录下运行。
    pause
    exit /b 1
)

echo ════════════════════════════════════════
echo       考试系统 v1.0.0 安装程序
echo ════════════════════════════════════════
echo.
echo 默认安装路径：C:\Program Files\考试系统
echo.
set /p INSTALL_DIR="请输入安装路径（留空使用默认值）: "
if "%INSTALL_DIR%"=="" set INSTALL_DIR=C:\Program Files\考试系统

echo.
echo 安装到: %INSTALL_DIR%
echo.

echo 正在复制文件...
xcopy "%SRC%" "%INSTALL_DIR%" /E /I /H /Y >nul
if %ERRORLEVEL% NEQ 0 (
    echo 复制失败！请确认你有管理员权限。
    pause
    exit /b 1
)

echo 正在创建桌面快捷方式...
set VBS=%TEMP%\create_shortcut.vbs
> "%VBS%" (
    echo Set ws = CreateObject("WScript.Shell"^)
    echo Set sc = ws.CreateShortcut(ws.SpecialFolders("Desktop"^) ^& "\考试系统.lnk"^)
    echo sc.TargetPath = "%INSTALL_DIR%\考试系统.exe"
    echo sc.WorkingDirectory = "%INSTALL_DIR%"
    echo sc.Description = "离线考试系统"
    echo sc.Save
)
cscript //nologo "%VBS%" >nul 2>&1
del "%VBS%" >nul 2>&1

echo 正在创建开始菜单快捷方式...
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\考试系统
if not exist "%START_MENU%" mkdir "%START_MENU%"
> "%TEMP%\startmenu_shortcut.vbs" (
    echo Set ws = CreateObject("WScript.Shell"^)
    echo Set sc = ws.CreateShortcut("%START_MENU%\考试系统.lnk"^)
    echo sc.TargetPath = "%INSTALL_DIR%\考试系统.exe"
    echo sc.WorkingDirectory = "%INSTALL_DIR%"
    echo sc.Description = "离线考试系统"
    echo sc.Save
)
cscript //nologo "%TEMP%\startmenu_shortcut.vbs" >nul 2>&1
del "%TEMP%\startmenu_shortcut.vbs" >nul 2>&1

echo 安装完成！
echo.
echo 考试系统已安装到：%INSTALL_DIR%
echo 桌面快捷方式和开始菜单已创建。
echo.
pause
