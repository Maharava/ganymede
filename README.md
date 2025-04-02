# Ganymede Secure File Sharing Server

A secure file sharing server with token-based authentication for temporary file sharing over the internet.

## Features

- HTTPS encryption for secure file transfer
- Username and token-based authentication
- Welcome image overlay on login
- Public IP detection for internet sharing
- Windows-optimized design
- Self-signed certificate generation
- Simple command-line interface

## Requirements

- Python 3.6 or higher
- Windows operating system
- Required packages (auto-installed):
  - pillow (for image processing)
  - pyopenssl (for HTTPS)
  - cryptography (for HTTPS)
- Port forwarding on your router (for internet access)

## Installation

1. Clone the repository or download the files
2. Run `check_deps.py` to install dependencies:

```python check_deps.py```

## Quick Start

1. Start the server with default settings:

```start_server.bat```

2. Or specify custom parameters:

```start_server.bat -p 9000 -d C:\Files\Share -u admin -t mysecrettoken```

## Command-Line Options

- `-p, --port PORT`: Port to run server on (default: 8000)
- `-d, --directory DIR`: Directory to share (default: current directory)
- `-t, --token TOKEN`: Custom access token (random if not specified)
- `-u, --username USERNAME`: Username for authentication
- `-h, --help`: Show help message

## Configuration

Edit `config.json` to configure:
- User credentials
- HTTPS settings
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
 "use_https": true,
 "cert_file": "certs/server.crt",
 "key_file": "certs/server.key"
}```

Internet Sharing
Ganymede automatically detects your public IP address to facilitate sharing files over the internet. To enable external access:

Configure port forwarding on your router (forward the server port to your computer)
Ensure your firewall allows incoming connections on the specified port
Share the public URL displayed when the server starts
Note: Using a dynamic DNS service is recommended if your ISP assigns dynamic IP addresses.

Security Notes
Self-signed certificates are used for HTTPS (browsers will display security warnings)
Authentication is based on username/token pairs defined in config.json or command line
Cookies are protected with HttpOnly, Secure, and SameSite attributes
Designed for temporary file sharing in controlled environments
All data is encrypted in transit but the server doesn't encrypt files at rest

Troubleshooting
Certificate warnings: These are normal with self-signed certificates. You can add an exception in your browser.
Connection refused: Check port forwarding setup and firewall settings.
Login failures: Verify username and token combinations in config.json.
Missing images: Run setup_assets.py to generate the welcome image.