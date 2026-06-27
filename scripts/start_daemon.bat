@echo off
REM Skydimo LED daemon auto-start on login
REM Uses the Python interpreter that has pyserial installed.
REM
REM If pyserial is in your main Python, just use "python".
REM If pyserial is in a venv, point to that venv's python.exe.
REM If mcp and pyserial are in separate environments, set SKYDIMO_DAEMON_PY.

set SKYDIMO_DAEMON_PY=python
start "" /B %SKYDIMO_DAEMON_PY% "%~dp0daemon\skydimo.py" start idle
