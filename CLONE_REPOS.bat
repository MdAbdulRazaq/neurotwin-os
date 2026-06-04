@echo off
echo Cloning external repositories for NEUROTWIN OS...
if not exist "D:\neurotwin\external" mkdir D:\neurotwin\external
cd /d D:\neurotwin\external

echo Cloning ruvnet/ruflo...
git clone https://github.com/ruvnet/ruflo.git ruflo 2>&1
if %ERRORLEVEL% EQU 0 (echo ruflo cloned successfully.) else (echo ruflo already exists or error.)

echo Cloning tirth8205/code-review-graph...
git clone https://github.com/tirth8205/code-review-graph.git code-review-graph 2>&1
if %ERRORLEVEL% EQU 0 (echo code-review-graph cloned successfully.) else (echo code-review-graph already exists or error.)

echo.
echo Directory listing:
dir D:\neurotwin\external /b
echo Done!
pause
