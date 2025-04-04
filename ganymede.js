// file-server.js
const express = require('express');
const path = require('path');
const fs = require('fs');
const localtunnel = require('localtunnel');
const basicAuth = require('express-basic-auth');
const https = require('https');
require('dotenv').config(); // Add dotenv support
const app = express();
const port = process.env.PORT || 3000;

// Set up EJS as the view engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Function to get public IP address
function getPublicIP() {
    return new Promise((resolve, reject) => {
        https.get('https://api.ipify.org', (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                resolve(data.trim());
            });
        }).on('error', (err) => {
            console.error(`Error getting public IP: ${err.message}`);
            resolve('Unable to determine public IP');
        });
    });
}

// Basic authentication from .env file
const users = {};
// Parse USERNAME_1:PASSWORD_1,USERNAME_2:PASSWORD_2 format from .env
const userCredentials = process.env.USER_CREDENTIALS || 'admin:password123';
userCredentials.split(',').forEach(credential => {
    const [username, password] = credential.split(':');
    if (username && password) {
        users[username] = password;
    }
});

app.use(basicAuth({
    users,
    challenge: true,
    realm: 'Simple File Sharing'
}));

// Add this function before your route definitions
function getFileType(filename) {
    const ext = path.extname(filename).toLowerCase();
    // Common file types
    const fileTypes = {
        '.pdf': 'PDF Document',
        '.doc': 'Word Document',
        '.docx': 'Word Document',
        '.xls': 'Excel Spreadsheet',
        '.xlsx': 'Excel Spreadsheet',
        '.ppt': 'PowerPoint',
        '.pptx': 'PowerPoint',
        '.jpg': 'JPEG Image',
        '.jpeg': 'JPEG Image',
        '.png': 'PNG Image',
        '.gif': 'GIF Image',
        '.mp3': 'MP3 Audio',
        '.mp4': 'MP4 Video',
        '.zip': 'ZIP Archive',
        '.txt': 'Text File',
        '.csv': 'CSV File',
    };
    
    return fileTypes[ext] || 'File';
}

// Serve the file browser page
app.get('/', (req, res) => {
    const directoryPath = path.join(__dirname, 'shared_files');
    
    // Get the current authenticated username
    const currentUser = req.auth.user;

    // Create assets directory if it doesn't exist
    try {
        if (!fs.existsSync(path.join(__dirname, 'assets'))) {
            fs.mkdirSync(path.join(__dirname, 'assets'), { recursive: true });
            console.log('Created assets directory');
        }
    } catch (err) {
        console.error(`Error creating assets directory: ${err.message}`);
    }

    // Inside your route handler, modify the background detection code
    const userBgPath = path.join(__dirname, 'assets', `background_${currentUser}.png`);
    const defaultBgPath = path.join(__dirname, 'assets', 'background.png');
    let backgroundImage = null;
    let userBackgroundImage = null;
    let backgroundBasename = '';

    // Always use default background as initial background if it exists
    if (fs.existsSync(defaultBgPath)) {
        backgroundImage = '/assets/background.png';
        backgroundBasename = 'background.png';
    }

    // Check if user has a custom background (but don't set it initially)
    if (fs.existsSync(userBgPath)) {
        userBackgroundImage = `/assets/background_${currentUser}.png`;
    }

    // Create the directory if it doesn't exist
    try {
        if (!fs.existsSync(directoryPath)) {
            fs.mkdirSync(directoryPath, { recursive: true });
        }
    } catch (err) {
        console.error(`Error creating directory: ${err.message}`);
        return res.status(500).send('Error creating shared_files directory');
    }
    
    fs.readdir(directoryPath, (err, files) => {
        if (err) {
            console.error(`Error reading directory: ${err.message}`);
            return res.status(500).send('Error reading directory');
        }
        
        // Generate HTML for file listing
        let fileList = '<ul>';
        files.forEach(file => {
            try {
                const filePath = path.join(directoryPath, file);
                const stats = fs.statSync(filePath);
                if (stats.isFile()) {
                    const fileSize = (stats.size / 1024).toFixed(2) + ' KB';
                    const fileType = getFileType(file);
                    const ext = path.extname(file).toLowerCase();
                    
                    // Check if the file is an image
                    const isImage = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].includes(ext);
                    let previewHtml = '';
                    
                    // Add image preview for image files
                    if (isImage) {
                        previewHtml = `<img class="thumbnail" src="/preview/${file}" alt="${file}" />`;
                    }
                    
                    fileList += `<li class="file-item">
                        <span class="file-type ${ext.substring(1) || 'generic'}">${fileType}</span>
                        ${previewHtml}
                        <a href="/download/${file}">${file}</a>
                        <span class="file-size">(${fileSize})</span>
                    </li>`;
                }
            } catch (err) {
                console.error(`Error processing file ${file}: ${err.message}`);
            }
        });
        fileList += '</ul>';
        
        // Get custom greeting messages from .env or use defaults
        let greetingHeader = process.env.GREETING_HEADER || "Hi, {username}! I'm Ganymede";
        const greetingSubheader = process.env.GREETING_SUBHEADER || "Want some of my files? Yeah you do:";
        const greetingEmpty = process.env.GREETING_EMPTY || "I got nothing! Tell whoever owns me to put files in the \"shared_files\" directory.";
        
        // Replace {username} placeholder with actual username
        greetingHeader = greetingHeader.replace('{username}', currentUser);
        
        // Render the template with the data
        res.render('index', {
            files,
            fileList,
            backgroundImage,
            userBackgroundImage,
            backgroundBasename,
            greetingHeader,
            greetingSubheader,
            greetingEmpty
        });
    });
});

// Handle file downloads
app.get('/download/:filename', (req, res) => {
    const filename = req.params.filename;
    const filePath = path.join(__dirname, 'shared_files', filename);
    
    // Check if file exists and is within the shared_files directory
    try {
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            res.download(filePath);
        } else {
            res.status(404).send('File not found');
        }
    } catch (err) {
        console.error(`Error accessing file ${filename}: ${err.message}`);
        res.status(500).send('Error accessing file');
    }
});

// Also add a route to serve the assets folder
app.use('/assets', express.static(path.join(__dirname, 'assets')));

// Add this route before the server.listen call

// Handle image previews
app.get('/preview/:filename', (req, res) => {
    const filename = req.params.filename;
    const filePath = path.join(__dirname, 'shared_files', filename);
    
    // Check if file exists and is within the shared_files directory
    try {
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            // Check if it's an image file
            const ext = path.extname(filename).toLowerCase();
            if (['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].includes(ext)) {
                res.sendFile(filePath);
            } else {
                res.status(400).send('Not an image file');
            }
        } else {
            res.status(404).send('File not found');
        }
    } catch (err) {
        console.error(`Error accessing file ${filename}: ${err.message}`);
        res.status(500).send('Error accessing file');
    }
});

// Serve favicon from assets
app.get('/favicon.ico', (req, res) => {
    const faviconPath = path.join(__dirname, 'assets', 'ganymede.ico');
    if (fs.existsSync(faviconPath)) {
        res.sendFile(faviconPath);
    } else {
        res.status(204).end(); // No content if favicon doesn't exist
    }
});

// Start the server
const server = app.listen(port, async () => {
    console.log(`File server running at http://localhost:${port}`);
    
    // Get and display public IP
    const publicIP = await getPublicIP();
    console.log(`Your public IP address is: ${publicIP}`);
    
    // Create a tunnel to make the server accessible over the internet
    (async () => {
        try {
            const tunnel = await localtunnel({ port });
            console.log(`Server is accessible at: ${tunnel.url}`);
            console.log(`Username: kyle or reece, Password: as configured`);
            console.log(`Place files you want to share in the "shared_files" directory`);
            
            tunnel.on('close', () => {
                console.log('Tunnel closed');
            });
            
            tunnel.on('error', (err) => {
                console.error(`Tunnel error: ${err.message}`);
            });
        } catch (err) {
            console.error(`Failed to create tunnel: ${err.message}`);
            console.log('Server is still accessible locally at http://localhost:' + port);
        }
    })();
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('Shutting down server...');
    server.close(() => {
        console.log('Server closed');
        process.exit(0);
    });
});
