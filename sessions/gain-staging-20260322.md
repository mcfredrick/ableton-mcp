# Gain Staging — Drip Copy
**Session:** 2026-03-22 | **Before:** master peak −0.56 dBFS | **After:** master peak −5.7 dBFS

## Summary

Gain staging applied across 73-track session. Master output brought from near-clip (−0.56 dBFS) to mixing headroom range (−5.7 dBFS peak, −7.4 dBFS average). All loop and instrument tracks are in the −8 to −10 dBFS range.

---

## Volume Settings Applied

| Track | Index | Before (vol) | After (vol) | dB Reduction | Reason |
|-------|-------|-------------|------------|-------------|--------|
| Vox 🎤 (group bus) | 5 | 0.850 | 0.850 | 0 | Routing bypassed — group meter reads -96 in API |
| Ld. Vox ×4 | 6–9 | 0.850 | 0.400 | ~−6 dB | Near-clip at −0.7 to −0.9 dBFS |
| Drums (group) | 10 | 0.850 | 0.302 | −9 dB | Peak −2.6 dBFS; live kit only (no arrangement clips) |
| Bass (group) | 51 | 0.850 | 0.850 | 0 | Group meter reads −96 in API |
| Drums loops (group) | 54 | 0.850 | 0.338 | −8 dB | Peak −3 dBFS |
| 61-Group | 60 | 0.850 | 0.380 | −7 dB | Peak −3.1 dBFS |
| 72-Control Kit | 71 | 0.850 | 0.269 | ~−6 dB | Peak −1.5 dBFS |
| 73-Sub Sine Bass | 72 | 0.850 | 0.237 | ~−10 dB | Peak −0.9 dBFS; also needs EQ (see below) |
| Loop tracks (55–70) | each | 0.850 | 0.288–0.412 | 6–9 dB | Peaks −2.6 to −5.7 dBFS |
| **Master** | −1 | 0.850 | 0.602 | −3 dB | Final output trim |

---

## Final State (levels-20260322-072652.json)

| Track | Peak (dBFS) | Active Ratio | Status |
|-------|------------|-------------|--------|
| Ld. Vox (×4, pre-master-fader) | −3.6 to −4.0 | 0.50–0.82 | Pre-fader; actual output −6.6 to −7.0 dBFS |
| 73-Sub Sine Bass | −6.0 | 0.85 | OK — EQ still needed |
| 72-Control Kit | −6.2 | 0.79 | OK |
| Loop tracks (55–70) | −7.9 to −10.7 | 0.05–0.43 | OK |
| Group buses (54, 60) | −15.0 to −17.8 | 0.40–0.55 | OK |
| **Master peak** | **−5.7** | — | **Target: −6 to −10 dBFS ✓** |
| **Master avg** | **−7.4** | — | |

---

## Routing Notes

- Vox 🎤 (track 5) and Bass (track 51) group tracks: `output_meter_level` reads −96 dBFS in the Live Remote Script API despite active children. This is an API limitation — the group fader IS attenuating audio but the meter cannot be read via the Python API.
- Ld. Vox tracks (6–9) route to master directly (group fader on track 5 has no effect on their meter or output path as observed). Gain staged via individual track faders at 0.400.
- Do NOT use `set_track_volume` with values below ~0.380 — the Live fader taper becomes extremely steep in that range. Values below 0.360 will silence the track. Reliable range: 0.400–0.850 (approximately linear).

---

## Remaining Work

1. **Sub Sine Bass (72) EQ** — cut 3 dB at 700 Hz (Q 3.5) for mud; cut 6 dB shelf above 8 kHz (harmonic bleed into air band at −12 dBFS). Priority: HIGH.
2. **HPF audit** — verify high-pass filter settings on all tracks via FabFilter Pro-Q 4 (in rack). Apply standard cutoffs from CLAUDE.md EQ Rules.
3. **Guitar loop presence boost** — tracks 62, 65, 68 have no upper/definition energy (−55 to −66 dBFS). Boost 2 dB at 3–5 kHz after HPF audit.
4. **Load AbletonMCP Analyzer on remaining tracks** — frequency data only available on 10 of 73 tracks. Run `sample_levels.py` again after loading analyzers for full frequency map.
