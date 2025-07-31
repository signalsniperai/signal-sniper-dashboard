@echo off
cd /d %~dp0
echo Loading .env...
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do set %%a=%%b

start "" n8n



