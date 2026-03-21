# AbletonMCP — Ableton Live + Claude Code Integration

A fork of [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) extended with a full-featured Claude Code mixing assistant: real-time meter levels, device parameter read/write, a custom Max4Live frequency analyzer, and an 8-step data-driven mixing workflow.

> **Original project** by [Siddharth Ahuja](https://x.com/sidahuj) — MIT License.
> Join the community: [Discord](https://discord.gg/3ZrMyGKnaU)

---

## What This Does

AbletonMCP connects Ableton Live to Claude AI through the Model Context Protocol (MCP), letting Claude directly control and compose within a Live session. This fork adds a structured mixing assistant layer on top of the core MCP — giving Claude the context it needs to make professional mixing decisions, not just programmatic track control.

## Features

### Core MCP (upstream)
- **Two-way communication** — socket-based connection between Claude and Ableton Live
- **Track control** — create, name, and manipulate MIDI and audio tracks
- **Browser access** — load instruments, effects, and presets from Ableton's library by URI
- **Clip editing** — create MIDI clips, add notes, set names and lengths
- **Session control** — playback, clip firing, tempo

### Mixing Assistant (this fork)
- **Real-time meter levels** — `get_track_levels` polls output meters across the whole session so Claude can audit gain staging instantly
- **Device parameter read/write** — `get_device_parameters` and `set_device_parameter` let Claude read EQ Eight bands, compressor GR, Utility gain/width, and apply targeted corrections directly
- **Max4Live frequency analyzer** — `AbletonMCP_Analyzer.amxd` is a custom M4L audio effect that runs a 6-band RMS analysis (Sub/Low/LoMid/Mid/HiMid/Hi) and exposes the results as Live parameters Claude can read
- **8-step mixing workflow** — gain staging audit → device inventory → HPF audit → frequency map → masking detection → trouble frequency check → apply corrections → verify; all from a Claude Code conversation
- **Distilled mixing reference** — Bobby Owsinski's EQ, dynamics, and mastering guidelines baked into `CLAUDE.md` as operating instructions Claude applies automatically

---

## Installation

### Prerequisites

- Ableton Live 10 or newer
- Python 3.10 or newer
- [uv](https://astral.sh/uv) — `brew install uv` on Mac

### Installing the Ableton Remote Script

1. Copy the `AbletonMCP_Remote_Script/` folder into Ableton's MIDI Remote Scripts directory:

   **macOS:**
   - `Applications → Right-click Ableton Live → Show Package Contents → Contents/App-Resources/MIDI Remote Scripts/`
   - or `~/Library/Preferences/Ableton/Live XX/User Remote Scripts/`

   **Windows:**
   - `C:\Users\[Username]\AppData\Roaming\Ableton\Live x.x.x\Preferences\User Remote Scripts\`
   - or `C:\ProgramData\Ableton\Live XX\Resources\MIDI Remote Scripts\`

2. Create a folder called `AbletonMCP` inside the Remote Scripts directory and place `__init__.py` inside it.

3. In Ableton: **Settings → Link, Tempo & MIDI → Control Surface → AbletonMCP**. Set Input and Output to None.

### Claude Code Integration (recommended)

Add to `~/.claude/mcp.json` to run the local repo directly (no PyPI download, always up to date):

```json
{
  "mcpServers": {
    "AbletonMCP": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ableton-mcp",
        "run",
        "ableton-mcp"
      ]
    }
  }
}
```

Replace `/path/to/ableton-mcp` with your local clone path. Claude Code will prompt to approve the server on first run.

### Claude Desktop Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "AbletonMCP": {
      "command": "uvx",
      "args": ["ableton-mcp"]
    }
  }
}
```

### Cursor Integration

Go to **Cursor Settings → MCP** and set the command to:

```
uvx ableton-mcp
```

> Only run one MCP server instance at a time (Claude Code, Claude Desktop, or Cursor — not multiple).

---

## Usage

1. Start Ableton Live with the Remote Script loaded (look for "AbletonMCP: Listening on port 9877" in the status bar)
2. Open Claude Code in your project directory
3. Approve the AbletonMCP server when prompted
4. Start giving instructions

### Example prompts

**Production:**
- "Add a MIDI track with a Wavetable bass synth and create a funky two-bar bass line in E minor"
- "Add a four-on-the-floor drum track with a 909 kit"
- "Add a lead synth with a melodic hook that leaves room to breathe"
- "Create an 80s synthwave track"
- "Add a Metro Boomin style hip-hop beat"

**Mixing:**
- "Check the EQ Eight settings on each track and flag any missing high-pass filters"
- "Read the gain levels across the session and flag anything that needs attention"
- "Scan all tracks for frequency masking and suggest targeted EQ cuts"
- "Run a full mix analysis and apply corrections"
- "Audit the HPF settings on every track against the standard cutoffs"

---

## Mixing Assistant

| Phase | What | Status |
|-------|------|--------|
| 1 | MCP extension: `get_track_levels`, `get_device_parameters`, `set_device_parameter` | ✅ Done |
| 2 | Max4Live 6-band RMS analyzer (`Max4Live/AbletonMCP_Analyzer.amxd`) | ✅ Done |
| 3 | Full CC mixing workflow (measure → analyze → fix → verify) | ✅ Done |
| 4 | Automated tests (24 unit tests, `uv run pytest`) | ✅ Done |

### Installing Everything

Run the setup script to install the Remote Script, M4L analyzer, and MCP server config in one step:

```bash
python install.py
```

Then restart Ableton and Claude Code.

To manually install just the Max4Live analyzer: drag `Max4Live/AbletonMCP_Analyzer.amxd` onto a track in Ableton as an audio effect.

---

## Project Structure

```
AbletonMCP_Remote_Script/   # Ableton MIDI Remote Script (socket server)
MCP_Server/                 # MCP server (Claude ↔ socket bridge)
Max4Live/                   # AbletonMCP Analyzer M4L device (6-band RMS)
tests/                      # Automated tests (uv run pytest)
CLAUDE.md                   # Operating instructions and mixing reference for Claude Code
MIXING_ASSISTANT_ROADMAP.md # Implementation history
```

---

## Troubleshooting

- **No connection** — confirm the Remote Script is loaded and Ableton shows "Listening on port 9877"
- **Tools not appearing in Claude Code** — approve the MCP server when prompted; restart the session if needed
- **Timeout errors** — break complex requests into smaller steps
- **Still broken** — restart both Ableton and Claude

---

## Contributing

PRs welcome. See the roadmap for the highest-value areas to contribute.

## License

MIT — see [LICENSE](LICENSE). Original project by [Siddharth Ahuja](https://github.com/ahujasid/ableton-mcp).
