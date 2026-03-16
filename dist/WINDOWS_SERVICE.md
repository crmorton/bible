# Running the Bible API as a Windows Service

There are two main ways to keep the server running in the background: **Task Scheduler** (quick and dirty) or as a **Windows Service** (recommended).

## Method 1: Windows Service (Recommended)

This method uses **WinSW** (Windows Service Wrapper) to run the Python server directly from your git repository. This is the most stable way to support multiple workers on Windows.

1. **Prepare the Service folder**:
   Ensure `dist\bible_server_service.xml` exists in your project.

2. **Download WinSW**:
   - Download the latest executable (e.g., `WinSW-x64.exe`) from the [WinSW GitHub Releases](https://github.com/winsw/winsw/releases).
   - Move it to the `dist\` folder in your project and rename it to `bible_server_service.exe`.

3. **Install the Service**:
   Open a terminal as **Administrator** and run:
   ```cmd
   cd /d C:\Projects\_dev-workspace\__Antigravity\bible\dist
   bible_server_service.exe install
   bible_server_service.exe start
   ```

   *Note: The service is configured to use the `.venv` in the parent directory of `dist\`.*

> **Performance:** When run on a networked machine (i7-8700 @ 1gbps w/ WORKERS=5), use CONCURRENT_REQUESTS=50 (1228 req/sec and 99.5% success), system performance is 35% CPU, 768MB RAM, 35Mbps Network Send

## Method 2: Task Scheduler

Build with `pyinstaller` using:

``` bash
pyinstaller --onefile --name bible_server --add-data "en_bcv_parser.js;." api.py
```

Create a Windows startup wrapper:

``` bat
@echo off
REM Adjust these as needed:
set PORT=9091
set DB_PATH=p:\services\bible\bible_v2.db
set LOAD_IN_MEMORY=true

REM Launch the bundled server executable
start "" "%~dp0\bible_server.exe"
```

Move files to `P:\services\bible`:

``` txt
dist\bible_server.exe
start_bible_server.bat
bible_v2.db
```

Import `bible_server_task.xml` into Task Scheduler.
