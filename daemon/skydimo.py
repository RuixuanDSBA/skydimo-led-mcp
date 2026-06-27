"""
Skydimo LED Controller — manages the direct-COM daemon.

Usage:
  python skydimo.py <mode>         # Start/switch mode (reasoning/output/decision/idle/waiting_user/testing/success/error/off)
  python skydimo.py start [mode]   # Start the daemon (default: idle)
  python skydimo.py stop           # Stop the daemon
  python skydimo.py status         # Check daemon status
  python skydimo.py set-state <s>  # Write state to .ai_state file
"""
import sys, os, subprocess, time

import skydimo_config as cfg


def is_running():
    if not os.path.exists(cfg.PID_FILE):
        return False
    try:
        with open(cfg.PID_FILE) as f:
            pid = int(f.read().strip())
        result = subprocess.run(
            ['powershell', '-noprofile', '-c',
             f'$p = Get-CimInstance Win32_Process -Filter "ProcessId = {pid}"; '
             f'if ($p) {{ $p.CommandLine }}'],
            capture_output=True, text=True, timeout=5)
        if result.returncode != 0 or not result.stdout.strip():
            return False
        return 'skydimo_daemon.py' in result.stdout
    except Exception:
        return False


def start(mode='idle'):
    if is_running():
        print("Daemon already running.")
        return
    proc = subprocess.Popen(
        [sys.executable, cfg.DAEMON_SCRIPT, mode],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )
    with open(cfg.PID_FILE, 'w') as f:
        f.write(str(proc.pid))
    time.sleep(1.5)
    if is_running():
        print(f"Daemon started ({mode}).")
    else:
        print("Failed to start daemon.")


def stop():
    if not os.path.exists(cfg.PID_FILE):
        print("Not running.")
        return

    pid = None
    try:
        with open(cfg.PID_FILE) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        pass

    open(cfg.STOP_FILE, 'w').close()
    time.sleep(1.5)

    if pid:
        try:
            subprocess.run(
                ['powershell', '-noprofile', '-c',
                 f'Wait-Process -Id {pid} -Timeout 3 -ErrorAction SilentlyContinue'],
                capture_output=True, timeout=10)
        except Exception:
            pass

    if pid and is_running():
        subprocess.run(['powershell', '-noprofile', '-c',
                        f'Stop-Process -Id {pid} -Force'],
                       capture_output=True)
        time.sleep(0.5)

    if os.path.exists(cfg.PID_FILE):
        try:
            os.remove(cfg.PID_FILE)
        except OSError:
            pass
    if os.path.exists(cfg.STOP_FILE):
        try:
            os.remove(cfg.STOP_FILE)
        except OSError:
            pass
    print("Daemon stopped.")


def status():
    d = "running" if is_running() else "stopped"
    s = "stopped"
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SkyDimo.exe'],
                             capture_output=True, text=True).stdout
        if 'SkyDimo.exe' in out:
            s = "running"
    except Exception:
        pass
    print(f"Daemon: {d}")
    print(f"Skydimo: {s}")
    if os.path.exists(cfg.STATE_FILE):
        with open(cfg.STATE_FILE) as f:
            print(f"State: {f.read().strip()}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == 'start':
        mode = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in cfg.VALID_MODES else 'idle'
        start(mode)
    elif cmd == 'stop':
        stop()
    elif cmd == 'status':
        status()
    elif cmd == 'set-state':
        if len(sys.argv) < 3:
            print("Usage: python skydimo.py set-state <mode>")
            return
        val = sys.argv[2]
        if val not in cfg.VALID_MODES:
            print(f"Invalid mode: {val}. Valid: {', '.join(cfg.VALID_MODES)}")
            return
        with open(cfg.STATE_FILE, 'w') as f:
            f.write(val)
        print(f"State set: {val}")
    elif cmd in cfg.VALID_MODES:
        with open(cfg.STATE_FILE, 'w') as f:
            f.write(cmd)
        if not is_running():
            start(cmd)
        else:
            print(f"State: {cmd}")
    else:
        print(f"Unknown command: {cmd}")


if __name__ == '__main__':
    main()
