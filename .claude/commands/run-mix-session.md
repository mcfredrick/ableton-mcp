---
name: run-mix-session
description: Start a data-driven CC mixing session on the current Ableton Live project
---

Start a CC mixing session on the open Ableton Live project. Follow the steps below exactly and in order.

---

## Environment check (do this first, silently)

Verify the Remote Script is responding by sending `get_session_info` via direct socket. If the connection fails or returns an unknown command error, the Remote Script needs updating — see **Troubleshooting** below before proceeding.

```python
import socket, json, time

def cmd(s, ctype, params={}):
    s.sendall(json.dumps({'type': ctype, 'params': params}).encode())
    time.sleep(0.4)
    s.settimeout(15.0)
    chunks = []
    while True:
        try:
            chunk = s.recv(65536)
            if not chunk: break
            chunks.append(chunk)
            try:
                return json.loads(b''.join(chunks).decode())
            except json.JSONDecodeError:
                continue
        except socket.timeout:
            break
    return {}

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', 9877))
```

Test commands in order: `get_session_info`, `get_track_levels`, `get_rack_devices`. If any return "Unknown command", the wrong Remote Script version is loaded — see Troubleshooting.

---

## Step 0 — Session snapshot

Save a pre-mix baseline:

```python
import datetime, os, json
snapshot = {'label': 'pre-mix', 'timestamp': datetime.datetime.now().isoformat()}
# add session info, levels, volumes
os.makedirs('/Users/matt/Code/ableton-mcp/sessions', exist_ok=True)
ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
# write to sessions/snapshot-{ts}-pre-mix.json
```

## Step 1 — Device inventory

For each track, call `get_track_info(track_index)`. Check for:
- **"Basic Chain FF Gain Reduction"** rack (class: `AudioEffectGroupDevice`) — present on most tracks
- Use `get_rack_devices(track_index, rack_device_index)` to inspect inside the rack — it contains FabFilter Pro-Q 3, Pro-C 2, Glue Compressor, and Utility
- **AbletonMCP Analyzer** (name contains "AbletonMCP", class contains "MaxDevice") — load with `load_analyzer_device(track_index)` on any track missing it. Do this automatically, do not ask.

Note all device indices for subsequent steps.

## Step 2 — Run level + frequency sampling

Once analyzers are loaded on all tracks, run the sampling script from the repo directory:

```bash
cd /Users/matt/Code/ableton-mcp
python sample_levels.py --duration 90
```

This starts Ableton playback, samples `get_track_levels` every 200ms and `get_all_analyzer_levels` every 2s, then stops and writes `sessions/levels-{timestamp}.json`. Use `--duration` long enough to cover the whole arrangement. Read the output file — it is the data source for all steps below.

**Gain staging flags from the levels JSON:**
- `peak_max_dbfs > -6` → too hot, needs gain reduction
- `active_ratio > 0.05` and `peak_max_dbfs < -20` → too quiet

## Step 3 — HPF audit

Use `get_rack_devices` to read the FabFilter Pro-Q 3 inside each track's rack. Find the HPF band and compare against:
- Kick / bass / floor tom: 40 Hz
- Most instruments: 80–100 Hz
- Hi-hats / cymbals: 250–500 Hz

Apply corrections via `set_rack_device_parameter(track_index, rack_device_index, chain_index, chain_device_index, parameter_index, value)`.

## Step 4 — Frequency map

Build a table from `freq_avg` in the levels JSON:

```
Track | Sub | Low | LoMid | Mud | Pres | Upper | Def | Bril | Air
```

The 9-band analyzer centers: Sub 40Hz · Low 110Hz · LoMid 316Hz · Mud 700Hz · Presence 1500Hz · Upper 3000Hz · Definition 5000Hz · Brilliance 9000Hz · Air 14000Hz.

## Step 5 — Masking detection

Flag any band where more than one track has `freq_avg > -20 dB`. State track names, band, and dB levels. Propose specific cuts (e.g. "Cut 2 dB at 316 Hz on Kick, Q 3").

## Step 6 — Trouble frequency check

Per active track (`active_ratio > 0.05`), cross-reference `freq_avg` against:
- LoMid (316 Hz): > -20 dB → muddiness → narrow cut
- Mud (700 Hz): > -18 dB → boxy/"Walmart" harshness → cut
- Presence (1.5 kHz): elevated → nasal/harsh → cut 1–2 dB
- Upper/Definition (3–5 kHz): low → lacks presence → boost 1–2 dB wide Q
- Brilliance/Air (9–14 kHz): low → dull → gentle shelf boost

## Step 7 — Apply corrections

Present all findings and proposed moves. After user confirmation, apply with `set_rack_device_parameter`. Always call `get_rack_devices` first to read current values and verify parameter indices and min/max bounds.

## Step 8 — Verify and sign off

Re-run `python sample_levels.py --duration 30` after corrections. Compare `freq_avg` and `peak_max_dbfs` to the pre-correction run. Present the Mastering Prep Checklist:

- [ ] No over-EQ (better slightly dull than too bright or too heavy)
- [ ] No over-compression on the bus
- [ ] Peaks at –10 to –6 dBFS on the mix output
- [ ] Phase/mono compatibility checked
- [ ] Fades and tails have breathing room
- [ ] Export at same resolution as recording

---

## Troubleshooting

### "Unknown command: get_track_levels" (or any newer command)

Ableton is loading a stale Remote Script. Fix:

```bash
cd /Users/matt/Code/ableton-mcp
python3 install.py   # copies updated script to app bundle + User Library
```

Then **fully quit and relaunch Ableton** — control surface reload alone does NOT work. Ableton caches the module in `sys.modules`; only a full restart re-imports from disk.

The Remote Script lives in the **app bundle**, not the User Library:
```
/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP/__init__.py
```
`install.py` handles this automatically (it detects and writes to the app bundle first).

### Connection refused on port 9877

Ableton is not running, or the AbletonMCP control surface is not set. In Ableton: Preferences → Link/Tempo/MIDI → Control Surface → select AbletonMCP.

### All tracks show zero level during sampling

The arrangement playhead is at a silent section. Either let the script run longer (`--duration 180`) or reposition the playhead to a full section before running.

### `get_rack_devices` returns empty chains

The track's rack may use a Chain Selector to switch chains. Read `Chain Selector` macro value first and adjust if needed.

---

## Key facts about this project

- **73 tracks** in arrangement (timeline) mode — not clip launcher
- Most tracks use **"Basic Chain FF Gain Reduction"** audio effect rack containing FabFilter Pro-Q 3, Pro-C 2, Glue Compressor, Utility — use `get_rack_devices` / `set_rack_device_parameter` for all EQ and compression work
- Track faders are at unity (0 dB) across the board — do not use fader positions for gain staging
- Instantaneous meter readings (`get_track_levels`) are only meaningful during playback — use `sample_levels.py` for all level analysis
- The AbletonMCP Analyzer is a 9-band M4L device; use `get_all_analyzer_levels` for bulk reads
- Tempo: 140 BPM
