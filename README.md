# Ganymede File Sharing Server

A simple file sharing server with token-based authentication for temporary file sharing over the network.

## Features

- Username and token-based authentication
- Welcome image overlay on login
- Public IP detection for network sharing
- Windows-optimized design
- Simple command-line interface

## Requirements

- Python 3.6 or higher
- Windows operating system
- Required packages (auto-installed):
  - pillow (for image processing)
- Port forwarding on your router (for internet access)

## Installation

1. Clone the repository or download the files
2. Run `check_deps.py` to install dependencies:

```
python check_deps.py
```

## Quick Start

1. Start the server with default settings:

```
start_server.bat
```

2. Or specify custom parameters:

```
start_server.bat -p 9000 -d C:\Files\Share -u admin -t mysecrettoken
```

## Command-Line Options

- `-p, --port PORT`: Port to run server on (default: 8000)
- `-d, --directory DIR`: Directory to share (default: current directory)
- `-t, --token TOKEN`: Custom access token (random if not specified)
- `-u, --username USERNAME`: Username for authentication
- `-h, --help`: Show help message

## Configuration

Edit `config.json` to configure:
- User credentials
- Port and directory defaults

Example config.json:
```json
{
 "port": 8000,
 "token_length": 8,
 "directory": "",
 "cookie_name": "ganymede_auth",
 "welcome_image": "assets/welcome.png",
 "allowed_users": {
     "admin": "admin_secret",
     "guest": "guest_access"
 },
 "use_https": false
}
```

## Internet Sharing
Ganymede automatically detects your public IP address to facilitate sharing files over the internet. To enable external access:

- Configure port forwarding on your router (forward the server port to your computer)
- Ensure your firewall allows incoming connections on the specified port
- Share the public URL displayed when the server starts
- Note: Using a dynamic DNS service is recommended if your ISP assigns dynamic IP addresses.

## Security Notes
- Authentication is based on username/token pairs defined in config.json or command line
- Designed for temporary file sharing in controlled environments
- The server doesn't encrypt data in transit (uses HTTP)
- All data is transmitted in plain text - do not use for sensitive information

## Troubleshooting
- Connection refused: Check port forwarding setup and firewall settings
- Login failures: Verify username and token combinations in config.json
- Missing images: Run setup_assets.py to generate the welcome image