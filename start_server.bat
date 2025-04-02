@echo off
REM filepath: c:\Users\rford\Desktop\AI\ganymede\start_server.bat
setlocal enabledelayedexpansion

REM Ganymede File Sharing Server Launcher for Windows

REM Default settings
set "SCRIPT_DIR=%~dp0"
set "SERVER_SCRIPT_PATH=%SCRIPT_DIR%file_server.py"
set "ASSETS_SCRIPT_PATH=%SCRIPT_DIR%setup_assets.py"
set "DEPS_SCRIPT_PATH=%SCRIPT_DIR%check_deps.py"
set "DEFAULT_PORT=8000"
set "DEFAULT_DIR=%CD%"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="-p" (
    set "PORT=%~2"
    shift
    shift
    goto :parse_args
) else if "%~1"=="--port" (
    set "PORT=%~2"
    shift
    shift
    goto :parse_args
) else if "%~1"=="-d" (
    set "DIRECTORY=%~2"
    shift
    shift
    goto :parse_args
) else if "%~1"=="--directory" (
    set "DIRECTORY=%~2"
    shift
    shift
    goto :parse_args
) else if "%~1"=="-t" (
    set "TOKEN=%~2"
    shift
    shift
    goto :parse_args
) else if "%~1"=="--token" (
    set "TOKEN=%~2"
    shift
    shift
    goto :parse_args
) else if "%~1"=="-u" (
    set "USERNAME=%~2"
    shift
    shift
    goto :parse_args
) else if "%~1"=="--username" (
    set "USERNAME=%~2"
    shift
    shift
    goto :parse_args
) else if "%~1"=="-h" (
    goto :show_help
) else if "%~1"=="--help" (
    goto :show_help
) else (
    echo Unknown option: %~1
    echo Use -h or --help for usage information.
    exit /b 1
)

:args_done
REM Set defaults if not specified
if not defined PORT set "PORT=%DEFAULT_PORT%"
if not defined DIRECTORY set "DIRECTORY=%DEFAULT_DIR%"

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python is required but not found. Please install Python and try again.
    exit /b 1
)

REM Check for required dependencies
echo Checking dependencies...
python "%DEPS_SCRIPT_PATH%"
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to install required dependencies.
    exit /b 1
)

REM Check if the specified directory exists
if not exist "%DIRECTORY%\" (
    echo Error: Directory '%DIRECTORY%' does not exist or is not a directory.
    exit /b 1
)

REM Create welcome image if it doesn't exist
echo Setting up assets...
python "%ASSETS_SCRIPT_PATH%"

REM Build command with optional parameters
set "CMD=python "%SERVER_SCRIPT_PATH%" --port %PORT% --directory "%DIRECTORY%""
if defined TOKEN set "CMD=!CMD! --token %TOKEN%"
if defined USERNAME set "CMD=!CMD! --username %USERNAME%"

REM Start the server
echo Starting file sharing server...
echo.
echo The server will automatically detect your public IP address.
echo This IP address will be displayed when the server starts.
echo.
echo IMPORTANT: For external access over the internet:
echo  1. Make sure port %PORT% is forwarded in your router to this computer
echo  2. Check that your firewall allows incoming connections on port %PORT%
echo  3. If your ISP uses dynamic IP addressing, consider using a Dynamic DNS service
echo.
%CMD%
exit /b

:show_help
echo Usage: %~nx0 [-p PORT] [-d DIRECTORY] [-t TOKEN] [-u USERNAME]
echo   -p, --port PORT        Port to run the server on (default: 8000)
echo   -d, --directory DIR    Directory to share files from (default: current directory)
echo   -t, --token TOKEN      Custom access token (random if not specified)
echo   -u, --username USERNAME Username for authentication (required in config)
echo   -h, --help             Show this help message
exit /b 0