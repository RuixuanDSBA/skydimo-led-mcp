@echo off
REM Skydimo LED daemon auto-start on login
REM Uses the venv Python (has both mcp and pyserial)
start "" /B "C:\Users\alexr\.workbuddy\binaries\python\envs\default\Scripts\python.exe" "C:\Users\alexr\skydimo-led-mcp\daemon\skydimo.py" start idle
