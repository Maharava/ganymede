# Ganymede File Server

![Ganymede Logo](assets/ganymede.ico)

A simple local file sharing server with internet access. Ganymede lets you easily share files with others over the internet through a secure, password-protected web interface.

## Features

- 🌐 **Internet Access**: Share files from your local machine to the internet
- 🔐 **Secure**: Basic authentication with customizable usernames and passwords
- 🎨 **Customizable**: User-specific backgrounds and personalized greetings
- 📁 **Simple**: Just drop files in a folder to share them
- 🚀 **Easy Setup**: Minimal configuration required

## Screenshots

*(Sample screenshots would appear here)*

## Installation

### Prerequisites

- Node.js (v14 or newer)
- A computer that can remain powered on while sharing files
- Basic knowledge of command line usage

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/maharava/ganymede.git
   ```

2. Navigate to the project directory:
   ```bash
   cd ganymede
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Create a `.env` file (see [Configuration](#configuration))

5. Run the server:
   - Windows: Double-click `start-ganymede.bat`
   - Mac/Linux: Run `node ganymede.js`

## Configuration

Create a `.env` file in the project root with the following options:

```
# Server configuration
PORT=3000

# User credentials (format: username:password,username2:password2)
USER_CREDENTIALS=user1:password1,user2:password2

# Greeting messages (use {username} as placeholder for the current user)
GREETING_HEADER=Hi, {username}! I'm Ganymede
GREETING_SUBHEADER=Want some of my files? Yeah you do:
GREETING_EMPTY=I got nothing! Tell whoever owns me to put files in the "shared_files" directory.
```

## Usage

### Sharing Files

1. Place any files you want to share in the `shared_files` directory
2. Start the server
3. Share the tunnel URL, your public IP address, and login credentials with users

### Customizing Appearance

The `assets` folder contains customizable elements:

- **Background Images**:
  - For all users: `assets/background.png`
  - For specific users: `assets/background_username.png` (e.g., `assets/background_kyle.png`)
- **Favicon**: `assets/ganymede.ico`

### Accessing Shared Files

Users will need to:
1. Access the tunnel URL shown when the server starts
2. Enter