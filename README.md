# Skydimo LED MCP Server

Turn a physical RGB LED strip into a real-time status indicator for AI coding assistants.

When your AI is thinking, the lights flow rainbow. When it's writing code, green beams chase across the strip. When tests fail, red pulses fire. You glance at your desk — you know what's happening, without looking at the screen.

## How It Works

```
AI Tool (WorkBuddy, Claude Code, opencode, etc.)
  │  MCP protocol (stdio)
  ▼
server.py  ──→  skydimo_bridge.py  ──→  daemon/skydimo.py
  │                                          │
  │                                     writes .ai_state file
  │                                          │
  ▼                                          ▼
MCP tools/resources              daemon/skydimo_daemon.py
                                      │  reads .ai_state (~100ms poll)
                                      │  renders animation (~40fps)
                                      ▼
                                 COM4 (Adalight protocol)
                                      │
                                      ▼
                              Skydimo SK0124 LED Strip ✨
```

The MCP server exposes tools that an AI assistant can call. Each tool call writes a state name to a file. A background daemon polls that file and switches the LED animation instantly (~162ms total latency).

## 9 LED Modes

| Mode | Effect | When to use |
|------|--------|-------------|
| `reasoning` | Rainbow flowing | AI is thinking / processing |
| `output` | Green chasing beams | Streaming output / writing files |
| `decision` | Red rapid breathing | Needs user decision / code review |
| `idle` | Teal breathing (slow) | Idle / waiting / done |
| `waiting_user` | Teal + white sparkle | Waiting for user reply |
| `testing` | Blue-white scanner | Running tests / verification |
| `success` | Green wave + sparkle | Tests passed / task completed |
| `error` | Red double pulse | Error / command failed |
| `off` | All off | Turn off lights |

## Hardware Requirements

- **LED Strip:** Skydimo SK0124 (54 RGB LEDs)
- **Connection:** CH340 USB-Serial adapter
- **Protocol:** Adalight (`Ada` header + LED count + RGB data)
- **Default port:** COM4, 115200 baud

> All hardware parameters are configurable via environment variables (see below).

## Acknowledgments & Prior Art

This project builds on the work of the open-source RGB lighting community:

- **[OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB)** — The large open-source RGB lighting control project. Our Adalight protocol implementation follows the same standard that OpenRGB uses for addressable LED strips.

- **[Skydimo OpenRGB](https://gitlab.com/skydimo-team/skydimo-open-rgb)** — Skydimo (the manufacturer of the SK0124 LED strip) maintains a fork of OpenRGB with device-specific optimizations. Their work informed the serial parameters and frame format used in this project's daemon.

- **[Skydimo](https://skydimo.com)** — Manufacturer of the SK0124 RGB LED strip hardware used in this project.

This project does **not** depend on or embed OpenRGB or Skydimo's software. The daemon (`daemon/skydimo_daemon.py`) is a standalone Python implementation that talks directly to the serial port using the Adalight protocol. However, the protocol knowledge and hardware parameters are derived from the above projects.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `mcp` and `pyserial` can be in the same Python environment. If they must be separate (e.g., MCP server runs in a managed venv but pyserial is only in system Python), set the `SKYDIMO_DAEMON_PY` environment variable to point to the interpreter that has pyserial.

### 2. Start the daemon

```bash
python daemon/skydimo.py start idle
```

The LED strip should light up with teal breathing.

### 3. Configure your MCP client

Add to your MCP client config (e.g., `~/.workbuddy/mcp.json` for WorkBuddy):

```json
{
  "mcpServers": {
    "skydimo-led": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/skydimo-led-mcp/server.py"],
      "description": "Physical LED strip status indicator for AI activity"
    }
  }
}
```

For Claude Code, add to `~/.claude.json`. For opencode, add to `opencode.jsonc`.

### 4. Test it

Tell your AI assistant: *"Set the LED to reasoning mode."*

The strip should switch to rainbow flowing.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKYDIMO_PORT` | `COM4` | Serial port (e.g., `COM4`, `/dev/ttyUSB0`) |
| `SKYDIMO_BAUDRATE` | `115200` | Serial baud rate |
| `SKYDIMO_NUM_LEDS` | `54` | Number of LEDs on the strip |
| `SKYDIMO_DIR` | `./daemon` | Path to the daemon directory |
| `SKYDIMO_DAEMON_PY` | `sys.executable` | Python interpreter for the daemon (must have pyserial) |

## Project Structure

```
skydimo-led-mcp/
├── server.py                 # MCP server (stdio transport) — 4 tools + 3 resources
├── skydimo_bridge.py         # Bridge: MCP server → daemon CLI (with auto-heal)
├── index.html                # Bilingual documentation page (= skydimo://help resource)
├── requirements.txt          # Python dependencies (mcp + pyserial)
├── daemon/
│   ├── skydimo_daemon.py     # Background daemon: COM4 + LED animation rendering
│   ├── skydimo.py            # CLI entry point (start/stop/status/set-state)
│   └── skydimo_config.py     # Shared config (paths, ports, modes — env var configurable)
├── scripts/
│   └── start_daemon.bat      # Windows auto-start script (for Startup folder)
├── LICENSE                   # MIT
└── .gitignore
```

## MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `set_led_state` | Switch LED to a visual mode | `mode` (required): one of 9 modes |
| `start_daemon` | Start the background daemon | `mode` (optional, default `idle`) |
| `stop_daemon` | Stop daemon gracefully (sends off frame) | none |
| `get_status` | Query daemon status and current LED state | none |

## MCP Resources

| URI | Content |
|-----|---------|
| `skydimo://status` | Plain-text status (daemon running? current state) |
| `skydimo://modes` | JSON list of valid mode names |
| `skydimo://help` | HTML documentation page |

## Daemon Auto-Start (Windows)

Copy `scripts/start_daemon.bat` to your Windows Startup folder (`Win+R` → `shell:startup`) so the daemon launches on login.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB) — Open-source RGB lighting control
- [Skydimo OpenRGB](https://gitlab.com/skydimo-team/skydimo-open-rgb) — Skydimo's device-optimized fork
- [Skydimo](https://skydimo.com) — Hardware manufacturer
- [Model Context Protocol](https://modelcontextprotocol.io) — MCP specification
