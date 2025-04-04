@echo off
echo Starting Ganymede File Server...

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if ganymede.js exists
if not exist ganymede.js (
    echo ERROR: ganymede.js not found
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Run Node with trace warnings
echo Running ganymede.js...
node --trace-warnings ganymede.js

pause