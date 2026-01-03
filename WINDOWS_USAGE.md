# DIN 12831 Heizlast - Windows Standalone Executable

## Installation

No installation required! Just download the executable.

## Running the Application

### Option 1: Double-Click (Recommended)
1. Double-click `din12831-heatload.exe`
2. A console window will open showing the server status
3. Your default web browser will automatically open to `http://localhost:8501`
4. If the browser doesn't open automatically, manually navigate to `http://localhost:8501`

### Option 2: Command Line
1. Open Command Prompt or PowerShell
2. Navigate to the folder containing `din12831-heatload.exe`
3. Run: `din12831-heatload.exe`
4. Open your browser to `http://localhost:8501`

## Stopping the Application

- Close the console window, or
- Press `Ctrl+C` in the console window

## Troubleshooting

### Port Already in Use
If you see an error that port 8501 is already in use:
- Close any other running instances of the application
- Or use a different port by running: `din12831-heatload.exe --server.port=8502`

### Browser Doesn't Open
- Manually open your browser and navigate to `http://localhost:8501`
- Make sure no firewall is blocking the application

### Application Won't Start
- Make sure you're running Windows 10 or newer
- Try running as Administrator (right-click → "Run as administrator")
- Check Windows Defender or antivirus isn't blocking the executable

## System Requirements

- Windows 10 or newer
- 4 GB RAM minimum
- Modern web browser (Chrome, Firefox, Edge)

## Notes

- The application runs a local web server on your computer
- No internet connection required after download
- Your data stays on your computer
- The console window must remain open while using the app
