@echo off
chcp 65001 >nul
title 考试系统 卸载程序
set INSTALL_DIR=%~dp0

echo ════════════════════════════════════════
echo       考试系统 - 卸载程序
echo ════════════════════════════════════════
echo.
echo 安装目录: %INSTALL_DIR%
echo.
echo 将删除以下内容：
echo   - 考试系统程序文件
echo   - 考试记录数据
echo   - 题库文件
echo   - 桌面快捷方式
echo.
echo 按 Ctrl+C 取消，或按任意键继续卸载...
pause >nul

echo.
echo 正在删除桌面快捷方式...
if exist "%USERPROFILE%\Desktop\考试系统.lnk" (
    del "%USERPROFILE%\Desktop\考试系统.lnk" >nul
    echo   - 桌面快捷方式已删除
) else (
    echo   - 未找到桌面快捷方式
)

echo 正在删除安装目录...
REM 创建临时脚本延迟删除（解决自删除问题）
set TMPFILE=%TEMP%\exam_uninst.bat
> "%TMPFILE%" (
    echo @echo off
    echo timeout /t 2 /nobreak ^>nul
    echo rmdir /s /q "%INSTALL_DIR%"
    echo del "%%~f0"
)
start /b "" cmd /c "%TMPFILE%"

echo.
echo 卸载完成，安装目录将在几秒后自动删除。
timeout /t 3 /nobreak >nul
exit
