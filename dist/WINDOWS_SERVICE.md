# Creating a Windows Service

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

> **When run on a networked machine (i7-8700 @ 1gbps w/ WORKERS=5), use CONCURRENT_REQUESTS=50 (1228 req/sec and 99.5% successful)**
