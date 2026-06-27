"""
Bridge between MCP server and the Skydimo LED daemon.
Delegates all operations to the CLI under daemon/.

Auto-healing: if the daemon isn't running when set_led_state is called,
the bridge starts it automatically.

Environment variables:
  SKYDIMO_DIR         - Override the daemon directory (default: ./daemon)
  SKYDIMO_DAEMON_PY   - Python interpreter for the daemon (needs pyserial).
                        Defaults to sys.executable. Set this only if mcp and
                        pyserial are installed in separate Python environments.
"""
import os
import sys
import subprocess

# Resolve daemon directory: env var > relative to this file > fallback
_HERE = os.path.dirname(os.path.abspath(__file__))
SKYDIMO_DIR = os.environ.get("SKYDIMO_DIR", os.path.join(_HERE, "daemon"))
SKYDIMO_CLI = os.path.join(SKYDIMO_DIR, "skydimo.py")
STATE_FILE = os.path.join(SKYDIMO_DIR, ".ai_state")
PID_FILE = os.path.join(SKYDIMO_DIR, ".skydimo_daemon.pid")

# Python interpreter for the daemon (needs pyserial).
# On most setups sys.executable works. If mcp and pyserial are in different
# environments, set SKYDIMO_DAEMON_PY to the interpreter that has pyserial.
DAEMON_PYTHON = os.environ.get("SKYDIMO_DAEMON_PY", sys.executable)

VALID_MODES = ("reasoning", "output", "decision", "idle", "waiting_user",
               "testing", "success", "error", "off")


def _run_cli(*args, python=None):
    """Run skydimo.py CLI with the specified Python interpreter."""
    py = python or sys.executable
    result = subprocess.run(
        [py, SKYDIMO_CLI, *args],
        capture_output=True, text=True, timeout=15,
        cwd=SKYDIMO_DIR,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _is_daemon_running() -> bool:
    """Quick check: does the PID file exist and is the process alive?"""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        result = subprocess.run(
            ['powershell', '-noprofile', '-c',
             f'$p = Get-CimInstance Win32_Process -Filter "ProcessId = {pid}"; '
             f'if ($p) {{ $p.CommandLine }}'],
            capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and 'skydimo_daemon.py' in result.stdout
    except Exception:
        return False


def _ensure_daemon_running(mode: str = "idle") -> bool:
    """Start the daemon if it's not already running (uses DAEMON_PYTHON)."""
    if _is_daemon_running():
        return True
    rc, out, err = _run_cli("start", mode, python=DAEMON_PYTHON)
    return rc == 0


def set_led_state(mode: str) -> str:
    if mode not in VALID_MODES:
        return f"Invalid mode: {mode}. Valid: {', '.join(VALID_MODES)}"
    # Auto-heal: start daemon if not running (except for 'off' mode)
    if mode != "off":
        _ensure_daemon_running(mode)
    rc, out, err = _run_cli("set-state", mode)
    if rc != 0:
        return f"Failed: {err or out}"
    return out


def start_daemon(mode: str = "idle") -> str:
    if mode not in VALID_MODES:
        mode = "idle"
    rc, out, err = _run_cli("start", mode, python=DAEMON_PYTHON)
    if rc != 0:
        return f"Failed: {err or out}"
    return out


def stop_daemon() -> str:
    rc, out, err = _run_cli("stop", python=DAEMON_PYTHON)
    if rc != 0:
        return f"Failed: {err or out}"
    return out


def get_status() -> dict:
    rc, out, err = _run_cli("status", python=DAEMON_PYTHON)
    result = {
        "daemon": "unknown",
        "skydimo_app": "unknown",
        "state": "unknown",
        "raw": out,
    }
    for line in out.splitlines():
        if line.startswith("Daemon:"):
            result["daemon"] = line.split(":", 1)[1].strip()
        elif line.startswith("Skydimo:"):
            result["skydimo_app"] = line.split(":", 1)[1].strip()
        elif line.startswith("State:"):
            result["state"] = line.split(":", 1)[1].strip()
    return result


def get_available_modes() -> list:
    return list(VALID_MODES)
