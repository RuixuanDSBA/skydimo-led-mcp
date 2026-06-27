"""
Skydimo shared configuration — single source of truth for modes, paths, and ports.
All hardware parameters are configurable via environment variables.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DAEMON_SCRIPT = os.path.join(BASE_DIR, 'skydimo_daemon.py')
PID_FILE = os.path.join(BASE_DIR, '.skydimo_daemon.pid')
STATE_FILE = os.path.join(BASE_DIR, '.ai_state')
STOP_FILE = os.path.join(BASE_DIR, '.skydimo_daemon.stop')

# Hardware parameters — override via environment variables if needed
PORT = os.environ.get('SKYDIMO_PORT', 'COM4')
BAUDRATE = int(os.environ.get('SKYDIMO_BAUDRATE', '115200'))
NUM_LEDS = int(os.environ.get('SKYDIMO_NUM_LEDS', '54'))

VALID_MODES = (
    'reasoning',
    'output',
    'decision',
    'idle',
    'waiting_user',
    'testing',
    'success',
    'error',
    'off',
)
