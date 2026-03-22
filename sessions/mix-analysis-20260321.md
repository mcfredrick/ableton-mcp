# Mix Analysis — Drip Copy
**Session:** 2026-03-21 22:08:40 | **Tempo:** 140 BPM | **Tracks:** 73 | **Sample count:** 467

> **Note:** The `duration_s` field in the JSON is 0, meaning `sample_levels.py` ran in indefinite/manual-stop mode. All 467 samples were collected. Return tracks (A-Reverb, B-Delay) were silent throughout — sends are likely not routed or the session was not playing with return bus activity. Frequency analyzer data was sparse: only 10 tracks have `freq_avg` populated, suggesting the AbletonMCP Analyzer was not loaded on most tracks.

**Master output:** peak −0.56 dBFS, avg −2.32 dBFS — the master bus is hot. Leaves almost no headroom for mastering.

---

## 1. Gain Staging Issues

### Too Hot (active tracks with `peak_max_dbfs > −6 dBFS`)

| Track | Peak (dBFS) | Active Ratio |
|-------|-------------|--------------|
| Ld. Vox (inst. 1) | −0.7 | 0.73 |
| Ld. Vox (inst. 2) | −0.7 | 0.49 |
| Ld. Vox (inst. 3) | −0.9 | 0.54 |
| Ld. Vox (inst. 4) | −0.9 | 0.79 |
| 73-Sub Sine Bass | −0.9 | 0.83 |
| 72-Control Kit | −1.5 | 0.78 |
| Vox 🎤 | −1.8 | 0.79 |
| Drums | −2.6 | 0.79 |
| 58-TH_80_Drumloop_08_Full | −2.6 | 0.18 |
| 56-SO_CA_130_drum_loop_dumbo | −2.9 | 0.40 |
| 57-WMM_140_drum_loop_hyphy | −3.0 | 0.09 |
| 61-Group | −3.1 | 0.83 |
| 60-shs_eerie_tape_70_drum_loop | −3.1 | 0.27 |
| 63-FNZ_guitar_loop_weird_140 | −3.2 | 0.09 |
| 59-TS_VV_76_drum_loop_acetone | −3.3 | 0.17 |
| 65-Melody_Loop_23_90_Em | −3.3 | 0.09 |
| 64-T_ESL_126_organ_stab_loop | −3.6 | 0.09 |
| 67-HAYWYRE_melodic_bass_stab | −3.7 | 0.06 |
| 62-KMRBI_GHGL_85_electric_guitar | −3.8 | 0.31 |
| 70-Sub 808 Bass | −3.8 | 0.24 |
| 71-Basic 303 Bass | −3.8 | 0.26 |
| 69-Sub 808 Bass | −4.0 | 0.21 |
| 66-HAYWYRE_clap_weird_02 | −4.2 | 0.07 |
| 68-X-Square Keys | −5.7 | 0.09 |

**24 of the active tracks are above −6 dBFS** — nearly every active signal in this session. Target range is −18 to −12 dBFS pre-fader on individual tracks. The busiest tracks (Ld. Vox, Sub Sine Bass) are at near-clip levels.

### Too Quiet (active tracks with `peak_max_dbfs < −20 dBFS`)

None. All active tracks are within range or hot.

---

## 2. Frequency Map

Only 10 tracks returned `freq_avg` data (AbletonMCP Analyzer not loaded on remaining tracks). Values in dBFS, rounded. `-` = below −60 dB (effectively silent).

| Track | Sub(40) | Low(110) | LoMid(316) | Mud(700) | Pres(1.5k) | Upper(3k) | Def(5k) | Bril(9k) | Air(14k) |
|-------|---------|----------|-----------|---------|-----------|---------|--------|--------|--------|
| Vox 🎤 | −25 | −25 | − | −25 | −25 | −26 | −30 | −27 | −23 |
| Ld. Vox (a) | −37 | −37 | − | −37 | −37 | −38 | −41 | −39 | −36 |
| Ld. Vox (b) | −21 | −21 | − | −21 | −21 | −22 | −26 | −23 | −19 |
| Ld. Vox (c) | −41 | −41 | − | −41 | −41 | −42 | −44 | −43 | −40 |
| Ld. Vox (d) | −25 | −25 | − | −25 | −26 | −27 | −30 | −28 | −24 |
| Drums | −27 | −27 | − | −27 | −28 | −29 | −32 | −30 | −25 |
| 56-SO_CA_drum_loop | −48 | −48 | − | −48 | −48 | −48 | −50 | −49 | −47 |
| 61-Group | −30 | −30 | − | −30 | −30 | −31 | −35 | −32 | −28 |
| 72-Control Kit | −21 | −21 | − | −21 | −21 | −22 | −25 | −24 | −20 |
| 73-Sub Sine Bass | −14 | −14 | − | −14 | −14 | −15 | −19 | −16 | −12 |

**Notable:** The LoMid (316 Hz) band shows `-` (below −60 dB) across all tracked tracks. This is anomalous — 316 Hz is in the heart of vocal and instrument body range. Either the analyzer band mapping shifted or most energy is below the detection threshold in that specific bin. Treat with caution; verify with ears and Spectrum.

---

## 3. Masking Conflicts

### Air (14 kHz) — 3 tracks above −20 dB

| Track | Air Level |
|-------|-----------|
| 73-Sub Sine Bass | −12 dB |
| Ld. Vox (b) | −19 dB |
| 72-Control Kit | −20 dB |

**73-Sub Sine Bass at −12 dB in the Air band is a significant problem.** A sub bass has no business pushing 14 kHz content — this suggests the bass is either heavily saturated/distorted or driving harmonic excitation into the highs. It will compete with vocal air and drum transient shimmer.

### No conflicts above −20 dB in other bands

Sub, Low, LoMid, Mud, Presence, Upper, Definition, Brilliance bands show at most one track at or above −20 dB in the current (partial) dataset. Full masking conflict analysis requires loading the Analyzer on all 73 tracks.

---

## 4. Trouble Frequency Check

### Boxy / Mud (700 Hz > −18 dB)
| Track | Mud Level | Verdict |
|-------|-----------|---------|
| 73-Sub Sine Bass | −14 dB | **FLAG** — cut 3 dB at 700 Hz, narrow Q (3–4) |

### Muddy / LoMid (316 Hz > −20 dB)
No tracks flagged — all LoMid readings are below −60 dB (silent in that bin; see note in Section 2).

### Buried (Upper+Def avg < −35 dB, active tracks)

| Track | Upper(3k) | Def(5k) | Avg | Active |
|-------|-----------|---------|-----|--------|
| 57-WMM_140_drum_loop_hyphy | −64 | −65 | −64.5 | 0.09 |
| 63-FNZ_guitar_loop_weird_140 | −65 | −65 | −65.0 | 0.09 |
| 64-T_ESL_126_organ_stab | −66 | −66 | −66.0 | 0.09 |
| 65-Melody_Loop_23_90_Em | −65 | −65 | −65.0 | 0.09 |
| 66-HAYWYRE_clap_weird_02 | −66 | −66 | −66.0 | 0.07 |
| 67-HAYWYRE_melodic_bass_stab | −67 | −67 | −67.0 | 0.06 |
| 68-X-Square Keys | −66 | −66 | −66.0 | 0.09 |
| 58-TH_80_Drumloop_08_Full | −60 | −61 | −60.5 | 0.18 |
| 59-TS_VV_76_drum_loop | −61 | −62 | −61.5 | 0.17 |
| 60-shs_eerie_tape_70_drum | −57 | −59 | −58.0 | 0.27 |
| 62-KMRBI_GHGL_85_guitar | −55 | −57 | −56.0 | 0.31 |
| 69-Sub 808 Bass | −61 | −62 | −61.5 | 0.21 |
| 70-Sub 808 Bass | −61 | −62 | −61.5 | 0.24 |
| 71-Basic 303 Bass | −58 | −60 | −59.0 | 0.26 |
| Ld. Vox (a) | −38 | −41 | −39.5 | 0.73 |
| Ld. Vox (c) | −42 | −44 | −43.0 | 0.54 |

Sub/808 basses being buried in upper mids is expected. Guitar loops (62, 63) and melodic elements (65, 68) should have definition-range presence — their low readings suggest the Analyzer may be post-fader at very low gain, or these loops lack high-end content inherently.

### Dull (Air < −40 dB, active tracks)
Same population as buried list above. For drum loops and bass lines this is acceptable; for guitar and melodic loops it warrants a gentle high-shelf boost after gain staging is corrected.

---

## 5. EQ Recommendations

**73-Sub Sine Bass** (peak −0.9 dBFS, mud −14 dB, air −12 dB)
- Cut 3 dB at 700 Hz, Q 3.5 — boxy mud content is atypical for a sine bass; likely harmonic or overdrive artifact
- Cut 6 dB shelf above 8 kHz — sub sines should have minimal high content; the −12 dB air reading indicates distortion bleed
- Reduce gain 8–10 dB via Utility to bring peak to −10 dBFS

**Vox 🎤** (peak −1.8 dBFS, broad flat energy ~−25 dB)
- Reduce pre-fader gain 10 dB to reach −12 dBFS peak
- Boost 2–3 dB shelf above 10 kHz, Q 0.7 — air at −23 dB is moderate but will sit below the bass at current gain staging

**Ld. Vox (all four instances)** (peaks −0.7 to −0.9 dBFS)
- Reduce pre-fader gain 8–10 dB each — four concurrent near-clip vocals summing to master is the primary cause of the hot master output
- On Ld. Vox (b), the most present instance: boost 2 dB at 5 kHz, Q 1.5 to restore definition after gain reduction

**Drums group** (peak −2.6 dBFS)
- Reduce gain 4–6 dB to bring peak to −8 to −6 dBFS range
- Cut 2 dB at 700 Hz, Q 2.0 — mud band at −27 dB will become more prominent once the overall gain picture is corrected

**62-KMRBI_GHGL_85_electric_guitar** (peak −3.8 dBFS, active 31%)
- Boost 2 dB at 3 kHz, Q 1.0 and 2 dB at 5 kHz, Q 1.0 — guitar has no upper/definition energy (−55/−57 dB); it will be inaudible in the mix without presence restoration

---

## 6. Top Issues Summary — Priority Order

1. **Gain staging is broken session-wide.** 24 active tracks are above −6 dBFS and the master peaks at −0.56 dBFS. There is zero headroom for mastering. Reduce all active tracks 6–10 dB via Utility before any EQ work is valid. This is the first and most urgent fix.

2. **Four Ld. Vox tracks are clipping simultaneously** (−0.7 to −0.9 dBFS each, active 49–79% of the time). When they overlap they sum well above 0 dBFS pre-bus. These need individual Utility gain reduction and a shared bus compressor to control combined output.

3. **73-Sub Sine Bass is bleeding harmonic content into the Air band (−12 dB at 14 kHz).** A clean sine should not radiate at 14 kHz. This track is saturated or overdriven and is masking vocal air and drum shimmer across the full arrangement.

4. **AbletonMCP Analyzer is not loaded on 63 of 73 tracks.** The frequency map and masking conflict analysis covers only 14% of the session. Load the Analyzer on all tracks and re-run `sample_levels.py` before proceeding with EQ work — the current data is too sparse for confident masking decisions on most tracks.

5. **Guitar and melodic loop tracks are buried in the upper midrange** (tracks 62, 63, 65, 68 show −55 to −66 dB at 3–5 kHz). After gain staging is corrected, reassess these tracks with Spectrum. If upper-mid content is genuinely absent, apply a 2–3 dB boost at 3–5 kHz with a wide Q to restore definition and prevent these elements from disappearing in the mix.
