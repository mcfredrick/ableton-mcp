Start a CC mixing session on the current Ableton Live project.

Follow the CC Mixing Session workflow from CLAUDE.md exactly, in order, without skipping steps:

0. Session snapshot — call capture_session_snapshot(label="pre-mix") to record the starting state as a benchmark
1. Gain staging audit — get_track_levels, flag anything too hot or too quiet
2. Device inventory and analyzer setup — get_track_info on every track, load AbletonMCP Analyzer on any track missing it (do this automatically, don't ask), note all device indices
   Note: if a track has a third-party EQ or compressor (FabFilter, etc.), prefer using it over loading a duplicate built-in device. Check device names in get_track_info.
3. HPF audit — read EQ Eight parameters on every track, compare against standard cutoffs, apply corrections
4. Frequency map — read AbletonMCP Analyzer parameters on every track, build a band-level table
5. Masking detection — identify frequency bands where more than one track is loud (> −20 dB)
6. Trouble frequency check — cross-reference each track's profile against the 6 known trouble bands
7. Apply corrections — present your findings and proposed EQ moves, then apply them with set_device_parameter after confirming with me
8. Verify — re-read levels and analyzer parameters to confirm improvement, present the Mastering Prep Checklist

Start immediately with Step 1. Report findings at each step before moving to the next.
