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

When the M4L Analysis Device is available (see Roadmap), add it after Spectrum.

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
  → [M4L Analysis Device when built]
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
```

---

## Mixing Assistant Roadmap

See [`MIXING_ASSISTANT_ROADMAP.md`](MIXING_ASSISTANT_ROADMAP.md) for the full plan to extend CC into a real-time audio analysis mixing assistant (meter levels, device parameter reading, Max4Live FFT device). Each phase includes instructions for updating this CLAUDE.md file with operating instructions as features are completed.
