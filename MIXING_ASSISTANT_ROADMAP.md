# Mixing Assistant Roadmap

This document tracks the plan to extend ableton-mcp into a full Claude Code mixing assistant, giving CC real audio analysis data rather than rule-of-thumb advice.

## The Problem

The Ableton Live API does not expose real-time audio buffers or FFT data directly. Without extensions, CC can only give generic mixing advice based on rules — it cannot measure the actual frequency content of a track or detect inter-track masking from live data.

## The Solution Architecture

Three phases, each building on the last:

1. **MCP Extension** — read meter levels and device parameters (EQ Eight bands, compressor GR) from Ableton in real time
2. **Max4Live Analysis Device** — real-time FFT on each track, exposed as device parameters the MCP can read
3. **CC Mixing Workflow** — CC reads all track data, builds a frequency map, detects problems, and applies fixes via `set_device_parameter`

---

## Phase 1 — MCP Extension: Meter Levels & Device Parameters

**Effort:** ~2 hours
**File to modify:** `AbletonMCP_Remote_Script/__init__.py`

### What to build

**`get_track_levels`** — new Remote Script command that polls `track.output_meter_left` and `track.output_meter_right` for every track and returns peak values. Gives CC a real-time picture of gain staging across the session.

**`get_device_parameters`** — new Remote Script command that reads all parameter name/value pairs from a specific device on a track. Gives CC the ability to read:
- EQ Eight: HPF frequency, band frequencies, gains, and Q values
- Compressor: threshold, ratio, attack, release, gain reduction
- Utility: gain, width setting
- Any other Ableton device

`set_device_parameter` already exists — CC can apply suggested changes after reading.

### MCP Server additions

Add corresponding tool functions in `MCP_Server/server.py` that call the new Remote Script commands and return structured JSON.

### When complete — update CLAUDE.md

Add a section under **Mixing Assistant** called **Reading Live Data (Phase 1)**:
- Document the `get_track_levels` command and its return format
- Document the `get_device_parameters` command, its params (track_index, device_index), and return format
- Add a workflow example: how to audit HPF settings across all tracks in one pass
- Update the **Standard Track Setup** section to note that Utility and EQ Eight parameters can now be read and verified by CC automatically

---

## Phase 2 — Max4Live Analysis Device

**Effort:** ~4–8 hours
**New file:** `Max4Live/AbletonMCP_Analyzer.amxd`

### What to build

A Max4Live audio effect device that:

1. Receives the audio signal via `plugin~` or `pfft~`
2. Runs a real-time FFT and bins energy into frequency bands:
   - Sub: 20–60 Hz
   - Low: 60–200 Hz
   - Low-Mid: 200–500 Hz
   - Mid: 500–2 kHz
   - Hi-Mid: 2–8 kHz
   - Hi: 8 kHz+
3. Maps each band's RMS energy to a Live device parameter (a dial/knob) so it is readable via the Live API
4. Also exposes peak frequency within each band as a parameter

The MCP's existing `get_device_parameters` command (from Phase 1) will read these parameter values — no additional MCP work needed.

### Workflow

Load the device on every track after Spectrum. CC calls `get_device_parameters` on it to get a per-track frequency profile. Repeat across all tracks to build a full-session frequency map.

### When complete — update CLAUDE.md

Add a section under **Mixing Assistant** called **Frequency Analysis (Phase 2)**:
- Document the device name and where to find it in the browser once installed
- Document the 6 parameter names and what they represent (band RMS levels)
- Add it to the **Standard Track Setup** load order
- Add a workflow example: how CC reads all tracks' M4L devices and flags masking conflicts
- Update the **Signal Chain Order** to include the M4L device at the end of the chain
- Add a note that the **6 Trouble Frequencies** table can now be checked against real measured data rather than by ear alone

---

## Phase 3 — Full CC Mixing Workflow

**Effort:** ~2 hours (documentation and workflow scripting)
**Files:** `CLAUDE.md`, socket helper scripts if needed

### What to build

With Phase 1 and 2 in place, document and optionally script the full mixing session workflow:

1. `get_track_levels` → build level map, flag tracks that are too hot (> -6 dBFS peaks) or too quiet
2. `get_device_parameters` on each track's M4L Analyzer device → build per-track frequency profile
3. Cross-reference all tracks: detect any frequency band where more than one track has significant energy (masking)
4. Check each track's EQ Eight HPF against the standard cutoffs from the mixing reference
5. Check each track's frequency profile against the 6 known trouble bands
6. Generate a prioritised list of suggested EQ moves
7. Apply moves via `set_device_parameter` with user confirmation
8. Re-read levels and M4L parameters to confirm improvement

### When complete — update CLAUDE.md

Replace the **Mixing Assistant Roadmap** reference in CLAUDE.md with a fully operational **CC Mixing Session** workflow section:
- The step-by-step mixing session procedure (the 8 steps above)
- What CC will say when it detects a masking conflict
- How to confirm and apply suggested changes
- Checklist for wrapping up a mixing session (gain staging sign-off, mono check, mastering prep)
- Remove the roadmap pointer — at this point the roadmap is complete and CLAUDE.md should only contain operational instructions

---

## Done When

- [ ] Phase 1: `get_track_levels` and `get_device_parameters` implemented and tested
- [ ] Phase 1: CLAUDE.md updated with Phase 1 operating instructions
- [ ] Phase 2: M4L Analyzer device built and tested on a live session
- [ ] Phase 2: CLAUDE.md updated with Phase 2 operating instructions
- [ ] Phase 3: Full workflow documented and tested end-to-end
- [ ] Phase 3: CLAUDE.md fully operational (roadmap pointer removed, workflow section added)
- [ ] README.md updated to reflect mixing assistant as a shipped feature

## Attribution

Fork of [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) by Siddharth Ahuja, MIT License.
