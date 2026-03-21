# context-mode — MANDATORY routing rules

Raw tool output floods context. These rules are not optional.

**BLOCKED** — do not retry, use the sandbox alternative instead:
- `curl` / `wget` → `ctx_fetch_and_index(url, source)`
- inline HTTP in Bash → `ctx_execute(language, code)`
- `WebFetch` → `ctx_fetch_and_index(url, source)` then `ctx_search(queries)`

**REDIRECTED** — use sandbox equivalents for large output:
- Bash (>20 lines) → `ctx_batch_execute(commands, queries)` or `ctx_execute(language: "shell", code: "...")`
- Read for analysis → `ctx_execute_file(path, language, code)` (Read is correct only when editing)
- Grep (large results) → `ctx_execute(language: "shell", code: "grep ...")`

**Tool hierarchy:** GATHER `ctx_batch_execute` → FOLLOW-UP `ctx_search` → PROCESS `ctx_execute` / `ctx_execute_file` → WEB `ctx_fetch_and_index`

Subagents inherit routing automatically. Keep responses under 500 words. Write artifacts to files, never inline.

| ctx command | Action |
|-------------|--------|
| `ctx stats` | Call `ctx_stats` MCP tool, display verbatim |
| `ctx doctor` | Call `ctx_doctor`, run shell command, display as checklist |
| `ctx upgrade` | Call `ctx_upgrade`, run shell command, display as checklist |

---

## Python Development Standards

This project has **two separate Python environments** — never mix their conventions:

| Component | Environment | Constraints |
|-----------|-------------|-------------|
| `AbletonMCP_Remote_Script/` | Ableton's embedded Python (2/3 compat) | No pip packages; use only stdlib + `_Framework`; `from __future__ import` guards required |
| `MCP_Server/` | Standard Python 3 via `uv` | Full pip ecosystem; FastMCP; type hints encouraged |

**Remote Script rules:**
- Maintain Python 2/3 compatibility (`try: import Queue` pattern, `.encode('utf-8')` guards)
- All Live API calls that modify state **must** run on the main thread via `self.schedule_message(0, fn)` with a `queue.Queue` for the response
- Read-only Live API calls (meter levels, parameter reads) can run directly on the socket thread
- Never import third-party packages

**MCP Server rules:**
- Each tool function must have a clear docstring explaining parameters and return shape
- Add new command types to `is_modifying_command` if they change Live state
- Return `json.dumps(result, indent=2)` for structured data; plain string for simple confirmations

**Running tests:**
```bash
uv run pytest          # all 24 unit tests (no Ableton required)
uv run pytest -v       # verbose output
```
Unit tests cover: M4L patch generator math and structure, MCP server tool routing, Remote Script method logic. Integration tests (live Ableton session) are not automated — test manually with a real session.

---

# Ableton MCP

## Architecture

Two components communicate over a TCP socket:
- **Remote Script** (`AbletonMCP_Remote_Script/__init__.py`) — runs inside Ableton Live, listens on `localhost:9877`
- **MCP Server** (`MCP_Server/server.py`) — implements MCP protocol, proxies commands to the socket

The MCP server is configured globally in `~/.claude/mcp.json` using `uv --directory /Users/matt/Code/ableton-mcp run ableton-mcp`, which runs the local repo directly. In Claude Code sessions the MCP tools should be available natively; if not, drive Ableton via Python socket.

## Direct Socket Pattern

```python
import socket, json, time

def cmd(s, ctype, params={}):
    s.sendall(json.dumps({'type': ctype, 'params': params}).encode())
    time.sleep(0.35)
    s.settimeout(15.0)
    chunks = []
    while True:
        try:
            chunk = s.recv(32768)
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

## Critical Workflow Rules

- **Always capture the track index** returned by `create_midi_track` — never assume index 0. Existing projects may already have many tracks.
- **Load order matters**: instrument first, then effects in signal-chain order.
- **`get_session_info` may not reflect track counts accurately** — use `get_track_info` by index.
- **Verify clips with `fire_clip`** after creation — `get_track_info` clips list is unreliable.
- State-modifying commands need ~300–500ms recovery time.

## Browser & URIs

Path format for `get_browser_items_at_path`: lowercase category, slash-separated subfolders.

```
instruments/Wavetable/Bass       instruments/Operator/Synth Lead
instruments/Meld/Pad             drums       audio_effects
```

URI format (use with `load_browser_item`):
```
query:Synths#Wavetable:Bass:FileId_112746      # Basic Reese Bass
query:AudioFx#EQ%20Eight                       # EQ Eight
query:AudioFx#Glue%20Compressor
query:Drums#FileId_112978                      # 909 Core Kit
```

Always browse first to get the correct FileId — don't guess URIs.

## Key Devices

| Category | Notable presets |
|----------|----------------|
| Wavetable Bass | Basic Reese Bass, Basic Saw Bass, Basic 303 Bass, Basic FM House Bass |
| Operator Bass | Acid Bass, Basic Sub Sine, Boom Bass |
| Wavetable Lead | Bright SAW Lead, Basic Glide Lead, Basic OG Lead |
| Drums | 909 Core Kit, 808 Boom Kit, 808 Core Kit, AG Techno Kit, Beastly Kit |
| Effects | EQ Eight, Glue Compressor, Compressor, Drum Buss, Saturator, Hybrid Reverb, Delay, Multiband Dynamics, Limiter, Utility, Auto Filter, Spectrum |

## MIDI Notes Reference

| Note | Pitch | Common use |
|------|-------|------------|
| C1   | 36    | Kick (Drum Rack) |
| D1   | 38    | Snare |
| F#1  | 42    | Closed hi-hat |
| A#1  | 46    | Open hi-hat |
| E2   | 40    | Bass root (common) |
| E5   | 76    | Lead melody range |

---

# Mixing Assistant

## Standard Track Setup (load on every track during mixing)

Always add these devices in this order after the instrument/sound source:

1. **EQ Eight** — surgical correction and frequency carving
2. **Utility** — gain staging, width control, mono check (flip phase to check compatibility)
3. **Spectrum** — visual frequency reference for CC analysis sessions

Add **AbletonMCP Analyzer** (Max4Live) after Spectrum once installed — see Frequency Analysis (Phase 2) below.

## Mixing Philosophy (Bobby Owsinski)

**Think tall, deep, and wide:**
- **Tall** — all frequencies from sub to air represented in correct proportions
- **Deep** — depth created with reverb and delay; use sends not inserts
- **Wide** — bass and kick mono, pads wide, leads slightly wide

**A mix must be interesting, not just technically correct.** It should build to a climax, with tension and release. Find the direction of the song, identify the groove instrument and build around it, find the most important element and emphasize it.

**Seven signs of an amateur mix** (eliminate all of these):
1. No contrast — same texture throughout
2. No focal point — holes between phrases with nothing holding attention
3. Noisy — clicks, hums, count-offs left in
4. Lacks clarity and punch — low end too heavy or too light
5. Distant and reverb-soaked — effects overused, sounds intimate
6. Inconsistent levels — faders set and forgotten; every note must be heard
7. Dull, generic sounds — use something the listener hasn't heard before

## EQ Rules

**HPF (High-Pass Filter) — apply to almost everything:**
| Element | HPF cutoff |
|---------|-----------|
| Kick, bass, floor tom | 40 Hz |
| Most instruments | 80–100 Hz |
| Hi-hats, cymbals | 250–500 Hz |
More tracks in the arrangement = more aggressive HPF on each.

**The 6 trouble frequencies to check on every track:**
| Frequency | Problem | Fix |
|-----------|---------|-----|
| 200 Hz | Muddy, boomy | Narrow cut (Q 4–5), a few dB |
| 300–500 Hz | Boxy, "beach ball" kick | Cut a few dB, check kick especially |
| 800 Hz | "Walmart" — cheap, harsh | Cut |
| 1.5 kHz | Nasal | Cut 1–2 dB |
| 4–6 kHz | Buried, lacks definition | Boost 1–2 dB, wide Q (1–1.5) to bring forward |
| 10 kHz+ | No air, no realness | Gentle shelf boost |

**Bonus: 50–150 Hz (boom zone)**
- Girth lives at 50–60 Hz (add 1–2 dB for kick and bass)
- Audibility on small speakers comes from 100–150 Hz — don't neglect this range
- Boosting below 100 Hz for "more bass" is a common mistake; listeners on small speakers won't hear it

**EQ Juggling for clarity:**
- No two tracks boosted at the same frequency — one will mask the other
- Boost where another track cuts (if kick is cut at 240 Hz, boost bass there)
- Always EQ in context of the full mix — never solo only
- Cuts are more powerful than boosts; start by cutting problem frequencies

## Dynamics

**Compression philosophy:**
- Attack controls transient response — slow attack lets drums punch through; fast attack catches and reduces them
- Release too fast = pumping; too slow = lowered perceived volume
- Over-compression is audible when quiet passages are too loud and noisy
- Do not over-compress the stereo bus — leave dynamics for mastering

**Per-element guidelines:**
- **Drums**: Glue Compressor (ratio 2:1–4:1, slow attack to preserve transients) + Drum Buss for saturation and sub
- **Bass**: Compressor with medium attack (let transient through), fast release tempo-tied; sidechain to kick to prevent low-end collision
- **Leads/pads**: Light compression for consistency, not squeeze — let dynamics breathe
- **Stereo bus**: Subtle Glue Compressor (1–2 dB GR max) + Limiter at –0.3 dBTP ceiling

## Gain Staging & Levels

- Print mixes with peaks at –10 to –6 dBFS — leave headroom for mastering
- Do not chase hot levels at the mix stage; that's what mastering is for
- Match perceived loudness across tracks using ears, not just meters
- Check mono compatibility with Utility (Width = 0): if elements disappear, something is out of phase

## Mastering Prep Checklist

- [ ] No over-EQ (better slightly dull than too bright or too heavy)
- [ ] No over-compression on the bus (leave dynamics intact)
- [ ] Peaks at –10 to –6 dBFS on the mix output
- [ ] Phase/mono compatibility checked (lead elements survive mono)
- [ ] Fades and tails have breathing room (don't trim reverb tails)
- [ ] Export at same resolution as recording (96kHz/24-bit stays 96kHz/24-bit)
- [ ] Alternate mixes made: vocal up +0.5dB and +1dB

## Signal Chain Order

```
Instrument / Sound Source
  → EQ Eight      (HPF + surgical cuts first)
  → Saturator     (if adding harmonics/grit)
  → Compressor    (dynamics after tone is shaped)
  → Utility       (gain staging, width, phase check)
  → Spectrum      (visual reference)
  → AbletonMCP Analyzer
  → Send → Reverb bus
  → Send → Delay bus
```

Drums:
```
Drum Rack
  → Drum Buss     (transient shaping, sub reinforcement)
  → Glue Compressor (bus glue)
  → Utility
  → Spectrum
  → AbletonMCP Analyzer
```

---

## Reading Live Data (Phase 1)

These MCP tools give CC real-time data from the session — not rule-of-thumb advice.

### `get_track_levels`

No parameters. Returns output meter levels (0.0–1.0) for every track, return track, and master.

```json
{
  "tracks": [
    { "index": 0, "name": "Bass", "output_meter_left": 0.42, "output_meter_right": 0.44, "output_meter_peak": 0.44 },
    ...
  ],
  "return_tracks": [...],
  "master": { "output_meter_left": 0.71, "output_meter_right": 0.69, "output_meter_peak": 0.71 }
}
```

Note: meter values are instantaneous snapshots — call during playback for meaningful readings.
Values above ~0.89 (approx –1 dBFS) on any track indicate a hot signal that needs gain staging.

### `get_device_parameters`

Parameters: `track_index`, `device_index`

Returns all parameters for the specified device: index, name, current value, min, max, is_quantized.

```json
{
  "device_name": "EQ Eight",
  "class_name": "Eq8",
  "parameters": [
    { "index": 0, "name": "1 Filter Active", "value": 1.0, "min": 0.0, "max": 1.0, "is_quantized": true },
    { "index": 1, "name": "1 Frequency A",   "value": 80.0, "min": 10.0, "max": 22000.0, "is_quantized": false },
    { "index": 2, "name": "1 Gain A",        "value": 0.0,  "min": -15.0, "max": 15.0, "is_quantized": false },
    { "index": 3, "name": "1 Resonance A",   "value": 0.71, "min": 0.1, "max": 9.9, "is_quantized": false },
    ...
  ]
}
```

### `set_device_parameter`

Parameters: `track_index`, `device_index`, `parameter_index`, `value`

Sets a device parameter to a new value. Always read parameters first to get the correct index and verify min/max bounds.

### HPF Audit Workflow

To verify HPF settings across all tracks in one pass:

1. `get_session_info` → get track count
2. For each track: `get_track_info` → find device index of EQ Eight (class_name `Eq8`)
3. `get_device_parameters(track_index, eq_device_index)` → find the HPF band frequency parameter
4. Compare against the standard cutoffs from the EQ Rules table
5. Flag any track where HPF is missing or set too low; apply corrections via `set_device_parameter`

### Standard Track Setup — Auto-Verification

With Phase 1 in place, CC can verify the standard setup on any track:
- Confirm EQ Eight is present (check `get_track_info` devices list)
- Confirm Utility is present and gain-staged appropriately
- Read Compressor threshold/ratio and flag over-compression (ratio > 8:1 is aggressive)
- Read Utility width parameter — confirm bass/kick are mono (width = 0)

---

## Frequency Analysis (Phase 2)

The **AbletonMCP Analyzer** Max4Live device (`Max4Live/AbletonMCP_Analyzer.amxd`) provides real-time per-band frequency analysis via Live parameters. No Max/MSP required — `.amxd` files are Max patches and Ableton loads them directly.

### Installing the device

Run the setup script once (also installs the Remote Script and configures the MCP server):

```bash
python install.py
```

After restarting Ableton, Claude can load the analyzer onto any track automatically:

> "Load the AbletonMCP Analyzer on track 2"

Or call `load_analyzer_device(track_index=2)` directly.

### Reading band levels

Once the device is on a track (e.g., device index 5), call:

```
get_device_parameters(track_index=0, device_index=5)
```

The 6 named parameters and what they represent:

| Parameter name | Band     | Frequency range | Value range |
|----------------|----------|-----------------|-------------|
| Sub Level      | Sub      | 20–60 Hz        | -70 to 0 dB |
| Low Level      | Low      | 60–200 Hz       | -70 to 0 dB |
| LoMid Level    | Lo-Mid   | 200–500 Hz      | -70 to 0 dB |
| Mid Level      | Mid      | 500–2000 Hz     | -70 to 0 dB |
| HiMid Level    | Hi-Mid   | 2000–8000 Hz    | -70 to 0 dB |
| Hi Level       | Hi       | 8000+ Hz        | -70 to 0 dB |

Values are peak amplitude in dB over ~23ms windows. Values near -70 dB = silence; values near 0 dB = full signal.

### Detecting masking conflicts

Scan all tracks' M4L Analyzer devices to build a full-session frequency map. A **masking conflict** exists when two or more tracks have the same band with energy above -20 dB. Example detection logic:

1. For each track, read its M4L Analyzer parameters → store as `{track_name: {band: level_db}}`
2. For each band, find all tracks with level > -20 dB
3. If more than one track is loud in the same band, flag it with the specific tracks and dB levels
4. Cross-reference the 6 trouble frequencies from the EQ Rules table

---

## CC Mixing Session

With Phase 1 + 2 in place, a complete data-driven mixing session follows these steps:

### Step 1 — Gain staging audit

```
get_track_levels()
```

Flag any track with `output_meter_peak > 0.89` (~−1 dBFS) as too hot. Target: peaks at −10 to −6 dBFS during performance (roughly 0.32–0.50).

### Step 2 — Device inventory and analyzer setup

For each track, call `get_track_info(track_index)` and check the `devices` list. Confirm:
- EQ Eight present (class_name `Eq8`)
- Compressor or Glue Compressor present
- Utility present
- Spectrum present
- AbletonMCP Analyzer present (last in chain, class_name contains `MaxDevice` or name contains `AbletonMCP`)

**For any track missing the AbletonMCP Analyzer, call `load_analyzer_device(track_index)` immediately** — do not wait to be asked. Load it on all tracks before proceeding to the frequency map step.

Note device indices for use in subsequent steps.

### Step 3 — HPF audit

For each track's EQ Eight, call `get_device_parameters` and find the HPF band. Compare against the standard cutoffs:
- Kick/bass/floor tom: 40 Hz
- Most instruments: 80–100 Hz
- Hi-hats/cymbals: 250–500 Hz

Apply corrections via `set_device_parameter`.

### Step 4 — Frequency map

For each track's M4L Analyzer device, read all 6 band levels. Build a table:

```
Track     | Sub  | Low  | LoMid | Mid  | HiMid | Hi
----------|------|------|-------|------|-------|----
Bass      | -8   | -12  | -35   | -55  | -70   | -70
Kick      | -15  | -18  | -28   | -48  | -62   | -70
Lead      | -70  | -45  | -22   | -14  | -18   | -35
```

### Step 5 — Masking detection

Flag bands where more than one track has energy > -20 dB. State the specific conflict:
> "Bass and Kick both have significant energy in Low (-12 dB and -18 dB). Cut 2–3 dB at 110 Hz on the Kick using a narrow Q (2–3)."

### Step 6 — Trouble frequency check

For each track, compare band levels against the 6 trouble frequencies:
- 200 Hz (LoMid band): if > -20 dB, check for muddiness → narrow cut
- 300–500 Hz (LoMid): if > -18 dB on kick → boxy sound → cut
- 800 Hz / 1.5 kHz (Mid band): if elevated → check for harshness
- 4–6 kHz (HiMid): if low → boost 1–2 dB, wide Q, to bring forward
- 10 kHz+ (Hi): if low → gentle shelf boost

### Step 7 — Apply corrections

Use `set_device_parameter` to apply each agreed EQ move. Read `get_device_parameters` first to confirm the parameter index and verify min/max bounds.

### Step 8 — Verify and sign off

Re-run `get_track_levels` and `get_device_parameters` on each M4L Analyzer to confirm improvement. Run the Mastering Prep Checklist before export.

## CC Mastering Session

A data-driven mastering session uses the AbletonMCP Analyzer on both the mix and a reference track to make spectral comparisons measurable rather than subjective. The reference track is the key best practice: always master toward a target, not in the abstract.

### Prerequisites

- Mix is complete (mixing session signed off, or working from a rendered stereo file on an audio track)
- A reference track is ready — a commercial release in the same genre that represents the target sound
- Master track is visible in the session

### Standard mastering chain (load on master track in this order)

Load these devices on the master track using `load_instrument_or_effect` with the appropriate URIs, then `load_analyzer_device(track_index=-1)` last:

1. **EQ Eight** — broad tonal correction, high-shelf air boost, low-shelf sub control
2. **Multiband Dynamics** — band-level compression for control without coloring the whole signal
3. **Glue Compressor** — glue and gentle loudness, 1–2 dB GR max
4. **Limiter** — hard ceiling at −0.3 dBTP, lookahead enabled
5. **AbletonMCP Analyzer** — post-chain measurement

### Step 1 — Set up mastering chain

Load the chain on the master track (track_index=-1). Read current devices via `get_track_info` on the master track first — if any are already present, skip loading them.

### Step 2 — Set up reference track

1. Create a new audio track, name it "Reference"
2. Ask the user to drop their reference track audio file onto the first clip slot
3. Load AbletonMCP Analyzer on the reference track
4. Mute the reference track (it's for measurement only, not playback in the master chain)

### Step 3 — Match loudness (pre-comparison)

Loudness matching must happen before spectral comparison — otherwise you are comparing levels, not tone.

1. Solo and play the reference track; read its peak via `get_track_levels`
2. Un-solo; play the mix; read its peak
3. If the mix is more than 2 dB louder than the reference, reduce the master Utility gain (or mix fader) to match. If quieter, increase it.
4. The goal is matched *perceived* loudness. Since Live does not expose LUFS, use peak meters as a proxy and trust your ears to confirm.

### Step 4 — Build frequency profiles

With levels matched, play both tracks and read their M4L Analyzer parameters. Build a comparison table:

```
Band    | Reference | Mix   | Delta
--------|-----------|-------|-------
Sub     | −22 dB    | −25   | −3 (mix light)
Low     | −14 dB    | −11   | +3 (mix heavy)
LoMid   | −18 dB    | −22   | −4 (mix thin)
Mid     | −16 dB    | −18   | −2 (within tolerance)
HiMid   | −12 dB    | −8    | +4 (mix harsh)
Hi      | −20 dB    | −24   | −4 (mix dull)
```

### Step 5 — Apply EQ corrections on master

For each band where the delta exceeds 2 dB, apply a correction to master EQ Eight. Mastering EQ is gentle — use wide Q (0.5–1.0), move in 1–2 dB increments:

| Delta | Direction | Action |
|-------|-----------|--------|
| Mix heavy (+3 dB Low) | Cut | −3 dB around 110 Hz, Q 0.7 |
| Mix light (−4 dB LoMid) | Boost | +3 dB around 316 Hz, Q 0.7 (leave 1 dB headroom) |
| Mix harsh (+4 dB HiMid) | Cut | −3 dB around 4 kHz, Q 0.7 |
| Mix dull (−4 dB Hi) | Boost | +3 dB shelf above 10 kHz |

Use `set_device_parameter` to apply. Always read current parameter values first with `get_device_parameters` to confirm band frequencies and indices.

### Step 6 — Set dynamics

Read current Glue Compressor and Limiter parameters via `get_device_parameters`, then set:

**Glue Compressor:**
- Ratio: 2:1
- Attack: 30 ms (slow — preserve transients)
- Release: 200 ms
- Threshold: adjust until GR reads 1–2 dB during loud passages

**Limiter:**
- Ceiling: −0.3 dBTP
- Lookahead: on (if available as a parameter)

### Step 7 — Verify

1. Re-read AbletonMCP Analyzer on master and reference — confirm all band deltas are within 2 dB
2. Re-read `get_track_levels` — confirm master peak ≤ ~0.97 (−0.3 dBFS)
3. Mono check: set master Utility width to 0 momentarily, confirm key elements survive, restore width

### Mastering sign-off checklist

- [ ] All band levels within 2 dB of reference
- [ ] Peak output ≤ −0.3 dBFS on master
- [ ] Glue Compressor GR ≤ 3 dB (no over-compression)
- [ ] Mono compatibility confirmed
- [ ] Reference track muted/deleted before export

