// file-server.js
const express = require('express');
const path = require('path');
const fs = require('fs');
const localtunnel = require('localtunnel');
const basicAuth = require('express-basic-auth');
const https = require('https');
require('dotenv').config(); // Add dotenv support
const archiver = require('archiver');
const socketIo = require('socket.io');
const rateLimit = require('express-rate-limit'); // Add rateLimit
const multer = require('multer'); // Add multer
const compression = require('compression'); // Add compression

const app = express();
const port = process.env.PORT || 3000;

// Add this near the top after creating the Express app
app.use(express.json()); // For parsing application/json requests

// Create limiters
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 attempts per window
  message: 'Too many login attempts, please try again later'
});

const downloadLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 30, // 30 downloads per minute
  message: 'Download limit exceeded, please try again later'
});

// Apply to specific routes
app.use('/download', downloadLimiter);

// Add compression middleware (before routes)
app.use(compression({
  // Compression filter - only compress text-based files
  filter: (req, res) => {
    if (req.path.startsWith('/download/')) {
      // Check file extension
      const ext = path.extname(req.path).toLowerCase();
      // Only compress text files, HTML, CSS, JS, JSON, etc.
      return ['.txt', '.html', '.css', '.js', '.json', '.xml', '.md'].includes(ext);
    }
    // Default compression behavior for other routes
    return compression.filter(req, res);
  },
  level: 6 // Compression level (0-9, higher = more compression but slower)
}));

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

// Add this function to sanitize file paths
function sanitizePath(userPath) {
  // Remove any null bytes
  let sanitized = userPath.replace(/\0/g, '');
  
  // Normalize path to remove ../ sequences
  const normalized = path.normalize(sanitized).replace(/^(\.\.(\/|\\|$))+/, '');
  
  // Ensure path is within shared_files directory
  const fullPath = path.join(__dirname, 'shared_files', normalized);
  const sharedDir = path.join(__dirname, 'shared_files');
  
  if (!fullPath.startsWith(sharedDir)) {
    return null; // Invalid path, outside shared directory
  }
  
  return normalized;
}

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

// Configure storage
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    // Get current directory from query or default to root
    const uploadDir = req.query.dir ? 
      path.join(__dirname, 'shared_files', sanitizePath(req.query.dir)) : 
      path.join(__dirname, 'shared_files');
    
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    // Keep original filename but sanitize it
    cb(null, file.originalname.replace(/[^\w\s.-]/g, ''));
  }
});

// Set up upload middleware with limits
const upload = multer({
  storage: storage,
  limits: {
    fileSize: 100 * 1024 * 1024, // 100MB limit
  },
  fileFilter: (req, file, cb) => {
    // Optional: filter file types
    cb(null, true);
  }
});

// Modify the root route to support pagination
app.get('/', (req, res) => {
    const directoryPath = path.join(__dirname, 'shared_files');
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 50; // Files per page
    
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
        
        // Calculate pagination
        const totalFiles = files.length;
        const totalPages = Math.ceil(totalFiles / limit);
        const startIndex = (page - 1) * limit;
        const endIndex = Math.min(startIndex + limit, totalFiles);
        const paginatedFiles = files.slice(startIndex, endIndex);
        
        // Generate pagination controls
        let paginationHtml = '<div class="pagination">';
        if (page > 1) {
            paginationHtml += `<a href="?page=${page - 1}" class="page-link">Previous</a>`;
        }
        
        for (let i = 1; i <= totalPages; i++) {
            if (i === page) {
                paginationHtml += `<span class="page-current">${i}</span>`;
            } else {
                paginationHtml += `<a href="?page=${i}" class="page-link">${i}</a>`;
            }
        }
        
        if (page < totalPages) {
            paginationHtml += `<a href="?page=${page + 1}" class="page-link">Next</a>`;
        }
        paginationHtml += '</div>';
        
        // Generate HTML for file listing, but use paginatedFiles instead of files
        let fileList = '<ul>';
        paginatedFiles.forEach(file => {
            try {
                const filePath = path.join(directoryPath, file);
                const stats = fs.statSync(filePath);
                
                if (stats.isDirectory()) {
                    // This is a folder
                    fileList += `<li class="file-item folder-item">
                        <span class="file-type folder">Folder</span>
                        <span class="folder-icon">📁</span>
                        <a href="/browse/${file}">${file}</a>
                        <a href="/download-folder/${file}" class="download-folder-btn" 
                           data-folder="${file}">Download Folder</a>
                    </li>`;
                } else if (stats.isFile()) {
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
            files: paginatedFiles,
            fileList,
            pagination: paginationHtml,
            currentPage: page,
            totalPages: totalPages,
            backgroundImage,
            userBackgroundImage,
            backgroundBasename,
            greetingHeader,
            greetingSubheader,
            greetingEmpty
        });
    });
});

// Add a route to browse folders
app.get('/browse/:folder', (req, res) => {
    const folderName = req.params.folder;
    const folderPath = path.join(__dirname, 'shared_files', folderName);
    
    // Check if folder exists and is within the shared_files directory
    try {
        if (!fs.existsSync(folderPath) || !fs.statSync(folderPath).isDirectory()) {
            return res.status(404).send('Folder not found');
        }
        
        const currentUser = req.auth.user;
        const userBgPath = path.join(__dirname, 'assets', `background_${currentUser}.png`);
        const defaultBgPath = path.join(__dirname, 'assets', 'background.png');
        let backgroundImage = null;
        let userBackgroundImage = null;
        let backgroundBasename = '';

        if (fs.existsSync(defaultBgPath)) {
            backgroundImage = '/assets/background.png';
            backgroundBasename = 'background.png';
        }

        if (fs.existsSync(userBgPath)) {
            userBackgroundImage = `/assets/background_${currentUser}.png`;
        }
        
        fs.readdir(folderPath, (err, files) => {
            if (err) {
                console.error(`Error reading directory: ${err.message}`);
                return res.status(500).send('Error reading directory');
            }
            
            // Generate HTML for file listing
            let fileList = '<ul>';
            // Add parent directory link
            fileList += `<li class="file-item folder-item">
                <span class="file-type folder">Parent Directory</span>
                <span class="folder-icon">📁</span>
                <a href="/">Back to root</a>
            </li>`;
            
            files.forEach(file => {
                try {
                    const filePath = path.join(folderPath, file);
                    const stats = fs.statSync(filePath);
                    
                    if (stats.isDirectory()) {
                        // This is a subfolder
                        fileList += `<li class="file-item folder-item">
                            <span class="file-type folder">Folder</span>
                            <span class="folder-icon">📁</span>
                            <a href="/browse/${folderName}/${file}">${file}</a>
                            <a href="/download-folder/${folderName}/${file}" class="download-folder-btn" 
                               data-folder="${folderName}/${file}">Download Folder</a>
                        </li>`;
                    } else if (stats.isFile()) {
                        const fileSize = (stats.size / 1024).toFixed(2) + ' KB';
                        const fileType = getFileType(file);
                        const ext = path.extname(file).toLowerCase();
                        
                        const isImage = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].includes(ext);
                        let previewHtml = '';
                        
                        if (isImage) {
                            previewHtml = `<img class="thumbnail" src="/preview/${folderName}/${file}" alt="${file}" />`;
                        }
                        
                        fileList += `<li class="file-item">
                            <span class="file-type ${ext.substring(1) || 'generic'}">${fileType}</span>
                            ${previewHtml}
                            <a href="/download/${folderName}/${file}">${file}</a>
                            <span class="file-size">(${fileSize})</span>
                        </li>`;
                    }
                } catch (err) {
                    console.error(`Error processing file ${file}: ${err.message}`);
                }
            });
            fileList += '</ul>';
            
            // Get custom greeting messages from .env or use defaults
            let greetingHeader = process.env.FOLDER_GREETING_HEADER || "Browsing: {foldername}";
            const greetingSubheader = process.env.FOLDER_GREETING_SUBHEADER || "Contents of this folder:";
            const greetingEmpty = process.env.FOLDER_GREETING_EMPTY || "This folder is empty.";
            
            // Replace {foldername} placeholder with actual folder name
            greetingHeader = greetingHeader.replace('{foldername}', folderName);
            
            // Render the template with the data
            res.render('index', {
                files,
                fileList,
                backgroundImage,
                userBackgroundImage,
                backgroundBasename,
                greetingHeader,
                greetingSubheader: files.length > 0 ? greetingSubheader : greetingEmpty,
                greetingEmpty
            });
        });
    } catch (err) {
        console.error(`Error accessing folder ${folderName}: ${err.message}`);
        res.status(500).send('Error accessing folder');
    }
});

// Add a route to download folders as zip archives
app.get('/download-folder/:folderPath(*)', (req, res) => {
    const folderPath = req.params.folderPath;
    const fullFolderPath = path.join(__dirname, 'shared_files', folderPath);
    const socketId = req.query.socketId;
    
    // Check if the folder exists and is within the shared_files directory
    try {
        if (!fs.existsSync(fullFolderPath) || !fs.statSync(fullFolderPath).isDirectory()) {
            return res.status(404).send('Folder not found');
        }
        
        const folderName = path.basename(folderPath);
        const zipFileName = `${folderName}.zip`;
        
        // Set response headers
        res.setHeader('Content-Type', 'application/zip');
        res.setHeader('Content-Disposition', `attachment; filename="${zipFileName}"`);
        
        // Create zip archive
        const archive = archiver('zip', {
            zlib: { level: 5 } // Compression level
        });
        
        // Pipe the archive to the response
        archive.pipe(res);
        
        // Track progress
        let fileCount = 0;
        let totalFiles = 0;
        
        // Count total files first for progress tracking
        const countFiles = (dir) => {
            const entries = fs.readdirSync(dir);
            entries.forEach(entry => {
                const entryPath = path.join(dir, entry);
                if (fs.statSync(entryPath).isDirectory()) {
                    countFiles(entryPath);
                } else {
                    totalFiles++;
                }
            });
        };
        
        try {
            countFiles(fullFolderPath);
            
            // Emit initial progress
            if (socketId && io.sockets.sockets.get(socketId)) {
                io.to(socketId).emit('zipProgress', {
                    folder: folderName,
                    current: 0,
                    total: totalFiles,
                    percent: 0
                });
            }
        } catch (err) {
            console.error(`Error counting files: ${err.message}`);
        }
        
        // Progress event
        archive.on('entry', (entry) => {
            fileCount++;
            // Calculate percentage and ensure it doesn't exceed 100%
            const percent = Math.min(Math.round((fileCount / totalFiles) * 100), 100);
            
            // Emit progress via Socket.IO
            if (socketId && io.sockets.sockets.get(socketId)) {
                io.to(socketId).emit('zipProgress', {
                    folder: folderName,
                    current: fileCount,
                    total: totalFiles,
                    percent: percent
                });
            }
        });
        
        // Add folder contents to the archive
        archive.directory(fullFolderPath, folderName);
        
        // Finalize the archive
        archive.finalize();
        
        // Handle errors
        archive.on('error', (err) => {
            console.error(`Error creating zip archive: ${err.message}`);
            
            // Emit error
            if (socketId && io.sockets.sockets.get(socketId)) {
                io.to(socketId).emit('zipError', {
                    folder: folderName,
                    error: err.message
                });
            }
            
            res.end();
        });
        
        // Handle archive completion
        archive.on('end', () => {
            // Emit completion
            if (socketId && io.sockets.sockets.get(socketId)) {
                io.to(socketId).emit('zipComplete', {
                    folder: folderName
                });
            }
        });
    } catch (err) {
        console.error(`Error accessing folder ${folderPath}: ${err.message}`);
        res.status(500).send('Error accessing folder');
    }
});

// Replace the simple download route with a streaming version
app.get('/download/:folderPath(*)', (req, res) => {
  const folderPath = sanitizePath(req.params.folderPath);
  if (!folderPath) return res.status(403).send('Invalid path');
  
  const filePath = path.join(__dirname, 'shared_files', folderPath);
  
  try {
    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      const stat = fs.statSync(filePath);
      const fileSize = stat.size;
      const fileName = path.basename(filePath);
      
      // Handle range requests (resumable downloads)
      const range = req.headers.range;
      if (range) {
        const parts = range.replace(/bytes=/, '').split('-');
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunkSize = (end - start) + 1;
        
        res.writeHead(206, {
          'Content-Range': `bytes ${start}-${end}/${fileSize}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': chunkSize,
          'Content-Type': 'application/octet-stream',
          'Content-Disposition': `attachment; filename="${fileName}"`
        });
        
        const stream = fs.createReadStream(filePath, { start, end });
        stream.pipe(res);
      } else {
        // Normal download (entire file)
        res.writeHead(200, {
          'Content-Length': fileSize,
          'Content-Type': 'application/octet-stream',
          'Content-Disposition': `attachment; filename="${fileName}"`
        });
        
        const stream = fs.createReadStream(filePath);
        stream.pipe(res);
      }
    } else {
      res.status(404).send('File not found');
    }
  } catch (err) {
    console.error(`Error streaming file ${folderPath}: ${err.message}`);
    res.status(500).send('Error accessing file');
  }
});

// Add upload route
app.post('/upload', upload.array('files', 10), (req, res) => {
  // req.files is array of uploaded files
  // req.body will contain text fields if any
  
  res.json({
    success: true,
    files: req.files.map(f => ({
      filename: f.originalname,
      size: f.size
    }))
  });
});

// Also add a route to serve the assets folder
app.use('/assets', express.static(path.join(__dirname, 'assets')));

// Add this route before the server.listen call

// Handle image previews
app.get('/preview/:folderPath(*)', (req, res) => {
    const folderPath = req.params.folderPath;
    const filePath = path.join(__dirname, 'shared_files', folderPath);
    
    // Check if file exists and is within the shared_files directory
    try {
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            // Check if it's an image file
            const ext = path.extname(filePath).toLowerCase();
            if (['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'].includes(ext)) {
                res.sendFile(filePath);
            } else {
                res.status(400).send('Not an image file');
            }
        } else {
            res.status(404).send('File not found');
        }
    } catch (err) {
        console.error(`Error accessing file ${folderPath}: ${err.message}`);
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

// Add these routes before the server.listen

// Route for wiping the shared_files directory
app.post('/wipe-folder', (req, res) => {
    const sharedDir = path.join(__dirname, 'shared_files');
    
    try {
        // Check if directory exists first
        if (fs.existsSync(sharedDir)) {
            // Read all items in the directory
            const items = fs.readdirSync(sharedDir);
            
            // Delete each item
            for (const item of items) {
                const itemPath = path.join(sharedDir, item);
                
                // If directory, delete recursively
                if (fs.statSync(itemPath).isDirectory()) {
                    fs.rmdirSync(itemPath, { recursive: true });
                } else {
                    // If file, delete directly
                    fs.unlinkSync(itemPath);
                }
            }
            
            res.json({ success: true, message: 'Folder wiped successfully' });
        } else {
            // Directory doesn't exist, create it
            fs.mkdirSync(sharedDir, { recursive: true });
            res.json({ success: true, message: 'Folder created' });
        }
    } catch (err) {
        console.error(`Error wiping folder: ${err.message}`);
        res.status(500).json({ success: false, error: err.message });
    }
});

// Route to prepare an export of all files as a zip
app.get('/prepare-export', (req, res) => {
    const sharedDir = path.join(__dirname, 'shared_files');
    const exportDir = path.join(__dirname, 'exports');
    const exportFile = path.join(exportDir, 'ganymede-export.zip');
    
    try {
        // Ensure export directory exists
        if (!fs.existsSync(exportDir)) {
            fs.mkdirSync(exportDir, { recursive: true });
        } else {
            // Remove old export if it exists
            if (fs.existsSync(exportFile)) {
                fs.unlinkSync(exportFile);
            }
        }
        
        // Create a write stream to the export file
        const output = fs.createWriteStream(exportFile);
        const archive = archiver('zip', {
            zlib: { level: 5 } // Compression level
        });
        
        // Listen for all archive data to be written
        output.on('close', function() {
            console.log('Export created successfully, ' + archive.pointer() + ' total bytes');
            res.status(200).json({ success: true });
        });
        
        // Handle archive warnings
        archive.on('warning', function(err) {
            if (err.code === 'ENOENT') {
                console.warn('Archive warning:', err);
            } else {
                throw err;
            }
        });
        
        // Handle archive errors
        archive.on('error', function(err) {
            throw err;
        });
        
        // Pipe archive data to the file
        archive.pipe(output);
        
        // Add the shared_files directory contents to the archive
        archive.directory(sharedDir, false);
        
        // Finalize the archive
        archive.finalize();
    } catch (err) {
        console.error(`Error preparing export: ${err.message}`);
        res.status(500).json({ success: false, error: err.message });
    }
});

// Route to download the prepared export zip
app.get('/download-export', (req, res) => {
    const exportFile = path.join(__dirname, 'exports', 'ganymede-export.zip');
    
    try {
        if (fs.existsSync(exportFile)) {
            res.download(exportFile, 'ganymede-export.zip');
        } else {
            res.status(404).send('Export not found');
        }
    } catch (err) {
        console.error(`Error downloading export: ${err.message}`);
        res.status(500).send('Error accessing export');
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

// Set up Socket.IO
const io = socketIo(server);
io.on('connection', (socket) => {
    console.log('Client connected');
    
    socket.on('disconnect', () => {
        console.log('Client disconnected');
    });
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('Shutting down server...');
    server.close(() => {
        console.log('Server closed');
        process.exit(0);
    });
});
