@echo off
REM Adjust these as needed:
set PORT=9091
set DB_PATH=p:\services\bible\bible_v2.db
set LOAD_IN_MEMORY=true
set WORKERS=1
set UVICORN_RELOAD=false

REM Launch the bundled server executable
start "" "%~dp0\bible_server.exe"

REM Optionally, you can also launch the server using Python directly:
REM python "%~dp0\api.py"
