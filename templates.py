"""HTML templates for the Ganymede File Server"""

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Ganymede File Server - Login</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
        .container {{ max-width: 500px; margin: 80px auto; padding: 30px; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); background-color: white; }}
        h2 {{ color: #2c3e50; margin-top: 0; }}
        input {{ padding: 12px; margin: 15px 0; width: 100%; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
        button {{ padding: 12px; background-color: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px; }}
        button:hover {{ background-color: #2980b9; }}
        .form-group {{ margin-bottom: 15px; }}
        .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Ganymede File Server</h2>
        <p>Please enter your credentials to continue:</p>
        <form id="loginForm">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" placeholder="Enter username" required>
            </div>
            <div class="form-group">
                <label for="token">Access Token:</label>
                <input type="password" id="token" name="token" placeholder="Enter access token" required>
            </div>
            <button type="submit">Access Files</button>
        </form>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            var username = document.getElementById('username').value;
            var token = document.getElementById('token').value;
            
            // Using fetch to set the cookie via a POST request
            fetch('/', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{username: username, token: token}})
            }})
            .then(response => {{
                if(response.ok) {{
                    window.location.href = '/';
                }} else {{
                    alert('Invalid credentials. Please try again.');
                }}
            }});
        }});
    </script>
</body>
</html>
"""

UNAUTHORIZED_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Unauthorized</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 500px; margin: 80px auto; padding: 30px; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); background-color: white; }
        .error { color: #e74c3c; }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h2 class="error">Unauthorized Access</h2>
        <p>Invalid or missing authentication.</p>
        <p><a href="/">Go back to login</a></p>
    </div>
</body>
</html>
"""

WELCOME_OVERLAY_TEMPLATE = """
<div id="welcome-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(255,255,255,0.95); display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 1000;">
    <img src="data:image/png;base64,{image_data}" alt="Welcome" style="max-width: 80%; max-height: 70%;">
    <h2 style="margin-top: 20px; color: #2c3e50;">Welcome to Ganymede File Server, {username}!</h2>
</div>
<script>
    setTimeout(function() {{
        const overlay = document.getElementById('welcome-overlay');
        overlay.style.transition = 'opacity 1s';
        overlay.style.opacity = 0;
        setTimeout(function() {{
            overlay.remove();
        }}, 1000);
    }}, 2000);
</script>
"""