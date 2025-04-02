#!/bin/bash

# Ganymede File Sharing Server Launcher

# Default settings
SERVER_SCRIPT_PATH="$(dirname "$(readlink -f "$0")")/file_server.py"
ASSETS_SCRIPT_PATH="$(dirname "$(readlink -f "$0")")/setup_assets.py"
DEFAULT_PORT=8000
DEFAULT_DIR="$(pwd)"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -d|--directory)
            DIRECTORY="$2"
            shift 2
            ;;
        -t|--token)
            TOKEN="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-p PORT] [-d DIRECTORY] [-t TOKEN]"
            echo "  -p, --port PORT        Port to run the server on (default: 8000)"
            echo "  -d, --directory DIR    Directory to share files from (default: current directory)"
            echo "  -t, --token TOKEN      Custom access token (random if not specified)"
            echo "  -h, --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information."
            exit 1
            ;;
    esac
done

# Set defaults if not specified
PORT=${PORT:-$DEFAULT_PORT}
DIRECTORY=${DIRECTORY:-$DEFAULT_DIR}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found. Please install Python 3 and try again."
    exit 1
fi

# Make sure the server script is executable
chmod +x "$SERVER_SCRIPT_PATH"

# Check if the specified directory exists
if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Directory '$DIRECTORY' does not exist or is not a directory."
    exit 1
fi

# Create welcome image if it doesn't exist
echo "Setting up assets..."
python3 "$ASSETS_SCRIPT_PATH"

# Build command with optional token
CMD="python3 \"$SERVER_SCRIPT_PATH\" --port \"$PORT\" --directory \"$DIRECTORY\""
if [ ! -z "$TOKEN" ]; then
    CMD="$CMD --token \"$TOKEN\""
fi

# Start the server
echo "Starting file sharing server..."
echo "Access via http://$(hostname -I | awk '{print $1}'):$PORT/"
eval $CMD