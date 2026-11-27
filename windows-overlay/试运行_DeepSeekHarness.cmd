@echo off
chcp 65001 >nul
cd /d "%~dp0"
taskkill /f /im AemeathAntigravityBoot.exe >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1"
if errorlevel 1 (
    pause
    exit /b 1
)
start "" "%~dp0build\AemeathAntigravityBoot.exe" --settings --play-app deepseek-harness
