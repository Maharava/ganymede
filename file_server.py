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
import ssl
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
    "use_https": True,
    "cert_file": "certs/server.crt",
    "key_file": "certs/server.key"
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

def setup_https(config):
    """Ensure HTTPS certificates are available."""
    if not config.get('use_https', True):
        return None
    
    cert_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config['cert_file'])
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config['key_file'])
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("HTTPS certificates not found. Generating self-signed certificates...")
        try:
            import generate_cert
            if not generate_cert.generate_self_signed_cert():
                print("Warning: Failed to generate HTTPS certificates. Falling back to HTTP.")
                return None
        except ImportError:
            print("Warning: Certificate generation module not found. Falling back to HTTP.")
            return None
    
    # Create SSL context
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        return context
    except Exception as e:
        print(f"Warning: Failed to setup HTTPS: {e}. Falling back to HTTP.")
        return None

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
            return False, None
            
        cookies = {}
        for cookie in cookie_header.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                cookies[name] = value
        
        auth_cookie = cookies.get(CONFIG['cookie_name'])
        if not auth_cookie or ':' not in auth_cookie:
            return False, None
            
        username, token = auth_cookie.split(':', 1)
        
        # Check if this is a valid user session
        if username in TOKEN_MAP and TOKEN_MAP[username] == token:
            return True, username
        
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
                
                logging.debug(f"Login attempt - Username: {username}, Configured users: {CONFIG['allowed_users']}, TOKEN_MAP: {TOKEN_MAP}")
                
                # Check if username exists and token matches
                valid = False
                
                # First check if this is a command-line specified user
                if username in TOKEN_MAP and TOKEN_MAP[username] == token:
                    valid = True
                
                # Then check against allowed_users in config
                elif username in CONFIG['allowed_users'] and CONFIG['allowed_users'][username] == token:
                    # Add to token map for future validation
                    TOKEN_MAP[username] = token
                    valid = True
                
                if valid:
                    # Authentication successful, set cookie with secure attributes
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    cookie_value = f"{username}:{token}"
                    cookie = f"{CONFIG['cookie_name']}={cookie_value}; Path=/; HttpOnly"
                    if CONFIG.get('use_https', True):
                        cookie += "; Secure; SameSite=Strict"
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
                print(f"Error processing login: {e}")
                
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

def create_custom_https_server(address, port, handler, ssl_context):
    """Create an HTTPS server with the given handler and SSL context."""
    # Change from "" to "0.0.0.0" to explicitly bind to all network interfaces
    httpd = socketserver.ThreadingTCPServer(("0.0.0.0", port), handler)
    httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
    return httpd

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
        # Add this line to copy configured users to TOKEN_MAP
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
    
    certs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')
    os.makedirs(certs_dir, exist_ok=True)
    
    # Set the directory to serve files from
    handler = lambda *args, **kwargs: AuthenticatedHTTPHandler(*args, directory=directory, **kwargs)
    
    # Setup HTTPS if enabled
    ssl_context = setup_https(CONFIG) if CONFIG.get('use_https', True) else None
    protocol = "HTTPS" if ssl_context else "HTTP"
    
    try:
        # Create and start the server
        if ssl_context:
            httpd = create_custom_https_server("0.0.0.0", port, handler, ssl_context)
        else:
            httpd = socketserver.ThreadingTCPServer(("0.0.0.0", port), handler)
        
        print(f"\n=== Ganymede File Sharing Server ===")
        print(f"Server started at {protocol.lower()}://{PUBLIC_IP}:{port}/")
        
        if TOKEN_MAP:
            print("\nAuthentication credentials:")
            for user, token_val in TOKEN_MAP.items():
                print(f"  Username: {user}")
                print(f"  Token: {token_val}")
                print()
        
        print(f"Serving files from: {os.path.abspath(directory)}")
        print(f"Share this URL with others: {protocol.lower()}://{PUBLIC_IP}:{port}/")
        print("They will need to enter valid credentials to access files.")
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
