#!/usr/bin/env python3
import http.server
import socketserver
import os
import random
import string
import socket
import sys
from io import BytesIO
import json
import base64
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import templates
from templates import LOGIN_PAGE, UNAUTHORIZED_PAGE, WELCOME_OVERLAY_TEMPLATE

# Configuration
DEFAULT_CONFIG = {
    "port": 8000,
    "token_length": 8,
    "directory": os.getcwd(),
    "cookie_name": "ganymede_auth",
    "welcome_image": "assets/welcome.png",
    "allowed_users": {},
    "use_https": False  # Default to HTTP
}

def get_public_ip():
    """Get the public-facing IP address of the machine."""
    try:
        # Try to get public IP from external service
        import urllib.request
        external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        return external_ip
    except Exception as e:
        print(f"Warning: Could not determine public IP: {e}")
        # Fall back to localhost
        return "127.0.0.1"

def generate_token(length=DEFAULT_CONFIG["token_length"]):
    """Generate a random token."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def load_config():
    """Load configuration from config.json if it exists."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
    
    # Force use_https to False for this HTTP-only version
    config["use_https"] = False
    
    logging.debug(f"Loaded configuration: {config}")
    return config

def get_welcome_image_data(config):
    """Load the welcome image and convert to base64."""
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config['welcome_image'])
    
    if not os.path.exists(image_path):
        # Return empty string if image doesn't exist
        print(f"Warning: Welcome image not found at {image_path}")
        return ""
    
    try:
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Warning: Failed to load welcome image: {e}")
        return ""

# Load configuration
CONFIG = load_config()
TOKEN_MAP = {}  # Will map usernames to tokens
PUBLIC_IP = get_public_ip()
WELCOME_IMAGE_DATA = get_welcome_image_data(CONFIG)
CURRENT_USERS = {}  # Track active user sessions

class AuthenticatedHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with cookie-based authentication."""
    
    def check_authentication(self):
        """Check if the request includes a valid authentication cookie."""
        cookie_header = self.headers.get('Cookie', '')
        if not cookie_header:
            logging.debug(f"No cookies found in request from {self.client_address[0]}")
            return False, None
            
        cookies = {}
        for cookie in cookie_header.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                cookies[name] = value
        
        auth_cookie = cookies.get(CONFIG['cookie_name'])
        if not auth_cookie or ':' not in auth_cookie:
            logging.debug(f"No valid auth cookie found. Cookies: {cookies}")
            return False, None
            
        username, token = auth_cookie.split(':', 1)
        
        # Check if this is a valid user session
        if username in TOKEN_MAP and TOKEN_MAP[username] == token:
            logging.debug(f"Valid authentication for {username} from {self.client_address[0]}")
            return True, username
        
        logging.debug(f"Invalid token for {username} from {self.client_address[0]}")
        return False, None
    
    def do_GET(self):
        """Handle GET requests with authentication."""
        # If accessing root without auth, show login page
        auth_valid, username = self.check_authentication()
        
        if self.path == '/' and not auth_valid:
            self.send_login_page()
            return
        
        # All other paths require authentication
        if not auth_valid:
            self.send_unauthorized_page()
            return
            
        # Store username for welcome overlay
        self.username = username
            
        # Process authenticated request
        return self.serve_content()
    
    def serve_content(self):
        """Serve the requested content."""
        # Let the parent class handle the file serving
        response = super().do_GET()
        
        # No need to modify anything for non-HTML responses
        if not self.path.endswith('/') and not self.path.endswith('.html'):
            return response
            
        return response
    
    def send_login_page(self):
        """Send the login page to the client."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(LOGIN_PAGE.encode())
    
    def send_unauthorized_page(self):
        """Send unauthorized access page to the client."""
        self.send_response(401)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(UNAUTHORIZED_PAGE.encode())
    
    def list_directory(self, path):
        """Generate directory listing with welcome screen."""
        try:
            list_resp = super().list_directory(path)
            if not list_resp:
                return None
            
            list_html = list_resp.read().decode('utf-8')
            
            # Add welcome overlay if image data exists and it's the first visit
            if WELCOME_IMAGE_DATA and self.path == '/' and hasattr(self, 'username'):
                # Find the </body> tag and insert welcome overlay before it
                overlay_html = WELCOME_OVERLAY_TEMPLATE.format(
                    image_data=WELCOME_IMAGE_DATA,
                    username=self.username
                )
                list_html = list_html.replace('</body>', f'{overlay_html}</body>')
            
            # Create a BytesIO object for the modified HTML
            buffer = BytesIO()
            buffer.write(list_html.encode('utf-8'))
            buffer.seek(0)
            return buffer
        except Exception as e:
            self.send_error(500, f"Error listing directory: {str(e)}")
            return None
    
    def do_POST(self):
        """Handle POST requests for authentication."""
        if self.path == '/':
            # Process login attempt
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                username = data.get('username', '')
                token = data.get('token', '')
                
                logging.info(f"Login attempt from {self.client_address[0]} - Username: {username}")
                logging.debug(f"TOKEN_MAP: {TOKEN_MAP}")
                logging.debug(f"Configured users: {CONFIG['allowed_users']}")
                
                # Check if username exists and token matches
                valid = False
                
                # First check if this is a command-line specified user
                if username in TOKEN_MAP and TOKEN_MAP[username] == token:
                    logging.info(f"Authentication successful for {username} via TOKEN_MAP")
                    valid = True
                
                # Then check against allowed_users in config
                elif username in CONFIG['allowed_users'] and CONFIG['allowed_users'][username] == token:
                    # Add to token map for future validation
                    TOKEN_MAP[username] = token
                    logging.info(f"Authentication successful for {username} via config")
                    valid = True
                else:
                    logging.info(f"Authentication failed for {username}. Invalid credentials.")
                
                if valid:
                    # Authentication successful, set cookie (HTTP-only version without Secure flag)
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    cookie_value = f"{username}:{token}"
                    cookie = f"{CONFIG['cookie_name']}={cookie_value}; Path=/; HttpOnly; SameSite=Lax"
                    self.send_header('Set-Cookie', cookie)
                    self.end_headers()
                    self.wfile.write(b'Authentication successful')
                    
                    # Track user session
                    CURRENT_USERS[username] = {
                        'login_time': time.time(),
                        'ip': self.client_address[0]
                    }
                    return
            except Exception as e:
                logging.error(f"Error processing login: {e}", exc_info=True)
                
            # Authentication failed
            self.send_response(401)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Authentication failed')
        else:
            # All other POST requests are disabled
            self.send_response(405)  # Method Not Allowed
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'POST requests are not allowed on this server except for authentication.')

def run_server(port=CONFIG['port'], directory=CONFIG['directory'], token=None, username=None):
    """Run the HTTP file server."""
    global TOKEN_MAP
    
    # Handle username/token authentication
    if username and token:
        TOKEN_MAP[username] = token
    elif token and not username:
        # If token provided but no username, use "admin" as default
        TOKEN_MAP["admin"] = token
    elif CONFIG['allowed_users']:
        # Use the configured users
        print("Using configured users from config.json")
        # Add configured users to TOKEN_MAP
        TOKEN_MAP.update(CONFIG['allowed_users'])
    else:
        # If no authentication specified, create a default admin user
        default_username = "admin"
        default_token = token if token else generate_token(CONFIG['token_length'])
        TOKEN_MAP[default_username] = default_token
        print(f"No users specified. Created default user:")
        print(f"  Username: {default_username}")
        print(f"  Token: {default_token}")
    
    # Create necessary directories
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    
    # Set the directory to serve files from
    handler = lambda *args, **kwargs: AuthenticatedHTTPHandler(*args, directory=directory, **kwargs)
    
    try:
        # Create and start the server
        httpd = socketserver.ThreadingTCPServer(("0.0.0.0", port), handler)
        
        print(f"\n=== Ganymede File Sharing Server (HTTP) ===")
        print(f"Server started on port {port}")
        
        if TOKEN_MAP:
            print("\nAuthentication credentials:")
            for user, token_val in TOKEN_MAP.items():
                print(f"  Username: {user}")
                print(f"  Token: {token_val}")
                print()
        
        print(f"Serving files from: {os.path.abspath(directory)}")
        print(f"Local access URL: http://localhost:{port}/")
        print(f"Network access URL: http://{PUBLIC_IP}:{port}/")
        print("Press Ctrl+C to stop the server.\n")
        
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ganymede File Sharing Server with Authentication")
    parser.add_argument("-p", "--port", type=int, default=CONFIG['port'], help=f"Port to run the server on (default: {CONFIG['port']})")
    parser.add_argument("-d", "--directory", type=str, default=CONFIG['directory'] or os.getcwd(), help="Directory to share files from")
    parser.add_argument("-t", "--token", type=str, help="Custom access token (random if not specified)")
    parser.add_argument("-u", "--username", type=str, help="Username for authentication (required in config)")
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist or is not a directory.")
        sys.exit(1)
    
    run_server(port=args.port, directory=args.directory, token=args.token, username=args.username)